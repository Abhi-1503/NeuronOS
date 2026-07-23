import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TenantMixin, UpdatedAtMixin, UUIDPKMixin


class Conversation(UUIDPKMixin, TenantMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    """API Spec §6 (AI Workspace). `user_id` scopes "own conversations only" at the
    application layer (migration 0005) — RLS's `tenant_isolation` policy only enforces
    the organization boundary, same as every other tenant-scoped table."""

    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)


class ChatMessage(UUIDPKMixin, Base):
    """API Spec §6. Only indirectly tenant-scoped (via `conversation_id`) — no RLS
    policy of its own, consistent with `document_chunks` relative to `documents`."""

    __tablename__ = "chat_messages"
    __table_args__ = (CheckConstraint("role IN ('user','assistant')", name="role_valid"),)

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
