import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import REAL, BigInteger, CheckConstraint, ForeignKey, Integer, Text
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


class Document(UUIDPKMixin, TenantMixin, CreatedAtMixin, UpdatedAtMixin, CreatedByMixin, SoftDeleteMixin, Base):
    """Database Spec §5.1."""

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "file_type IN ('pdf','docx','pptx','xlsx','email','other')", name="file_type_valid"
        ),
        CheckConstraint("visibility IN ('org','admin_only','custom')", name="visibility_valid"),
        CheckConstraint("source IN ('manual','integration')", name="source_valid"),
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(Text, nullable=False, default="org")
    source: Mapped[str] = mapped_column(Text, nullable=False, default="manual")


class DocumentChunk(UUIDPKMixin, Base):
    """Database Spec §5.2. Embedding dimensionality (1536) is locked in at the first
    migration touching this table — confirm the embedding model before that migration ships
    (Database Spec §9's hardest-to-reverse schema decision). `embedding` is nullable
    (migration 0003) — a chunk supports keyword search over `content` on its own;
    embeddings are populated only when `OPENAI_API_KEY` is configured (optional at
    Phase 1)."""

    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class DocumentTag(Base):
    """Database Spec §5.3. Composite PK `(document_id, tag)`."""

    __tablename__ = "document_tags"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    tag: Mapped[str] = mapped_column(Text, primary_key=True)


class LinkedEntity(UUIDPKMixin, TenantMixin, CreatedAtMixin, Base):
    """Database Spec §5.4. Polymorphic `(source_type, source_id)` / `(target_type, target_id)`
    pairs — deliberately no FK constraints on those four columns (§7.3); integrity is enforced
    at the application layer plus a periodic consistency-check job."""

    __tablename__ = "linked_entities"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ai_suggested','confirmed','rejected','manual')", name="status_valid"
        ),
    )

    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relationship: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(REAL, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="ai_suggested")
    corrected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    corrected_at: Mapped[datetime | None] = mapped_column(nullable=True)
