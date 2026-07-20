import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    CreatedAtMixin,
    SoftDeleteMixin,
    TenantMixin,
    UpdatedAtMixin,
    UUIDPKMixin,
)
from app.models.types import CIText


class User(UUIDPKMixin, TenantMixin, CreatedAtMixin, UpdatedAtMixin, SoftDeleteMixin, Base):
    """Database Spec §1.2. `email` is globally unique (decision record, §1.2) — resolved
    during Phase 0 implementation in favor of making `POST /auth/login` unambiguous, since
    multi-org-per-person is out of scope for MVP."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('owner','admin','member')", name="role_valid"),
        CheckConstraint("status IN ('invited','active','suspended')", name="status_valid"),
    )

    email: Mapped[str] = mapped_column(CIText, nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False, default="member")
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    invitation_token_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    invitation_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="invited")
