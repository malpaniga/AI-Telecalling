"""Revenue and Margin Analytics API — admin only.

GET /api/v1/analytics/mrr              — current MRR + ARR + ARPU
GET /api/v1/analytics/mrr-movement     — new/expansion/churn MRR
GET /api/v1/analytics/revenue          — subscription + calling revenue breakdown
GET /api/v1/analytics/costs            — provider cost breakdown (admin only)
GET /api/v1/analytics/margins          — gross profit + margin
GET /api/v1/analytics/arpu             — average revenue per user
GET /api/v1/analytics/daily            — per-day call/credit chart data
GET /api/v1/analytics/report           — full analytics report
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from backend.core.rbac import require_platform
from backend.core.db import get_db
from backend.services.analytics_service import AnalyticsService

log = logging.getLogger("api.analytics")
router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(require_platform())],
)


@router.get("/mrr")
async def get_mrr():
    """Current MRR, ARR estimate, and ARPU. Admin only."""
    return await AnalyticsService(get_db()).compute_mrr()


@router.get("/mrr-movement")
async def get_mrr_movement(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
):
    """New / expansion / churn MRR for a period."""
    from datetime import timezone
    now = datetime.now(timezone.utc)
    fd = from_date or datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    td = to_date or now
    return await AnalyticsService(get_db()).compute_mrr_movement(fd, td)


@router.get("/revenue")
async def get_revenue(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
):
    """Subscription + calling revenue with provider costs and gross margin."""
    return await AnalyticsService(get_db()).compute_revenue(from_date, to_date)


@router.get("/costs")
async def get_costs(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
):
    """Provider cost breakdown. Admin only — never expose to customers."""
    data = await AnalyticsService(get_db()).compute_revenue(from_date, to_date)
    return {
        "provider_cost_paise": data["provider_cost_paise"],
        "provider_cost_inr": data["provider_cost_inr"],
        "total_revenue_paise": data["total_revenue_paise"],
        "gross_profit_paise": data["gross_profit_paise"],
        "gross_margin_pct": data["gross_margin_pct"],
    }


@router.get("/margins")
async def get_margins(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
):
    """Gross profit and margin. Admin only."""
    data = await AnalyticsService(get_db()).compute_revenue(from_date, to_date)
    return {
        "gross_profit_paise": data["gross_profit_paise"],
        "gross_profit_inr": data["gross_profit_inr"],
        "gross_margin_pct": data["gross_margin_pct"],
        "total_revenue_paise": data["total_revenue_paise"],
        "provider_cost_paise": data["provider_cost_paise"],
    }


@router.get("/arpu")
async def get_arpu():
    """Average Revenue Per User."""
    return await AnalyticsService(get_db()).compute_arpu()


@router.get("/daily")
async def get_daily_analytics(
    days: int = Query(default=30, ge=1, le=365),
    organization_id: Optional[str] = None,
):
    """Per-day analytics for charts. Optionally filtered by org."""
    daily = await AnalyticsService(get_db()).daily_analytics(
        days=days, organization_id=organization_id
    )
    return {"days": days, "data": daily}


@router.get("/report")
async def get_full_report(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
):
    """Full analytics report: MRR + movement + revenue + margins."""
    return await AnalyticsService(get_db()).full_report(from_date, to_date)
