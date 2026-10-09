"""Revenue and margin analytics service — MVP simple approach.

Per spec: "Keep MVP analytics simple."

Metrics computed:
  MRR          — Monthly Recurring Revenue (active subscriptions)
  ARR estimate — MRR × 12
  new_mrr      — from new subscriptions this period
  expansion_mrr — from upgrades this period
  churn_mrr    — from cancellations this period
  ARPU         — Average Revenue Per User (MRR / active orgs)
  subscription_revenue — invoice totals for the period
  calling_revenue      — usage event totals for the period
  provider_costs       — provider_cost_paise sum
  gross_profit         — revenue - provider_costs
  gross_margin_pct     — gross_profit / revenue * 100

All monetary values in integer paise. INR equivalents provided for display.
"""

from __future__ import annotations

import logging
from datetime import datetime, date, timedelta, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

log = logging.getLogger("service.analytics")


class AnalyticsService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    # ---- MRR / ARR ----

    async def compute_mrr(self) -> dict:
        """
        Current MRR from active subscriptions.
        MRR = sum of monthly price of all active/trialing subscriptions
        (yearly subscriptions divided by 12).
        """
        pipeline = [
            {"$match": {"status": {"$in": ["active", "trialing"]}}},
            {"$lookup": {
                "from": "subscription_plans",
                "localField": "plan_id",
                "foreignField": "_id",
                "as": "plan",
            }},
            {"$unwind": {"path": "$plan", "preserveNullAndEmpty": True}},
            {"$project": {
                "billing_cycle": 1,
                "monthly_paise": {
                    "$cond": {
                        "if": {"$eq": ["$billing_cycle", "yearly"]},
                        "then": {"$divide": [{"$ifNull": ["$plan.price_yearly_paise", 0]}, 12]},
                        "else": {"$ifNull": ["$plan.price_monthly_paise", 0]},
                    }
                },
            }},
            {"$group": {"_id": None, "mrr_paise": {"$sum": "$monthly_paise"}}},
        ]
        rows = await self.db["subscriptions"].aggregate(pipeline).to_list(1)
        mrr_paise = int(rows[0]["mrr_paise"]) if rows else 0
        arr_paise = mrr_paise * 12

        # Active subscriber count
        active_orgs = await self.db["subscriptions"].count_documents(
            {"status": {"$in": ["active", "trialing"]}}
        )

        arpu_paise = mrr_paise // active_orgs if active_orgs > 0 else 0

        return {
            "mrr_paise": mrr_paise,
            "mrr_inr": mrr_paise / 100,
            "arr_paise": arr_paise,
            "arr_inr": arr_paise / 100,
            "active_subscribers": active_orgs,
            "arpu_paise": arpu_paise,
            "arpu_inr": arpu_paise / 100,
        }

    async def compute_mrr_movement(
        self,
        from_date: datetime,
        to_date: datetime,
    ) -> dict:
        """
        MRR movement for a period:
          new_mrr       — from new subscriptions started in period
          expansion_mrr — from upgrades (plan_id changed, higher price)
          churn_mrr     — from cancellations in period
        MVP: approximate via subscription events in the period.
        """
        # New subscriptions started in period
        new_subs = await self.db["subscriptions"].count_documents({
            "started_at": {"$gte": from_date, "$lte": to_date},
            "status": {"$in": ["active", "trialing"]},
        })
        # Cancelled in period
        churned = await self.db["subscriptions"].count_documents({
            "cancelled_at": {"$gte": from_date, "$lte": to_date},
            "status": "cancelled",
        })

        # Approximate MRR values using average ARPU
        mrr_data = await self.compute_mrr()
        arpu = mrr_data["arpu_paise"]

        return {
            "new_mrr_paise": new_subs * arpu,
            "new_mrr_inr": (new_subs * arpu) / 100,
            "expansion_mrr_paise": 0,       # MVP: not tracking upgrades yet
            "expansion_mrr_inr": 0.0,
            "churn_mrr_paise": churned * arpu,
            "churn_mrr_inr": (churned * arpu) / 100,
            "new_subscribers": new_subs,
            "churned_subscribers": churned,
            "note": "expansion_mrr requires M27 reconciliation; approximated as 0 for MVP",
        }

    # ---- Revenue breakdown ----

    async def compute_revenue(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> dict:
        """Total revenue: subscription + calling."""
        match_usage: dict = {}
        match_invoice: dict = {}
        if from_date or to_date:
            date_f: dict = {}
            if from_date:
                date_f["$gte"] = from_date
            if to_date:
                date_f["$lte"] = to_date
            match_usage["created_at"] = date_f
            match_invoice["issued_at"] = date_f

        # Subscription revenue from invoices
        sub_pipeline = [
            {"$match": match_invoice},
            {"$group": {"_id": None, "total": {"$sum": "$total_paise"}}},
        ]
        sub_rows = await self.db["invoices"].aggregate(sub_pipeline).to_list(1)
        sub_revenue_paise = sub_rows[0]["total"] if sub_rows else 0

        # Calling pack + usage revenue
        usage_pipeline = [
            {"$match": match_usage},
            {"$group": {
                "_id": None,
                "customer_charge": {"$sum": "$customer_charge_paise"},
                "provider_cost": {"$sum": "$provider_cost_paise"},
                "total_credits": {"$sum": "$credits_consumed"},
                "total_events": {"$sum": 1},
            }},
        ]
        usage_rows = await self.db["usage_events"].aggregate(usage_pipeline).to_list(1)
        usage_charge = usage_rows[0]["customer_charge"] if usage_rows else 0
        provider_cost = usage_rows[0]["provider_cost"] if usage_rows else 0
        total_credits = usage_rows[0]["total_credits"] if usage_rows else 0
        total_events = usage_rows[0]["total_events"] if usage_rows else 0

        total_revenue = sub_revenue_paise + usage_charge
        gross_profit = total_revenue - provider_cost
        gross_margin = round(gross_profit / total_revenue * 100, 2) if total_revenue > 0 else None

        return {
            "subscription_revenue_paise": sub_revenue_paise,
            "subscription_revenue_inr": sub_revenue_paise / 100,
            "calling_revenue_paise": usage_charge,
            "calling_revenue_inr": usage_charge / 100,
            "total_revenue_paise": total_revenue,
            "total_revenue_inr": total_revenue / 100,
            "provider_cost_paise": provider_cost,
            "provider_cost_inr": provider_cost / 100,
            "gross_profit_paise": gross_profit,
            "gross_profit_inr": gross_profit / 100,
            "gross_margin_pct": gross_margin,
            "total_credits_consumed": total_credits,
            "total_usage_events": total_events,
        }

    # ---- ARPU ----

    async def compute_arpu(self) -> dict:
        mrr_data = await self.compute_mrr()
        return {
            "arpu_paise": mrr_data["arpu_paise"],
            "arpu_inr": mrr_data["arpu_inr"],
            "active_subscribers": mrr_data["active_subscribers"],
            "mrr_paise": mrr_data["mrr_paise"],
        }

    # ---- Daily analytics summary (for sparklines) ----

    async def daily_analytics(
        self,
        days: int = 30,
        organization_id: Optional[str] = None,
    ) -> list[dict]:
        """Per-day call/credit analytics for the last N days."""
        end = date.today()
        start = end - timedelta(days=days)

        match: dict = {
            "date": {
                "$gte": start.isoformat(),
                "$lte": end.isoformat(),
            }
        }
        if organization_id:
            match["organization_id"] = organization_id

        pipeline = [
            {"$match": match},
            {"$sort": {"date": 1}},
            {"$project": {
                "_id": 0,
                "date": 1,
                "organization_id": 1,
                "calls_total": {"$ifNull": ["$calls_total", 0]},
                "calls_qualified": {"$ifNull": ["$calls_qualified", 0]},
                "credits_consumed": {"$ifNull": ["$credits_consumed", 0]},
            }},
        ]
        return await self.db["analytics_daily"].aggregate(pipeline).to_list(None)

    # ---- Full analytics report ----

    async def full_report(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> dict:
        """Complete analytics report for the admin dashboard."""
        import asyncio

        mrr_task = self.compute_mrr()
        revenue_task = self.compute_revenue(from_date, to_date)

        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        movement_task = self.compute_mrr_movement(month_start, now)

        mrr, revenue, movement = await asyncio.gather(
            mrr_task, revenue_task, movement_task
        )

        return {
            "mrr": mrr,
            "mrr_movement": movement,
            "revenue": revenue,
            "period": {
                "from": from_date.isoformat() if from_date else None,
                "to": to_date.isoformat() if to_date else None,
            },
        }
