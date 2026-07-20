import uuid
from datetime import date, datetime

from sqlalchemy import REAL, CheckConstraint, ForeignKey, SmallInteger, Text
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


class Project(UUIDPKMixin, TenantMixin, CreatedAtMixin, UpdatedAtMixin, CreatedByMixin, SoftDeleteMixin, Base):
    """Database Spec §3.1. Schema created in Phase 0 per the "full schema now" decision
    (§9 decision record); no Project API/service-layer code ships until Phase 2 (Roadmap)."""

    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "status IN ('on_track','at_risk','needs_review','in_review','completed')",
            name="status_valid",
        ),
        CheckConstraint("progress_pct BETWEEN 0 AND 100", name="progress_pct_range"),
    )

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="on_track")
    progress_pct: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    deadline: Mapped[date | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)


class ProjectMember(Base):
    """Database Spec §3.2. Composite PK `(project_id, user_id)`."""

    __tablename__ = "project_members"
    __table_args__ = (
        CheckConstraint("role_on_project IN ('lead','contributor','reviewer')", name="role_on_project_valid"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_on_project: Mapped[str] = mapped_column(Text, nullable=False, default="contributor")
    added_at: Mapped[datetime] = mapped_column(nullable=False)


class Task(UUIDPKMixin, TenantMixin, CreatedAtMixin, UpdatedAtMixin, CreatedByMixin, SoftDeleteMixin, Base):
    """Database Spec §3.3."""

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("status IN ('todo','in_progress','blocked','done')", name="status_valid"),
        CheckConstraint(
            "source IN ('manual','meeting_action_item','automation')", name="source_valid"
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="todo")
    due_date: Mapped[date | None] = mapped_column(nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    source_meeting_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True
    )


class RiskFlag(UUIDPKMixin, TenantMixin, CreatedAtMixin, CreatedByMixin, Base):
    """Database Spec §3.4. `reasoning`/`confidence_score` are load-bearing, not optional —
    Blueprint §2.7 requires every AI-generated risk flag to show its reasoning inline."""

    __tablename__ = "risk_flags"
    __table_args__ = (
        CheckConstraint(
            "flag_type IN ('deadline_risk','dependency_blocked','resourcing','budget')",
            name="flag_type_valid",
        ),
        CheckConstraint("severity IN ('low','medium','high')", name="severity_valid"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    flag_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(REAL, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
