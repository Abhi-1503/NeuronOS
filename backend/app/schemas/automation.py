import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AutomationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    trigger_type: str = Field(
        pattern="^(invoice_overdue|no_reply_days|project_completed|contract_expiring|new_customer)$"
    )
    trigger_config: dict
    # Matches action_type_registry (Database Spec §6.1 decision record) — a graduating-mode
    # automation creates a real ai_actions row using this exact value, so it must be one
    # action_type_registry actually knows, not a separately-maintained list that can drift.
    action_type: str = Field(
        pattern="^(send_followup_email|create_task|prepare_meeting_brief|send_contract_email|generate_invoice|send_invoice_reminder)$"
    )
    action_config: dict = Field(default_factory=dict)
    is_active: bool = True


class AutomationUpdate(BaseModel):
    is_active: bool | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)


class PromoteModeRequest(BaseModel):
    mode: str = Field(pattern="^(dry_run|graduating|live|paused)$")
    reason: str | None = None


class AutomationOut(BaseModel):
    id: uuid.UUID
    name: str
    mode: str
    is_active: bool
    trigger_type: str
    trigger_config: dict
    action_type: str
    action_config: dict
    graduation_threshold: int
    approved_run_count: int
    times_triggered: int
    success_rate_pct: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AutomationRunOut(BaseModel):
    id: uuid.UUID
    automation_id: uuid.UUID
    triggered_at: datetime
    status: str
    related_ai_action_id: uuid.UUID | None
    error_message: str | None
    target_entity_type: str | None
    target_entity_id: uuid.UUID | None

    model_config = {"from_attributes": True}
