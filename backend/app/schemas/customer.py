import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    owner_user_id: uuid.UUID | None = None
    status: str = Field(default="active", pattern="^(active|at_risk|inactive|churned)$")
    # Onboarding Path C (Onboarding Spec §2) — captured directly since there's no
    # timeline event or integration to derive it from at manual-entry time
    # (API Spec §2 gap note on POST /customers).
    last_contact_at: datetime | None = None


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    status: str | None = Field(default=None, pattern="^(active|at_risk|inactive|churned)$")
    owner_user_id: uuid.UUID | None = None


class RecommendedActionOut(BaseModel):
    id: uuid.UUID
    title: str
    reasoning: str | None
    confidence_score: float | None
    severity_tier: str
    status: str

    model_config = {"from_attributes": True}


class CustomerOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    owner_user_id: uuid.UUID | None
    status: str
    relationship_score: int | None
    score_algorithm_version: str
    revenue_total: float
    currency: str
    last_contact_at: datetime | None
    source: str
    created_at: datetime
    updated_at: datetime
    # No backing column on `customers` (Database Spec §2.1 has no `ai_summary` field) —
    # API Spec §2 documents this response field, but populating it needs a live LLM
    # summarization call, which Phase 1's Action Engine deliberately doesn't make yet
    # (decision_engine.py's `_draft_followup_email` docstring). Always `null` for now,
    # not backed by storage, until that capability actually exists.
    ai_summary: str | None = None
    recommended_next_action: RecommendedActionOut | None = None

    model_config = {"from_attributes": True}


class CustomerSummaryOut(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    relationship_score: int | None
    revenue_total: float
    last_contact_at: datetime | None

    model_config = {"from_attributes": True}


class TimelineEventCreate(BaseModel):
    event_type: str = Field(
        default="note", pattern="^(meeting|email|proposal|invoice|note|contract)$"
    )
    title: str = Field(min_length=1, max_length=500)
    body: str | None = None
    occurred_at: datetime | None = None


class TimelineEventOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    event_type: str
    title: str
    body: str | None
    occurred_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class DealCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    stage: str = Field(default="proposal", pattern="^(proposal|negotiation|won|lost)$")
    amount: float = Field(gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    expected_close_date: date | None = None


class DealUpdate(BaseModel):
    stage: str | None = Field(default=None, pattern="^(proposal|negotiation|won|lost)$")
    title: str | None = Field(default=None, min_length=1, max_length=500)
    amount: float | None = Field(default=None, gt=0)
    expected_close_date: date | None = None


class DealOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    title: str
    stage: str
    amount: float
    currency: str
    expected_close_date: date | None
    closed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
