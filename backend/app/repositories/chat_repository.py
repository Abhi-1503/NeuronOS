import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, Conversation


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add_conversation(self, conversation: Conversation) -> None:
        self._session.add(conversation)

    async def get_conversation(self, conversation_id: uuid.UUID) -> Conversation | None:
        return await self._session.get(Conversation, conversation_id)

    async def list_for_user(self, user_id: uuid.UUID, *, limit: int = 25) -> list[Conversation]:
        result = await self._session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    def add_message(self, message: ChatMessage) -> None:
        self._session.add(message)

    async def get_messages(self, conversation_id: uuid.UUID) -> list[ChatMessage]:
        result = await self._session.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at)
        )
        return list(result.scalars().all())
