import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import LinkedEntity
from app.models.user import User
from app.repositories.document_repository import DocumentRepository

REVIEW_QUEUE_CONFIDENCE_THRESHOLD = 0.7  # API Spec §5A default


class LinkedEntityNotFoundError(Exception):
    pass


class LinkedEntityService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._documents = DocumentRepository(session)

    async def review_queue(self, *, entity_type: str | None, limit: int) -> list[LinkedEntity]:
        return await self._documents.get_review_queue(
            entity_type=entity_type, confidence_threshold=REVIEW_QUEUE_CONFIDENCE_THRESHOLD, limit=limit
        )

    async def confirm(self, link_id: uuid.UUID, *, user: User) -> LinkedEntity:
        link = await self._documents.get_link_by_id(link_id)
        if link is None:
            raise LinkedEntityNotFoundError()
        link.status = "confirmed"
        link.corrected_by_user_id = user.id
        link.corrected_at = datetime.now(timezone.utc)
        await self._session.flush()
        return link

    async def reject(
        self,
        link_id: uuid.UUID,
        *,
        user: User,
        correct_target_type: str | None,
        correct_target_id: uuid.UUID | None,
    ) -> tuple[LinkedEntity, LinkedEntity | None]:
        link = await self._documents.get_link_by_id(link_id)
        if link is None:
            raise LinkedEntityNotFoundError()
        link.status = "rejected"
        link.corrected_by_user_id = user.id
        link.corrected_at = datetime.now(timezone.utc)

        created = None
        if correct_target_type is not None and correct_target_id is not None:
            created = LinkedEntity(
                organization_id=link.organization_id,
                source_type=link.source_type,
                source_id=link.source_id,
                target_type=correct_target_type,
                target_id=correct_target_id,
                relationship=link.relationship,
                status="manual",
                corrected_by_user_id=user.id,
                corrected_at=datetime.now(timezone.utc),
            )
            self._documents.add_linked_entity(created)

        await self._session.flush()
        return link, created
