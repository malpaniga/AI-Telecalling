"""Subscription plan and subscription repositories."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from pymongo import ASCENDING, DESCENDING

from backend.models.base import new_id, utcnow
from backend.models.subscription import Subscription, SubscriptionPlan
from backend.repositories.base import BaseRepository

log = logging.getLogger("repo.subscription")


class SubscriptionPlanRepository(BaseRepository):
    """Platform-managed subscription plans."""

    collection_name = "subscription_plans"
    model_class = SubscriptionPlan

    async def create(
        self,
        name: str,
        slug: str,
        description: str = "",
        price_monthly_paise: int = 0,
        price_yearly_paise: int = 0,
        max_concurrent_calls: int = 1,
        max_campaigns: int = 1,
        max_agents: int = 1,
        max_leads_per_campaign: int = 500,
        max_team_members: int = 3,
        analytics_retention_days: int = 30,
        knowledge_base_enabled: bool = False,
        api_access: bool = False,
        custom_voice_profiles: bool = False,
        priority_support: bool = False,
        white_label: bool = False,
        trial_days: int = 0,
        is_public: bool = True,
        sort_order: int = 0,
        features: Optional[dict] = None,
    ) -> SubscriptionPlan:
        plan = SubscriptionPlan(
            _id=new_id(),
            name=name,
            slug=slug,
            description=description,
            price_monthly_paise=price_monthly_paise,
            price_yearly_paise=price_yearly_paise,
            max_concurrent_calls=max_concurrent_calls,
            max_campaigns=max_campaigns,
            max_agents=max_agents,
            max_leads_per_campaign=max_leads_per_campaign,
            max_team_members=max_team_members,
            analytics_retention_days=analytics_retention_days,
            knowledge_base_enabled=knowledge_base_enabled,
            api_access=api_access,
            custom_voice_profiles=custom_voice_profiles,
            priority_support=priority_support,
            white_label=white_label,
            trial_days=trial_days,
            is_public=is_public,
            sort_order=sort_order,
            features=features or {},
        )
        await self.insert(plan)
        log.info("plan created id=%s slug=%s", plan.id, plan.slug)
        return plan

    async def find_by_slug(self, slug: str) -> Optional[SubscriptionPlan]:
        return await self.find_one({"slug": slug})

    async def list_public(self) -> list[SubscriptionPlan]:
        """Active public plans, sorted by sort_order."""
        return await self.find_many(
            {"is_active": True, "is_public": True},
            sort=[("sort_order", ASCENDING)],
        )

    async def list_all(
        self, include_inactive: bool = False
    ) -> list[SubscriptionPlan]:
        query: dict = {} if include_inactive else {"is_active": True}
        return await self.find_many(query, sort=[("sort_order", ASCENDING)])

    async def set_active(self, plan_id: str, is_active: bool) -> bool:
        return await self.update_by_id(plan_id, {"is_active": is_active})

    async def update_price(
        self,
        plan_id: str,
        price_monthly_paise: Optional[int] = None,
        price_yearly_paise: Optional[int] = None,
    ) -> bool:
        updates: dict = {}
        if price_monthly_paise is not None:
            updates["price_monthly_paise"] = price_monthly_paise
        if price_yearly_paise is not None:
            updates["price_yearly_paise"] = price_yearly_paise
        if not updates:
            return False
        return await self.update_by_id(plan_id, updates)

    async def update_limits(self, plan_id: str, **limit_kwargs) -> bool:
        allowed_fields = {
            "max_concurrent_calls", "max_campaigns", "max_agents",
            "max_leads_per_campaign", "max_team_members",
            "analytics_retention_days", "knowledge_base_enabled",
            "api_access", "custom_voice_profiles", "priority_support",
            "white_label", "trial_days", "sort_order", "description",
            "name", "features",
        }
        updates = {k: v for k, v in limit_kwargs.items() if k in allowed_fields}
        if not updates:
            return False
        return await self.update_by_id(plan_id, updates)


class SubscriptionRepository(BaseRepository):
    """Organization subscriptions — one active subscription per org."""

    collection_name = "subscriptions"
    model_class = Subscription

    async def create_for_org(
        self,
        organization_id: str,
        plan: SubscriptionPlan,
        billing_cycle: str = "monthly",
        created_by: Optional[str] = None,
        start_trial: bool = True,
    ) -> Subscription:
        """Create a new subscription. Cancels any existing active subscription first."""
        now = utcnow()

        # Determine period end
        if billing_cycle == "yearly":
            period_end = now + timedelta(days=365)
        else:
            period_end = now + timedelta(days=30)

        # Trial end
        trial_ends_at = None
        status = "active"
        if start_trial and plan.trial_days > 0:
            trial_ends_at = now + timedelta(days=plan.trial_days)
            status = "trialing"

        sub = Subscription(
            _id=new_id(),
            organization_id=organization_id,
            plan_id=plan.id,
            plan_slug=plan.slug,
            billing_cycle=billing_cycle,
            status=status,
            started_at=now,
            current_period_start=now,
            current_period_end=period_end,
            trial_ends_at=trial_ends_at,
            created_by=created_by,
            # Snapshot plan limits at subscription time
            snapshot_max_concurrent_calls=plan.max_concurrent_calls,
            snapshot_max_campaigns=plan.max_campaigns,
            snapshot_max_agents=plan.max_agents,
            snapshot_max_leads_per_campaign=plan.max_leads_per_campaign,
            snapshot_max_team_members=plan.max_team_members,
            snapshot_features={
                "knowledge_base_enabled": plan.knowledge_base_enabled,
                "api_access": plan.api_access,
                "custom_voice_profiles": plan.custom_voice_profiles,
                "priority_support": plan.priority_support,
                "white_label": plan.white_label,
                "analytics_retention_days": plan.analytics_retention_days,
            },
        )
        await self.insert(sub)
        log.info("subscription created org=%s plan=%s", organization_id, plan.slug)
        return sub

    async def find_active_for_org(self, organization_id: str) -> Optional[Subscription]:
        """Get the current active/trialing/past_due subscription for an org."""
        return await self.find_one({
            "organization_id": organization_id,
            "status": {"$in": ["active", "trialing", "past_due"]},
        })

    async def find_for_org(self, organization_id: str) -> Optional[Subscription]:
        """Get the most recent subscription (any status)."""
        docs = await self.find_many(
            {"organization_id": organization_id},
            sort=[("created_at", DESCENDING)],
            limit=1,
        )
        return docs[0] if docs else None

    async def list_all(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[Subscription]:
        query: dict = {}
        if status:
            query["status"] = status
        return await self.find_many(
            query,
            sort=[("created_at", DESCENDING)],
            limit=limit,
            skip=skip,
        )

    async def cancel(
        self,
        sub_id: str,
        at_period_end: bool = True,
    ) -> bool:
        now = utcnow()
        if at_period_end:
            return await self.update_by_id(sub_id, {
                "cancel_at_period_end": True,
                "cancelled_at": now,
            })
        else:
            return await self.update_by_id(sub_id, {
                "status": "cancelled",
                "cancelled_at": now,
                "cancel_at_period_end": False,
            })

    async def upgrade(
        self,
        sub_id: str,
        new_plan: SubscriptionPlan,
        billing_cycle: str,
    ) -> bool:
        """Upgrade/downgrade to a new plan. Updates snapshot immediately."""
        now = utcnow()
        if billing_cycle == "yearly":
            period_end = now + timedelta(days=365)
        else:
            period_end = now + timedelta(days=30)

        return await self.update_by_id(sub_id, {
            "plan_id": new_plan.id,
            "plan_slug": new_plan.slug,
            "billing_cycle": billing_cycle,
            "status": "active",
            "current_period_start": now,
            "current_period_end": period_end,
            "cancel_at_period_end": False,
            "cancelled_at": None,
            "snapshot_max_concurrent_calls": new_plan.max_concurrent_calls,
            "snapshot_max_campaigns": new_plan.max_campaigns,
            "snapshot_max_agents": new_plan.max_agents,
            "snapshot_max_leads_per_campaign": new_plan.max_leads_per_campaign,
            "snapshot_max_team_members": new_plan.max_team_members,
            "snapshot_features": {
                "knowledge_base_enabled": new_plan.knowledge_base_enabled,
                "api_access": new_plan.api_access,
                "custom_voice_profiles": new_plan.custom_voice_profiles,
                "priority_support": new_plan.priority_support,
                "white_label": new_plan.white_label,
                "analytics_retention_days": new_plan.analytics_retention_days,
            },
        })

    async def mark_past_due(self, sub_id: str) -> bool:
        return await self.update_by_id(sub_id, {"status": "past_due"})

    async def mark_renewed(
        self, sub_id: str, payment_id: str, billing_cycle: str
    ) -> bool:
        now = utcnow()
        if billing_cycle == "yearly":
            period_end = now + timedelta(days=365)
        else:
            period_end = now + timedelta(days=30)
        return await self.update_by_id(sub_id, {
            "status": "active",
            "current_period_start": now,
            "current_period_end": period_end,
            "last_payment_id": payment_id,
            "last_payment_at": now,
        })

    async def count_by_plan(self, plan_id: str) -> int:
        """How many active orgs are on this plan."""
        return await self.count({
            "plan_id": plan_id,
            "status": {"$in": ["active", "trialing"]},
        })
