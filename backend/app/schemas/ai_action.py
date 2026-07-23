import uuid
from datetime import datetime

from pydantic import BaseModel


class AIActionOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    title: str
    description: str | None
    action_type: str
    severity_tier: str
    is_reversible: bool
    reasoning: str | None
    confidence_score: float | None
    priority: str
    status: str
    suggested_amount: float | None
    related_entity_type: str | None
    related_entity_id: uuid.UUID | None
    assigned_to_user_id: uuid.UUID | None
    delegated_to_user_id: uuid.UUID | None
    decided_by_user_id: uuid.UUID | None
    decided_at: datetime | None
    executed_at: datetime | None
    generated_by_engine: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApproveRequest(BaseModel):
    edited_content: dict | None = None
    confirm_high_severity: bool | None = None


class RejectRequest(BaseModel):
    reason: str | None = None


class DelegateRequest(BaseModel):
    delegated_to_user_id: uuid.UUID
