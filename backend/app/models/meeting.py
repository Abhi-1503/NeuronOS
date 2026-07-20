import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, Text
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
from app.models.types import CIText


class Meeting(UUIDPKMixin, TenantMixin, CreatedAtMixin, UpdatedAtMixin, CreatedByMixin, SoftDeleteMixin, Base):
    """Database Spec §4.1. Schema created in Phase 0; no Meetings API/service code until
    Phase 2 (Roadmap). Note: `join_url` is a documented gap (Screen Spec §3, item 1) not yet
    added to the spec — omitted here too, to stay exactly in sync with the Database Spec as
    written rather than silently patching in a column the spec doesn't yet have."""

    __tablename__ = "meetings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('upcoming','brief_ready','completed','needs_notes')", name="status_valid"
        ),
    )

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="upcoming")
    source_calendar_event_id: Mapped[str | None] = mapped_column(Text, nullable=True)


class MeetingAttendee(UUIDPKMixin, Base):
    """Database Spec §4.2. Non-composite PK since a customer contact has no `user_id`."""

    __tablename__ = "meeting_attendees"
    __table_args__ = (
        CheckConstraint("attendee_type IN ('user','customer_contact')", name="attendee_type_valid"),
    )

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    attendee_type: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    customer_contact_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_contact_email: Mapped[str | None] = mapped_column(CIText, nullable=True)


class MeetingSummary(UUIDPKMixin, Base):
    """Database Spec §4.3. One summary per meeting."""

    __tablename__ = "meeting_summaries"

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    talking_points: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    generated_by_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(nullable=False)
    edited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class MeetingActionItem(UUIDPKMixin, Base):
    """Database Spec §4.4."""

    __tablename__ = "meeting_action_items"

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)
