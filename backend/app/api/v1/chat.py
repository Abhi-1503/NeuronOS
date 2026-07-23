import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_scoped_db
from app.api.v1.envelope import envelope
from app.models.user import User
from app.schemas.chat import (
    ChatMessageOut,
    ConversationDetailOut,
    ConversationSummaryOut,
    SendMessageRequest,
    SendMessageResponse,
)
from app.services.chat_service import (
    ChatService,
    ConversationAccessDeniedError,
    ConversationNotFoundError,
)

router = APIRouter(prefix="/chat", tags=["chat"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=404, detail={"error": {"code": "not_found", "message": "Conversation not found."}}
    )


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={"error": {"code": "permission_denied", "message": "Not your conversation."}},
    )


@router.post("/messages")
async def send_message(
    body: SendMessageRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = ChatService(session)
    try:
        conversation, assistant_message = await service.send_message(
            organization_id=user.organization_id,
            user_id=user.id,
            include_admin_only=user.role in ("owner", "admin"),
            conversation_id=body.conversation_id,
            message=body.message,
        )
    except ConversationNotFoundError:
        raise _not_found()
    except ConversationAccessDeniedError:
        raise _forbidden()
    return envelope(
        SendMessageResponse(
            conversation_id=conversation.id,
            message=ChatMessageOut(
                role="assistant",
                content=assistant_message.content,
                citations=assistant_message.citations or [],
            ),
        )
    )


@router.get("/conversations")
async def list_conversations(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = ChatService(session)
    conversations = await service.list_conversations(user.id)
    return envelope([ConversationSummaryOut.model_validate(c) for c in conversations])


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = ChatService(session)
    try:
        conversation, messages = await service.get_conversation_detail(
            conversation_id, user_id=user.id
        )
    except ConversationNotFoundError:
        raise _not_found()
    except ConversationAccessDeniedError:
        raise _forbidden()
    return envelope(
        ConversationDetailOut(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=[
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "citations": m.citations or [],
                    "created_at": m.created_at,
                }
                for m in messages
            ],
        )
    )
