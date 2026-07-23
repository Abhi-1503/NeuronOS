import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer, Deal, TimelineEvent


class CustomerRepository:
    """Data access for `customers`. RLS (Database Spec §0.1) enforces org-scoping at the
    database layer — every query here still filters `deleted_at IS NULL` explicitly, since
    soft-delete filtering is an application-layer convention RLS doesn't know about."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, customer_id: uuid.UUID) -> Customer | None:
        result = await self._session.execute(
            select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_active(
        self, *, status: str | None = None, cursor: uuid.UUID | None = None, limit: int = 25
    ) -> list[Customer]:
        query = select(Customer).where(Customer.deleted_at.is_(None))
        if status:
            query = query.where(Customer.status == status)
        if cursor:
            query = query.where(Customer.id > cursor)
        query = query.order_by(Customer.id).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    def add(self, customer: Customer) -> None:
        self._session.add(customer)

    async def add_timeline_event(self, event: TimelineEvent) -> None:
        self._session.add(event)

    async def get_timeline(
        self, customer_id: uuid.UUID, *, event_type: str | None = None, limit: int = 25
    ) -> list[TimelineEvent]:
        query = select(TimelineEvent).where(TimelineEvent.customer_id == customer_id)
        if event_type:
            query = query.where(TimelineEvent.event_type == event_type)
        query = query.order_by(TimelineEvent.occurred_at.desc()).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_latest_timeline_event_at(self, customer_id: uuid.UUID) -> datetime | None:
        result = await self._session.execute(
            select(TimelineEvent.occurred_at)
            .where(TimelineEvent.customer_id == customer_id)
            .order_by(TimelineEvent.occurred_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def add_deal(self, deal: Deal) -> None:
        self._session.add(deal)

    async def get_deals(self, customer_id: uuid.UUID) -> list[Deal]:
        result = await self._session.execute(
            select(Deal)
            .where(Deal.customer_id == customer_id, Deal.deleted_at.is_(None))
            .order_by(Deal.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_deal_by_id(self, deal_id: uuid.UUID) -> Deal | None:
        result = await self._session.execute(
            select(Deal).where(Deal.id == deal_id, Deal.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_all_deals_for_org(self, *, stage: str | None = None) -> list[Deal]:
        """Org-wide (RLS-scoped, not filtered by customer_id) — backs Reports aggregates."""
        query = select(Deal).where(Deal.deleted_at.is_(None))
        if stage:
            query = query.where(Deal.stage == stage)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def count_active(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Customer).where(Customer.deleted_at.is_(None))
        )
        return result.scalar_one()

    async def list_all_active(self) -> list[Customer]:
        """Unpaginated — for Reports aggregation, not list-view display."""
        result = await self._session.execute(
            select(Customer).where(Customer.deleted_at.is_(None))
        )
        return list(result.scalars().all())
