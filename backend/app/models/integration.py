import uuid
from datetime import datetime

from sqlalchemy import ARRAY, CheckConstraint, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, SoftDeleteMixin, TenantMixin, UpdatedAtMixin, UUIDPKMixin


class IntegrationConnection(UUIDPKMixin, TenantMixin, CreatedAtMixin, UpdatedAtMixin, SoftDeleteMixin, Base):
    """Database Spec §8.1. Token encryption keys are managed outside the database (KMS/secrets
    manager per Blueprint §17.5) — this model stores only the already-encrypted ciphertext,
    never plaintext, and never the encryption key itself."""

    __tablename__ = "integration_connections"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('gmail','google_drive','google_calendar','outlook','microsoft_365',"
            "'slack','whatsapp','hubspot','salesforce','zoho_crm','zoho_books','quickbooks')",
            name="provider_valid",
        ),
        CheckConstraint(
            "status IN ('connected','sync_error','disconnected')", name="status_valid"
        ),
        CheckConstraint(
            "provider_review_status IN ('not_submitted','in_review','approved','rejected')",
            name="provider_review_status_valid",
        ),
    )

    provider: Mapped[str] = mapped_column(Text, nullable=False)
    connected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    scopes: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="connected")
    last_synced_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_review_status: Mapped[str] = mapped_column(Text, nullable=False, default="not_submitted")
