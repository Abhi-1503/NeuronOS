from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SelectMethodRequest(BaseModel):
    method: str  # "integration" | "documents" | "manual_customers"


class OnboardingStep(BaseModel):
    key: str
    label: str
    completed: bool


class OnboardingStatusOut(BaseModel):
    onboarding_method: str | None
    steps: list[OnboardingStep]
    first_insight_at: datetime | None


class FirstInsightOut(BaseModel):
    type: str  # "risk_flag" | "all_clear"
    message: str
    ai_action_id: UUID | None


class OnboardingCompleteOut(BaseModel):
    onboarding_method: str | None
    steps: list[OnboardingStep]
    first_insight_at: datetime | None
    first_insight: FirstInsightOut | None
