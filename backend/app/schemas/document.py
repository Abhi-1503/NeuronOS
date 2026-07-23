import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: uuid.UUID
    title: str
    file_type: str
    size_bytes: int | None
    ai_summary: str | None
    visibility: str
    source: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadOut(BaseModel):
    document_id: uuid.UUID
    status: str


class DocumentSearchResultOut(BaseModel):
    id: uuid.UUID
    title: str
    file_type: str
    excerpt: str


class LinkedEntityOut(BaseModel):
    id: uuid.UUID
    source_type: str
    source_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    relationship: str | None
    confidence: float | None
    status: str

    model_config = {"from_attributes": True}


class CreateLinkRequest(BaseModel):
    target_type: str
    target_id: uuid.UUID
    relationship: str | None = None


class RejectLinkRequest(BaseModel):
    correct_target_type: str | None = None
    correct_target_id: uuid.UUID | None = None
