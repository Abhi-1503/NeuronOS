import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk, LinkedEntity
from app.repositories.customer_repository import CustomerRepository
from app.repositories.document_repository import DocumentRepository
from app.services.embedding_service import EmbeddingService
from app.services.storage import StorageBackend
from app.services.summarization_service import SummarizationService
from app.services.text_extraction import UnsupportedFileTypeError, chunk_text, extract_text

ALLOWED_FILE_TYPES = ("pdf", "docx", "pptx", "xlsx", "email", "other")
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB, per API Spec §5's placeholder limit

# Rule-based linking confidence (Blueprint §14's "rule-based, not ML" MVP philosophy
# applied to Context Engine too, not just Decision Engine) — a name-substring match is
# a real signal, but a weak one, so it lands well below the review-queue threshold
# (0.7, API Spec §5A) and always needs human confirmation before anything downstream
# trusts it (Blueprint §14.1's hard rule).
NAME_MATCH_CONFIDENCE = 0.55


class DocumentNotFoundError(Exception):
    pass


class DocumentError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class DocumentService:
    def __init__(self, session: AsyncSession, storage: StorageBackend) -> None:
        self._session = session
        self._storage = storage
        self._documents = DocumentRepository(session)
        self._customers = CustomerRepository(session)
        self._embeddings = EmbeddingService()
        self._summarizer = SummarizationService()

    async def upload(
        self,
        *,
        organization_id: uuid.UUID,
        title: str,
        file_type: str,
        content: bytes,
        visibility: str,
        force: bool = False,
    ) -> Document:
        if file_type not in ALLOWED_FILE_TYPES:
            raise DocumentError(
                "validation_error", f"file_type must be one of {ALLOWED_FILE_TYPES}.", 422
            )
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise DocumentError("validation_error", "File exceeds the 50MB limit.", 422)

        # Content-hash duplicate detection (API Spec §0.5's note on POST /documents) —
        # a genuinely different logical upload of the same bytes is caught here, which
        # an Idempotency-Key alone (protecting only a *retried* request) cannot catch.
        content_hash = hashlib.sha256(content).hexdigest()
        if not force:
            existing = await self._documents.get_by_content_hash(organization_id, content_hash)
            if existing is not None:
                raise DocumentError(
                    "duplicate_content",
                    f"This file matches an existing document, '{existing.title}' "
                    f"({existing.id}). Pass force=true to upload it anyway as a separate document.",
                    409,
                )

        storage_key = await self._storage.save(
            organization_id=organization_id, filename=title, content=content
        )

        document = Document(
            organization_id=organization_id,
            title=title,
            file_type=file_type,
            storage_key=storage_key,
            size_bytes=len(content),
            content_hash=content_hash,
            visibility=visibility,
        )
        self._documents.add(document)
        await self._session.flush()

        try:
            extracted_text = extract_text(file_type=file_type, content=content)
        except UnsupportedFileTypeError:
            extracted_text = ""

        if extracted_text.strip():
            document.ai_summary = await self._summarizer.summarize(title=title, text=extracted_text)
            now = datetime.now(timezone.utc)
            for index, chunk_content in enumerate(chunk_text(extracted_text)):
                embedding = await self._embeddings.embed(chunk_content)
                self._documents.add_chunk(
                    DocumentChunk(
                        document_id=document.id,
                        chunk_index=index,
                        content=chunk_content,
                        embedding=embedding,
                        created_at=now,
                    )
                )

        await self._link_mentioned_customers(document, extracted_text, title)
        await self._session.flush()
        return document

    async def _link_mentioned_customers(self, document: Document, text: str, title: str) -> None:
        """Rule-based Context Engine v1 (Blueprint §14.1): a case-insensitive name
        substring match against every active customer. Deliberately conservative — every
        match is `status='ai_suggested'` at a below-review-threshold confidence, so
        nothing downstream (Blueprint §14.1's hard rule) weights it until a human
        confirms it via the review queue."""
        haystack = f"{title}\n{text}".lower()
        customers = await self._customers.list_all_active()
        for customer in customers:
            if customer.name.lower() in haystack:
                self._documents.add_linked_entity(
                    LinkedEntity(
                        organization_id=document.organization_id,
                        source_type="document",
                        source_id=document.id,
                        target_type="customer",
                        target_id=customer.id,
                        relationship="mentions",
                        confidence=NAME_MATCH_CONFIDENCE,
                        status="ai_suggested",
                    )
                )

    async def get(self, document_id: uuid.UUID) -> Document:
        document = await self._documents.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError()
        return document

    async def get_tags(self, document_id: uuid.UUID) -> list[str]:
        return await self._documents.get_tags(document_id)

    async def list_documents(self, *, limit: int) -> list[Document]:
        return await self._documents.list_active(limit=limit)

    async def search(
        self, query: str, *, limit: int, include_admin_only: bool = True
    ) -> list[tuple[Document, str]]:
        return await self._documents.keyword_search(
            query, limit=limit, include_admin_only=include_admin_only
        )

    async def soft_delete(self, document_id: uuid.UUID) -> None:
        document = await self.get(document_id)
        document.deleted_at = datetime.now(timezone.utc)

    async def create_link(
        self, document_id: uuid.UUID, *, target_type: str, target_id: uuid.UUID, relationship: str | None
    ) -> LinkedEntity:
        document = await self.get(document_id)
        link = LinkedEntity(
            organization_id=document.organization_id,
            source_type="document",
            source_id=document_id,
            target_type=target_type,
            target_id=target_id,
            relationship=relationship,
            status="manual",
        )
        self._documents.add_linked_entity(link)
        await self._session.flush()
        return link
