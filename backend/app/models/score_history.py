import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, UUIDPKMixin


class ScoreHistory(UUIDPKMixin, TenantMixin, Base):
    """Database Spec §7.5. Append-only. No write-frequency cap or downsampling job exists
    yet — flagged as an open item (Database Spec §10 item 19) to revisit before Phase 2
    usage volume makes unbounded growth a real storage concern."""

    __tablename__ = "score_history"
    __table_args__ = (
        CheckConstraint("entity_type IN ('organization','customer')", name="entity_type_valid"),
    )

    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(Text, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(nullable=False)
