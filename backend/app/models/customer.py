import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    CreatedAtMixin,
    CreatedByMixin,
    SoftDeleteMixin,
    TenantMixin,
    UpdatedAtMixin,
    UUIDPKMixin,
)


class Customer(UUIDPKMixin, TenantMixin, CreatedAtMixin, UpdatedAtMixin, CreatedByMixin, SoftDeleteMixin, Base):
    """Database Spec §2.1."""

    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("status IN ('active','at_risk','inactive','churned')", name="status_valid"),
        CheckConstraint("source IN ('manual','integration')", name="source_valid"),
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    relationship_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    score_algorithm_version: Mapped[str] = mapped_column(Text, nullable=False, default="v1_rule_based")
    revenue_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(Text, nullable=False, default="INR")
    last_contact_at: Mapped[datetime | None] = mapped_column(nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    source_integration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integration_connections.id"), nullable=True
    )


class TimelineEvent(UUIDPKMixin, TenantMixin, CreatedAtMixin, CreatedByMixin, Base):
    """Database Spec §2.2. Append-only — no `updated_at`, no soft delete; cascades on
    customer delete only."""

    __tablename__ = "timeline_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('meeting','email','proposal','invoice','note','contract')",
            name="event_type_valid",
        ),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)
    linked_entity_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class Deal(UUIDPKMixin, TenantMixin, CreatedAtMixin, UpdatedAtMixin, CreatedByMixin, SoftDeleteMixin, Base):
    """Database Spec §2.3."""

    __tablename__ = "deals"
    __table_args__ = (
        CheckConstraint("stage IN ('proposal','negotiation','won','lost')", name="stage_valid"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    stage: Mapped[str] = mapped_column(Text, nullable=False, default="proposal")
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False, default="INR")
    expected_close_date: Mapped[date | None] = mapped_column(nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)
