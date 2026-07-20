import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    organization_name: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = Field(pattern="^(admin|member)$")


class AcceptInviteRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8)


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    email: str
    name: str
    role: str
    status: str

    model_config = {"from_attributes": True}


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    plan: str
    terms_accepted_at: datetime | None = None

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    organization: OrganizationOut
    user: UserOut
    token: str
    refresh_token: str


class InviteResponse(BaseModel):
    invitation_id: uuid.UUID
    email: str
    status: str
