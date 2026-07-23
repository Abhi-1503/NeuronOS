import calendar
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.score_history import ScoreHistory
from app.repositories.ai_action_repository import AIActionRepository
from app.repositories.customer_repository import CustomerRepository
from app.schemas.reports import (
    OverviewOut,
    RevenueBySourceSlice,
    RevenueTrendPoint,
    ScoreHistoryPoint,
    TopCustomerOut,
)

INVOICE_ACTION_TYPES = ("generate_invoice", "send_invoice_reminder")


class ReportsError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _period_bounds(period: str, from_: date | None, to: date | None) -> tuple[date, date]:
    today = datetime.now(timezone.utc).date()
    if period == "custom":
        if from_ is None or to is None:
            raise ReportsError(
                "validation_error", "from and to are required when period=custom.", 422
            )
        return from_, to
    if period == "last_month":
        first_of_this_month = today.replace(day=1)
        last_month_end = first_of_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return last_month_start, last_month_end
    # this_month (default)
    return today.replace(day=1), today


def _previous_equivalent_period(start: date, end: date) -> tuple[date, date]:
    length = (end - start).days
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=length)
    return prev_start, prev_end


def _pct_delta(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0 if current == 0 else 100.0
    return round((current - previous) / previous * 100, 1)


class ReportsService:
    """Reports (Roadmap Phase 1 — 'Static overview: revenue, deals, at-risk count').
    Computed directly from Customers/Deals/AI Actions — no integrations exist yet to
    feed richer data, matching the Roadmap's explicit MVP scope."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._customers = CustomerRepository(session)
        self._ai_actions = AIActionRepository(session)

    async def overview(self, *, period: str, from_: date | None, to: date | None) -> OverviewOut:
        start, end = _period_bounds(period, from_, to)
        prev_start, prev_end = _previous_equivalent_period(start, end)

        all_deals = await self._customers.get_all_deals_for_org()

        def revenue_in(range_start: date, range_end: date) -> float:
            return sum(
                float(d.amount)
                for d in all_deals
                if d.stage == "won"
                and d.closed_at is not None
                and range_start <= d.closed_at.date() <= range_end
            )

        def new_deals_in(range_start: date, range_end: date) -> int:
            return sum(
                1 for d in all_deals if range_start <= d.created_at.date() <= range_end
            )

        total_revenue = revenue_in(start, end)
        prev_revenue = revenue_in(prev_start, prev_end)
        new_deals = new_deals_in(start, end)
        prev_new_deals = new_deals_in(prev_start, prev_end)

        # "Revenue at risk" (mockup: "Revenue At Risk — 12 customers") ties directly to
        # the Decision Engine's actual live signal — customers with a currently-unactioned
        # suggested AI Action — rather than the rarely-set manual `customers.status` field,
        # since that's what's actually driving risk in this product, not a separate manual
        # classification a user would have to remember to maintain.
        flagged_actions = await self._ai_actions.list(status="suggested", assigned_to_user_id=None, cursor=None, limit=1000)
        at_risk_customer_ids = {
            a.related_entity_id for a in flagged_actions if a.related_entity_type == "customer"
        }
        all_customers = await self._customers.list_all_active()
        customers_by_id = {c.id: c for c in all_customers}
        revenue_at_risk = sum(
            float(customers_by_id[cid].revenue_total)
            for cid in at_risk_customer_ids
            if cid in customers_by_id
        )

        # No invoice ledger exists in this schema at all (Database Spec has no `invoices`
        # table) — approximated as the count of still-open AI Actions that *are* about
        # invoicing, which is honest about what's actually tracked rather than fabricating
        # real invoice data. Naturally 0 until Automations (this module) starts generating
        # these action types.
        open_invoices = sum(
            1
            for a in flagged_actions
            if a.action_type in INVOICE_ACTION_TYPES
        )

        return OverviewOut(
            total_revenue=total_revenue,
            new_deals=new_deals,
            revenue_at_risk=revenue_at_risk,
            revenue_at_risk_customer_count=len(at_risk_customer_ids & customers_by_id.keys()),
            open_invoices=open_invoices,
            deltas={
                "total_revenue": _pct_delta(total_revenue, prev_revenue),
                "new_deals": _pct_delta(new_deals, prev_new_deals),
            },
        )

    async def revenue_trend(self) -> list[RevenueTrendPoint]:
        today = datetime.now(timezone.utc).date()
        this_start = today.replace(day=1)
        prev_end = this_start - timedelta(days=1)
        prev_start = prev_end.replace(day=1)
        days_this_month = (today - this_start).days + 1
        days_last_month = calendar.monthrange(prev_start.year, prev_start.month)[1]

        all_deals = await self._customers.get_all_deals_for_org(stage="won")
        won = [d for d in all_deals if d.closed_at is not None]

        points: list[RevenueTrendPoint] = []
        running_this = 0.0
        running_last = 0.0
        for day_index in range(1, max(days_this_month, days_last_month) + 1):
            if day_index <= days_this_month:
                day = this_start + timedelta(days=day_index - 1)
                running_this += sum(float(d.amount) for d in won if d.closed_at.date() == day)
            last_period_value: float | None = None
            if day_index <= days_last_month:
                day2 = prev_start + timedelta(days=day_index - 1)
                running_last += sum(float(d.amount) for d in won if d.closed_at.date() == day2)
                last_period_value = running_last
            points.append(
                RevenueTrendPoint(
                    day_of_period=day_index,
                    this_period=running_this if day_index <= days_this_month else running_this,
                    last_period=last_period_value,
                )
            )
        return points

    async def revenue_by_source(self) -> list[RevenueBySourceSlice]:
        """Buckets by the existing `customers.source` field (`manual` vs `integration`),
        not by acquisition channel (existing/new/referral/other) as the original mockup
        literally shows — that data was never modeled anywhere in this schema, and
        fabricating a plausible-looking breakdown would be worse than an honest,
        differently-labeled one from what's actually tracked."""
        customers = await self._customers.list_all_active()
        totals: dict[str, float] = {}
        for c in customers:
            totals[c.source] = totals.get(c.source, 0.0) + float(c.revenue_total)
        grand_total = sum(totals.values())
        labels = {"manual": "Manually added", "integration": "Synced from integration"}
        return [
            RevenueBySourceSlice(
                label=labels.get(source, source),
                revenue=amount,
                pct=round(amount / grand_total * 100, 1) if grand_total else 0.0,
            )
            for source, amount in totals.items()
        ]

    async def top_customers(self, *, limit: int) -> list[TopCustomerOut]:
        customers = await self._customers.list_all_active()
        deals_by_customer: dict[uuid.UUID, int] = {}
        for c in customers:
            deals = await self._customers.get_deals(c.id)
            deals_by_customer[c.id] = len(deals)
        ranked = sorted(customers, key=lambda c: float(c.revenue_total), reverse=True)[:limit]
        return [
            TopCustomerOut(
                id=c.id,
                name=c.name,
                revenue_total=float(c.revenue_total),
                deal_count=deals_by_customer[c.id],
                relationship_score=c.relationship_score,
            )
            for c in ranked
        ]

    async def score_history(
        self,
        *,
        entity_type: str,
        entity_id: uuid.UUID,
        from_: date | None,
        to: date | None,
    ) -> list[ScoreHistoryPoint]:
        query = select(ScoreHistory).where(
            ScoreHistory.entity_type == entity_type, ScoreHistory.entity_id == entity_id
        )
        if from_:
            query = query.where(ScoreHistory.computed_at >= from_)
        if to:
            query = query.where(ScoreHistory.computed_at <= to)
        query = query.order_by(ScoreHistory.computed_at.asc())
        result = await self._session.execute(query)
        rows = result.scalars().all()
        return [
            ScoreHistoryPoint(score=r.score, algorithm_version=r.algorithm_version, computed_at=r.computed_at)
            for r in rows
        ]
