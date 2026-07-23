import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk, DocumentTag, LinkedEntity


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, document: Document) -> None:
        self._session.add(document)

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        result = await self._session.execute(
            select(Document).where(Document.id == document_id, Document.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_content_hash(
        self, organization_id: uuid.UUID, content_hash: str
    ) -> Document | None:
        result = await self._session.execute(
            select(Document).where(
                Document.organization_id == organization_id,
                Document.content_hash == content_hash,
                Document.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_tags(self, document_id: uuid.UUID) -> list[str]:
        result = await self._session.execute(
            select(DocumentTag.tag).where(DocumentTag.document_id == document_id)
        )
        return list(result.scalars().all())

    def add_tag(self, document_id: uuid.UUID, tag: str) -> None:
        self._session.add(DocumentTag(document_id=document_id, tag=tag))

    def add_chunk(self, chunk: DocumentChunk) -> None:
        self._session.add(chunk)

    async def keyword_search(
        self, query: str, *, limit: int = 20, include_admin_only: bool = True
    ) -> list[tuple[Document, str]]:
        """Hybrid-ish keyword search (API Spec §5): title ILIKE match always considered;
        chunk-content ILIKE match surfaces the matching document with that chunk's text
        as the excerpt. Real Postgres `ILIKE`, not an in-memory filter — this scales to
        realistic Phase 1 document counts without pulling every row into Python first.

        `include_admin_only=False` excludes `visibility='admin_only'` documents at the
        query level (Blueprint §5.3's hard requirement that AI-surfaced content never
        leak outside the requester's visibility scope — this is the same check
        `GET /documents/{id}` applies, just enforced before the row is even fetched
        rather than as a post-hoc 403)."""
        pattern = f"%{query}%"
        conditions = [Document.deleted_at.is_(None), Document.title.ilike(pattern)]
        if not include_admin_only:
            conditions.append(Document.visibility != "admin_only")
        title_matches = await self._session.execute(select(Document).where(*conditions).limit(limit))
        results: list[tuple[Document, str]] = [
            (doc, doc.ai_summary or "") for doc in title_matches.scalars().all()
        ]
        seen_ids = {doc.id for doc, _ in results}

        chunk_conditions = [Document.deleted_at.is_(None), DocumentChunk.content.ilike(pattern)]
        if not include_admin_only:
            chunk_conditions.append(Document.visibility != "admin_only")
        chunk_matches = await self._session.execute(
            select(DocumentChunk, Document)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(*chunk_conditions)
            .limit(limit)
        )
        for chunk, doc in chunk_matches.all():
            if doc.id not in seen_ids:
                results.append((doc, chunk.content[:300]))
                seen_ids.add(doc.id)

        return results[:limit]

    async def list_active(self, *, limit: int = 25) -> list[Document]:
        result = await self._session.execute(
            select(Document)
            .where(Document.deleted_at.is_(None))
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_active(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Document).where(Document.deleted_at.is_(None))
        )
        return result.scalar_one()

    def add_linked_entity(self, link: LinkedEntity) -> None:
        self._session.add(link)

    async def get_links_for_document(self, document_id: uuid.UUID) -> list[LinkedEntity]:
        result = await self._session.execute(
            select(LinkedEntity).where(
                LinkedEntity.source_type == "document", LinkedEntity.source_id == document_id
            )
        )
        return list(result.scalars().all())

    async def get_link_by_id(self, link_id: uuid.UUID) -> LinkedEntity | None:
        return await self._session.get(LinkedEntity, link_id)

    async def get_review_queue(
        self, *, entity_type: str | None, confidence_threshold: float, limit: int
    ) -> list[LinkedEntity]:
        query = select(LinkedEntity).where(
            LinkedEntity.status == "ai_suggested",
            LinkedEntity.confidence < confidence_threshold,
        )
        if entity_type:
            query = query.where(
                (LinkedEntity.source_type == entity_type) | (LinkedEntity.target_type == entity_type)
            )
        query = query.order_by(LinkedEntity.created_at.desc()).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())
