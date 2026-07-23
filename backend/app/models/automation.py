import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Integer, SmallInteger, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
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


class Automation(UUIDPKMixin, TenantMixin, CreatedAtMixin, UpdatedAtMixin, CreatedByMixin, SoftDeleteMixin, Base):
    """Database Spec §6.1. `mode`'s dry_run -> graduating -> live state machine is what
    makes this schema-enforced rather than convention-only (Blueprint §2.3) — no automation
    can be inserted able to skip straight to unsupervised execution."""

    __tablename__ = "automations"
    __table_args__ = (
        CheckConstraint("mode IN ('dry_run','graduating','live','paused')", name="mode_valid"),
        CheckConstraint(
            "trigger_type IN ('invoice_overdue','no_reply_days','project_completed',"
            "'contract_expiring','new_customer')",
            name="trigger_type_valid",
        ),
        # Real FK into action_type_registry (Database Spec §6.1 decision record, resolved
        # during Phase 1 Automations implementation) — matches ai_actions.action_type's
        # pattern, since a graduating-mode automation creates a real ai_actions row using
        # this same value and the two must speak the same vocabulary, not two
        # independently-maintained enums that can silently drift apart.
        ForeignKeyConstraint(["action_type"], ["action_type_registry.action_type"]),
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False, default="dry_run")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    trigger_type: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    action_type: Mapped[str] = mapped_column(Text, nullable=False)
    action_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    graduation_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    approved_run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    times_triggered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_rate_pct: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)


class AutomationRun(UUIDPKMixin, Base):
    """Database Spec §6.2. `UNIQUE (automation_id, idempotency_key)` is the database-level
    guarantee against double-firing a retried trigger (§7.4)."""

    __tablename__ = "automation_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('simulated','success','failed','pending_approval')", name="status_valid"
        ),
    )

    automation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("automations.id", ondelete="CASCADE"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    related_ai_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_actions.id", ondelete="SET NULL"), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_entity_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
