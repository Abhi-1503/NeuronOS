import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer, Deal, TimelineEvent
from app.repositories.ai_action_repository import AIActionRepository
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    DealCreate,
    DealUpdate,
    TimelineEventCreate,
)
from app.services.decision_engine import DecisionEngine


class CustomerNotFoundError(Exception):
    pass


class DealNotFoundError(Exception):
    pass


class CustomerService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._customers = CustomerRepository(session)
        self._ai_actions = AIActionRepository(session)
        self._decision_engine = DecisionEngine(session)

    async def create(self, *, organization_id: uuid.UUID, data: CustomerCreate) -> Customer:
        customer = Customer(
            organization_id=organization_id,
            name=data.name,
            owner_user_id=data.owner_user_id,
            status=data.status,
            last_contact_at=data.last_contact_at,
        )
        self._customers.add(customer)
        await self._session.flush()
        # Scored immediately, not left blank until some later batch job — a Path C user
        # (Onboarding Spec §2) adding 5 customers needs a real signal within minutes, and
        # there's no background runner to defer this to yet (Blueprint §8/decision_engine.py).
        await self._decision_engine.evaluate_and_flag(
            customer, organization_id=organization_id, now=datetime.now(timezone.utc)
        )
        return customer

    async def get(self, customer_id: uuid.UUID) -> Customer:
        customer = await self._customers.get_by_id(customer_id)
        if customer is None:
            raise CustomerNotFoundError()
        return customer

    async def list_customers(
        self, *, status: str | None, cursor: uuid.UUID | None, limit: int
    ) -> list[Customer]:
        return await self._customers.list_active(status=status, cursor=cursor, limit=limit)

    async def update(self, customer_id: uuid.UUID, data: CustomerUpdate) -> Customer:
        customer = await self.get(customer_id)
        if data.name is not None:
            customer.name = data.name
        if data.status is not None:
            customer.status = data.status
        if data.owner_user_id is not None:
            customer.owner_user_id = data.owner_user_id
        return customer

    async def soft_delete(self, customer_id: uuid.UUID) -> None:
        customer = await self.get(customer_id)
        customer.deleted_at = datetime.now(timezone.utc)

    async def get_recommended_next_action(self, customer_id: uuid.UUID):
        return await self._ai_actions.get_latest_unactioned_for_entity(
            related_entity_type="customer", related_entity_id=customer_id
        )

    async def add_timeline_event(
        self, customer_id: uuid.UUID, data: TimelineEventCreate
    ) -> TimelineEvent:
        customer = await self.get(customer_id)
        occurred_at = data.occurred_at or datetime.now(timezone.utc)
        event = TimelineEvent(
            organization_id=customer.organization_id,
            customer_id=customer_id,
            event_type=data.event_type,
            title=data.title,
            body=data.body,
            occurred_at=occurred_at,
        )
        await self._customers.add_timeline_event(event)

        # A logged contact event is exactly the kind of data change that should move
        # `last_contact_at` and re-run scoring (Blueprint §14.1-adjacent principle:
        # context that changes should propagate, not sit stale until a page reload).
        if data.event_type in ("meeting", "email", "note", "call") and (
            customer.last_contact_at is None or occurred_at > customer.last_contact_at
        ):
            customer.last_contact_at = occurred_at
        await self._session.flush()
        await self._decision_engine.evaluate_and_flag(
            customer, organization_id=customer.organization_id, now=datetime.now(timezone.utc)
        )
        return event

    async def get_timeline(self, customer_id: uuid.UUID, *, event_type: str | None, limit: int):
        return await self._customers.get_timeline(customer_id, event_type=event_type, limit=limit)

    async def add_deal(self, customer_id: uuid.UUID, data: DealCreate) -> Deal:
        customer = await self.get(customer_id)
        deal = Deal(
            organization_id=customer.organization_id,
            customer_id=customer_id,
            title=data.title,
            stage=data.stage,
            amount=data.amount,
            currency=data.currency,
            expected_close_date=data.expected_close_date,
        )
        self._customers.add_deal(deal)
        await self._session.flush()
        await self._recompute_revenue_total(customer_id)
        return deal

    async def get_deals(self, customer_id: uuid.UUID) -> list[Deal]:
        return await self._customers.get_deals(customer_id)

    async def update_deal(self, customer_id: uuid.UUID, deal_id: uuid.UUID, data: DealUpdate) -> Deal:
        """Gap addressed (surfaced during Phase 1 Reports implementation): no endpoint
        existed anywhere to move a deal out of `proposal` — every deal would stay open
        forever, making revenue reporting meaningless. Moving to `won`/`lost` sets
        `closed_at`; any stage change recomputes the customer's `revenue_total`."""
        deal = await self._customers.get_deal_by_id(deal_id)
        if deal is None or deal.customer_id != customer_id:
            raise DealNotFoundError()

        if data.title is not None:
            deal.title = data.title
        if data.amount is not None:
            deal.amount = data.amount
        if data.expected_close_date is not None:
            deal.expected_close_date = data.expected_close_date
        if data.stage is not None and data.stage != deal.stage:
            deal.stage = data.stage
            deal.closed_at = datetime.now(timezone.utc) if data.stage in ("won", "lost") else None

        await self._session.flush()
        await self._recompute_revenue_total(customer_id)
        return deal

    async def _recompute_revenue_total(self, customer_id: uuid.UUID) -> None:
        """`revenue_total` (Database Spec §2.1) = sum of this customer's non-lost deal
        amounts (open + won) — "how much business this customer represents," not just
        closed-won revenue. Recomputed on every deal change rather than incrementally
        adjusted, since Phase 1 deal volume per customer is small enough that this is
        cheap and it's impossible for it to drift out of sync with the source rows."""
        customer = await self.get(customer_id)
        deals = await self._customers.get_deals(customer_id)
        # `float(...)`, not raw `d.amount`: a `Deal` just created in this same session
        # still holds `amount` as the plain Python float Pydantic parsed (SQLAlchemy
        # doesn't refresh it from the DB — and its `Numeric` type — until something
        # forces a reload), while a `Deal` loaded fresh via this same query returns
        # `decimal.Decimal` for that same column. Summing the two as-is mixes types and
        # raises `TypeError: unsupported operand type(s) for +: 'float' and 'Decimal'`.
        customer.revenue_total = sum(float(d.amount) for d in deals if d.stage != "lost")
