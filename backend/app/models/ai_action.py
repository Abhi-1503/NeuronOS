import uuid
from datetime import datetime

from sqlalchemy import REAL, CheckConstraint, ForeignKey, ForeignKeyConstraint, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TenantMixin, UpdatedAtMixin, UUIDPKMixin


class ActionTypeRegistry(Base):
    """Database Spec §7.1. The single source of truth for which `action_type` values exist
    and what severity/reversibility each carries — `ai_actions.action_type` is a real FK into
    this table (not a freeform column), so an engine cannot insert an unregistered action type
    or set severity/reversibility incorrectly per instance."""

    __tablename__ = "action_type_registry"
    __table_args__ = (
        CheckConstraint("severity_tier IN ('low','medium','high')", name="severity_tier_valid"),
    )

    action_type: Mapped[str] = mapped_column(Text, primary_key=True)
    severity_tier: Mapped[str] = mapped_column(Text, nullable=False)
    is_reversible: Mapped[bool] = mapped_column(nullable=False)


class AIAction(UUIDPKMixin, TenantMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    """Database Spec §7.1. No soft delete — history is kept permanently for the Learning
    Engine. `reasoning`/`confidence_score` must be rendered visibly by the frontend, not
    behind a "why?" click (Blueprint §2.7) — that's a product requirement this schema
    supports, not one it can enforce by itself."""

    __tablename__ = "ai_actions"
    __table_args__ = (
        CheckConstraint("severity_tier IN ('low','medium','high')", name="severity_tier_valid"),
        CheckConstraint("priority IN ('low','medium','high')", name="priority_valid"),
        CheckConstraint(
            "status IN ('suggested','approved','rejected','delegated','executed','failed')",
            name="status_valid",
        ),
        ForeignKeyConstraint(["action_type"], ["action_type_registry.action_type"]),
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity_tier: Mapped[str] = mapped_column(Text, nullable=False, default="low")
    is_reversible: Mapped[bool] = mapped_column(nullable=False, default=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(REAL, nullable=True)
    priority: Mapped[str] = mapped_column(Text, nullable=False, default="medium")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="suggested")
    suggested_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    related_entity_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    delegated_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    generated_by_engine: Mapped[str] = mapped_column(Text, nullable=False)


class AIActionExecution(UUIDPKMixin, Base):
    """Database Spec §7.2. Execution audit log required by Blueprint §17.4."""

    __tablename__ = "ai_action_executions"
    __table_args__ = (
        CheckConstraint("result IN ('success','failed')", name="result_valid"),
    )

    ai_action_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_actions.id", ondelete="CASCADE"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    executed_action: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(nullable=False)
