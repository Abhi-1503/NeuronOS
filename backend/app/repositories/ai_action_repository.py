import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_action import AIAction, AIActionExecution


class AIActionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, action: AIAction) -> None:
        self._session.add(action)

    async def get_by_id(self, action_id: uuid.UUID) -> AIAction | None:
        return await self._session.get(AIAction, action_id)

    async def list(
        self,
        *,
        status: str | None = None,
        assigned_to_user_id: uuid.UUID | None = None,
        cursor: uuid.UUID | None = None,
        limit: int = 25,
    ) -> list[AIAction]:
        query = select(AIAction)
        if status:
            query = query.where(AIAction.status == status)
        if assigned_to_user_id:
            query = query.where(AIAction.assigned_to_user_id == assigned_to_user_id)
        if cursor:
            query = query.where(AIAction.id > cursor)
        query = query.order_by(AIAction.id).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_latest_unactioned_for_entity(
        self, *, related_entity_type: str, related_entity_id: uuid.UUID
    ) -> AIAction | None:
        result = await self._session.execute(
            select(AIAction)
            .where(
                AIAction.related_entity_type == related_entity_type,
                AIAction.related_entity_id == related_entity_id,
                AIAction.status == "suggested",
            )
            .order_by(AIAction.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_execution_by_idempotency_key(
        self, idempotency_key: str
    ) -> AIActionExecution | None:
        result = await self._session.execute(
            select(AIActionExecution).where(
                AIActionExecution.idempotency_key == idempotency_key
            )
        )
        return result.scalar_one_or_none()

    def add_execution(self, execution: AIActionExecution) -> None:
        self._session.add(execution)
