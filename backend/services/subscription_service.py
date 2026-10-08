"""Subscription service — business logic layer.

Responsibilities:
- Entitlement checks (can this org start a campaign? add an agent? etc.)
- Plan change (upgrade/downgrade) with limit enforcement
- Seed default plans on first startup
- Enforce: one active subscription per org

All monetary values are in INTEGER PAISE. Behaviour changes are driven by plan
configuration in the database — no hard-coded pricing or feature lists here.
"""

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.subscription import EntitlementCheck, Subscription, SubscriptionPlan
from backend.repositories.subscription_repo import (
    SubscriptionPlanRepository,
    SubscriptionRepository,
)

log = logging.getLogger("service.subscription")

# ---------------------------------------------------------------------------
# Default plans seeded on first startup
# ---------------------------------------------------------------------------
DEFAULT_PLANS = [
    {
        "name": "Starter",
        "slug": "starter",
        "description": "Get started with AI calling. Perfect for small teams.",
        "price_monthly_paise": 299900,   # ₹2,999/month
        "price_yearly_paise": 2999900,   # ₹29,999/year (~₹2,500/month)
        "max_concurrent_calls": 1,
        "max_campaigns": 2,
        "max_agents": 2,
        "max_leads_per_campaign": 1000,
        "max_team_members": 3,
        "analytics_retention_days": 30,
        "knowledge_base_enabled": False,
        "api_access": False,
        "trial_days": 7,
        "is_public": True,
        "sort_order": 1,
    },
    {
        "name": "Growth",
        "slug": "growth",
        "description": "Scale your outreach. Ideal for growing sales teams.",
        "price_monthly_paise": 799900,   # ₹7,999/month
        "price_yearly_paise": 7999900,   # ₹79,999/year (~₹6,667/month)
        "max_concurrent_calls": 5,
        "max_campaigns": 10,
        "max_agents": 5,
        "max_leads_per_campaign": 5000,
        "max_team_members": 10,
        "analytics_retention_days": 90,
        "knowledge_base_enabled": True,
        "api_access": False,
        "trial_days": 7,
        "is_public": True,
        "sort_order": 2,
    },
    {
        "name": "Pro",
        "slug": "pro",
        "description": "Full power for enterprise teams. API access included.",
        "price_monthly_paise": 1999900,  # ₹19,999/month
        "price_yearly_paise": 19999900,  # ₹1,99,999/year (~₹16,667/month)
        "max_concurrent_calls": 20,
        "max_campaigns": 50,
        "max_agents": 20,
        "max_leads_per_campaign": 50000,
        "max_team_members": 50,
        "analytics_retention_days": 365,
        "knowledge_base_enabled": True,
        "api_access": True,
        "custom_voice_profiles": True,
        "priority_support": True,
        "trial_days": 14,
        "is_public": True,
        "sort_order": 3,
    },
]


async def seed_default_plans(db: AsyncIOMotorDatabase) -> list[SubscriptionPlan]:
    """Create default plans if they don't exist. Safe to call on every startup."""
    repo = SubscriptionPlanRepository(db)
    created = []
    for plan_data in DEFAULT_PLANS:
        existing = await repo.find_by_slug(plan_data["slug"])
        if existing is None:
            plan = await repo.create(**plan_data)
            created.append(plan)
            log.info("seeded plan: %s", plan.slug)
        else:
            log.debug("plan already exists: %s", plan_data["slug"])
    return created


# ---------------------------------------------------------------------------
# Entitlement checks — all business logic lives here, not in endpoints
# ---------------------------------------------------------------------------

class SubscriptionService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.plan_repo = SubscriptionPlanRepository(db)
        self.sub_repo = SubscriptionRepository(db)

    async def get_active_subscription(
        self, organization_id: str
    ) -> Optional[Subscription]:
        return await self.sub_repo.find_active_for_org(organization_id)

    async def get_plan(self, plan_id: str) -> Optional[SubscriptionPlan]:
        return await self.plan_repo.find_by_id(plan_id)

    async def get_plan_by_slug(self, slug: str) -> Optional[SubscriptionPlan]:
        return await self.plan_repo.find_by_slug(slug)

    # ---- Entitlement checks ----

    async def check_subscription_active(
        self, organization_id: str
    ) -> EntitlementCheck:
        sub = await self.get_active_subscription(organization_id)
        if sub is None:
            return EntitlementCheck(
                allowed=False,
                reason="No active subscription. Please subscribe to a plan.",
            )
        return EntitlementCheck(allowed=True)

    async def check_can_add_campaign(
        self, organization_id: str, current_campaign_count: int
    ) -> EntitlementCheck:
        sub = await self.get_active_subscription(organization_id)
        if sub is None:
            return EntitlementCheck(allowed=False, reason="No active subscription")
        limit = sub.snapshot_max_campaigns
        if current_campaign_count >= limit:
            return EntitlementCheck(
                allowed=False,
                reason=f"Campaign limit reached ({limit}). Upgrade your plan to create more.",
                limit=limit,
                current=current_campaign_count,
            )
        return EntitlementCheck(
            allowed=True, limit=limit, current=current_campaign_count
        )

    async def check_can_add_agent(
        self, organization_id: str, current_agent_count: int
    ) -> EntitlementCheck:
        sub = await self.get_active_subscription(organization_id)
        if sub is None:
            return EntitlementCheck(allowed=False, reason="No active subscription")
        limit = sub.snapshot_max_agents
        if current_agent_count >= limit:
            return EntitlementCheck(
                allowed=False,
                reason=f"Agent limit reached ({limit}). Upgrade your plan.",
                limit=limit,
                current=current_agent_count,
            )
        return EntitlementCheck(allowed=True, limit=limit, current=current_agent_count)

    async def check_concurrent_calls(
        self, organization_id: str, current_active_calls: int
    ) -> EntitlementCheck:
        sub = await self.get_active_subscription(organization_id)
        if sub is None:
            return EntitlementCheck(allowed=False, reason="No active subscription")
        limit = sub.snapshot_max_concurrent_calls
        if current_active_calls >= limit:
            return EntitlementCheck(
                allowed=False,
                reason=f"Concurrent call limit reached ({limit}).",
                limit=limit,
                current=current_active_calls,
            )
        return EntitlementCheck(
            allowed=True, limit=limit, current=current_active_calls
        )

    async def check_feature(
        self, organization_id: str, feature: str
    ) -> EntitlementCheck:
        """Check a boolean feature gate, e.g. 'knowledge_base_enabled'."""
        sub = await self.get_active_subscription(organization_id)
        if sub is None:
            return EntitlementCheck(allowed=False, reason="No active subscription")
        enabled = sub.snapshot_features.get(feature, False)
        if not enabled:
            return EntitlementCheck(
                allowed=False,
                reason=f"Feature '{feature}' is not available on your plan. Upgrade to access it.",
            )
        return EntitlementCheck(allowed=True)

    async def check_leads_per_campaign(
        self, organization_id: str, lead_count: int
    ) -> EntitlementCheck:
        sub = await self.get_active_subscription(organization_id)
        if sub is None:
            return EntitlementCheck(allowed=False, reason="No active subscription")
        limit = sub.snapshot_max_leads_per_campaign
        if lead_count > limit:
            return EntitlementCheck(
                allowed=False,
                reason=f"Lead count ({lead_count}) exceeds plan limit ({limit}). Upgrade or split the campaign.",
                limit=limit,
                current=lead_count,
            )
        return EntitlementCheck(allowed=True, limit=limit, current=lead_count)

    async def check_team_members(
        self, organization_id: str, current_count: int
    ) -> EntitlementCheck:
        sub = await self.get_active_subscription(organization_id)
        if sub is None:
            return EntitlementCheck(allowed=False, reason="No active subscription")
        limit = sub.snapshot_max_team_members
        if current_count >= limit:
            return EntitlementCheck(
                allowed=False,
                reason=f"Team member limit reached ({limit}). Upgrade your plan.",
                limit=limit,
                current=current_count,
            )
        return EntitlementCheck(allowed=True, limit=limit, current=current_count)

    # ---- Subscription lifecycle ----

    async def activate_plan(
        self,
        organization_id: str,
        plan_id: str,
        billing_cycle: str = "monthly",
        created_by: Optional[str] = None,
        payment_id: Optional[str] = None,
    ) -> Subscription:
        """Activate a plan for an org. Cancels any existing subscription immediately."""
        plan = await self.plan_repo.find_by_id(plan_id)
        if plan is None:
            raise ValueError(f"Plan {plan_id} not found")
        if not plan.is_active:
            raise ValueError(f"Plan '{plan.name}' is no longer available")

        # Cancel existing subscription (immediate)
        existing = await self.sub_repo.find_active_for_org(organization_id)
        if existing:
            await self.sub_repo.cancel(existing.id, at_period_end=False)
            log.info("cancelled existing sub=%s for org=%s", existing.id, organization_id)

        sub = await self.sub_repo.create_for_org(
            organization_id=organization_id,
            plan=plan,
            billing_cycle=billing_cycle,
            created_by=created_by,
            start_trial=(payment_id is None),  # no trial if paid upfront
        )

        # If paid upfront, mark as active immediately (not trial)
        if payment_id:
            await self.sub_repo.update_by_id(sub.id, {
                "status": "active",
                "last_payment_id": payment_id,
                "last_payment_at": sub.started_at,
                "trial_ends_at": None,
            })

        return sub

    async def cancel_subscription(
        self,
        organization_id: str,
        at_period_end: bool = True,
        cancelled_by: Optional[str] = None,
    ) -> Optional[Subscription]:
        sub = await self.sub_repo.find_active_for_org(organization_id)
        if sub is None:
            return None
        await self.sub_repo.cancel(sub.id, at_period_end=at_period_end)
        return sub

    async def change_plan(
        self,
        organization_id: str,
        new_plan_id: str,
        billing_cycle: str = "monthly",
    ) -> Subscription:
        """Upgrade or downgrade. Takes effect immediately."""
        new_plan = await self.plan_repo.find_by_id(new_plan_id)
        if new_plan is None:
            raise ValueError(f"Plan {new_plan_id} not found")
        if not new_plan.is_active:
            raise ValueError(f"Plan '{new_plan.name}' is no longer available")

        sub = await self.sub_repo.find_active_for_org(organization_id)
        if sub is None:
            # No active sub → create new one
            return await self.activate_plan(
                organization_id, new_plan_id, billing_cycle
            )

        await self.sub_repo.upgrade(sub.id, new_plan, billing_cycle)
        refreshed = await self.sub_repo.find_by_id(sub.id)
        log.info(
            "plan changed org=%s from=%s to=%s",
            organization_id, sub.plan_slug, new_plan.slug,
        )
        return refreshed

    # ---- Convenience: get entitlement summary ----

    async def get_entitlements(
        self, organization_id: str
    ) -> dict:
        """Return a safe summary of what the org is entitled to (for API response)."""
        sub = await self.get_active_subscription(organization_id)
        if sub is None:
            return {
                "has_subscription": False,
                "status": "none",
                "plan_slug": None,
                "limits": {},
                "features": {},
            }
        return {
            "has_subscription": True,
            "status": sub.status,
            "plan_slug": sub.plan_slug,
            "billing_cycle": sub.billing_cycle,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            "cancel_at_period_end": sub.cancel_at_period_end,
            "limits": {
                "max_concurrent_calls": sub.snapshot_max_concurrent_calls,
                "max_campaigns": sub.snapshot_max_campaigns,
                "max_agents": sub.snapshot_max_agents,
                "max_leads_per_campaign": sub.snapshot_max_leads_per_campaign,
                "max_team_members": sub.snapshot_max_team_members,
            },
            "features": sub.snapshot_features,
        }
