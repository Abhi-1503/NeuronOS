import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    message: str = Field(min_length=1)


class CitationOut(BaseModel):
    type: str
    id: uuid.UUID
    excerpt: str


class ChatMessageOut(BaseModel):
    role: str
    content: str
    citations: list[CitationOut]


class SendMessageResponse(BaseModel):
    conversation_id: uuid.UUID
    message: ChatMessageOut


class ConversationSummaryOut(BaseModel):
    id: uuid.UUID
    title: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageHistoryOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    citations: list[CitationOut]
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailOut(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageHistoryOut]

    model_config = {"from_attributes": True}
