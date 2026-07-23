import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UpdateOrganizationRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    industry: str | None = None
    company_size: str | None = Field(default=None, pattern="^(1-10|11-50|51-250|251\\+)$")
    timezone: str | None = None


class MemberOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str
    status: str
    last_login_at: datetime | None

    model_config = {"from_attributes": True}


class UpdateMemberRequest(BaseModel):
    role: str | None = Field(default=None, pattern="^(admin|member)$")
    status: str | None = Field(default=None, pattern="^(active|suspended)$")


class RequestDpaRequest(BaseModel):
    requested_by_email: EmailStr | None = None
    notes: str | None = None


class RequestDeletionResponse(BaseModel):
    confirmation_token: str
    expires_at: datetime


class IntegrationOut(BaseModel):
    provider: str
    status: str
    provider_review_status: str
    last_synced_at: datetime | None
