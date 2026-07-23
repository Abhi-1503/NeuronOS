import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_scoped_db, require_role
from app.api.v1.envelope import envelope
from app.core.security import create_deletion_confirmation_token, verify_deletion_confirmation_token
from app.models.organization import Organization
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.auth import OrganizationOut
from app.schemas.settings import (
    MemberOut,
    RequestDeletionResponse,
    RequestDpaRequest,
    UpdateMemberRequest,
    UpdateOrganizationRequest,
)
from app.services.decision_engine import DecisionEngine
from app.services.settings_service import SettingsError, SettingsService

router = APIRouter(prefix="/organization", tags=["organization"])


class AcceptTermsRequest(BaseModel):
    version: str = Field(min_length=1)


class DeleteOrganizationRequest(BaseModel):
    confirmation_token: str


class OrganizationProfileOut(BaseModel):
    id: uuid.UUID
    name: str
    industry: str | None
    company_size: str | None
    timezone: str
    plan: str
    business_health_score: int | None
    terms_accepted_version: str | None
    terms_accepted_at: datetime | None
    dpa_signed_at: datetime | None

    model_config = {"from_attributes": True}


def _raise_from(exc: SettingsError):
    raise HTTPException(
        status_code=exc.status_code, detail={"error": {"code": exc.code, "message": exc.message}}
    ) from exc


async def _profile_out(session: AsyncSession, organization: Organization) -> OrganizationProfileOut:
    """Shared by GET and PATCH — both return the *same* full profile shape (API Spec
    §11); PATCH previously returned the smaller `OrganizationOut` (the auth-response
    schema, missing `industry`/`company_size`/etc.), a real bug caught by a test
    actually asserting on the PATCH response body rather than only its status code."""
    score = await DecisionEngine(session).compute_business_health(
        organization_id=organization.id, now=datetime.now(timezone.utc)
    )
    organization.business_health_score = score
    return OrganizationProfileOut(
        id=organization.id,
        name=organization.name,
        industry=organization.industry,
        company_size=organization.company_size,
        timezone=organization.timezone,
        plan=organization.plan,
        business_health_score=score,
        terms_accepted_version=organization.terms_accepted_version,
        terms_accepted_at=organization.terms_accepted_at,
        dpa_signed_at=organization.dpa_signed_at,
    )


@router.get("")
async def get_organization(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    """API Spec §11. `business_health_score` is recomputed on read (see
    DecisionEngine.compute_business_health's docstring for why that's fine at Phase 1
    scale) rather than served from a stale cached column."""
    repo = OrganizationRepository(session)
    organization = await repo.get_by_id(user.organization_id)
    assert organization is not None
    return envelope(await _profile_out(session, organization))


@router.patch("")
async def update_organization(
    body: UpdateOrganizationRequest,
    user: User = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = SettingsService(session)
    organization = await service.update_organization(user.organization_id, body)
    return envelope(await _profile_out(session, organization))


@router.get("/members")
async def list_members(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = SettingsService(session)
    members = await service.list_members()
    return envelope([MemberOut.model_validate(m) for m in members])


@router.patch("/members/{user_id}")
async def update_member(
    user_id: uuid.UUID,
    body: UpdateMemberRequest,
    acting_user: User = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = SettingsService(session)
    try:
        member = await service.update_member(user_id, body, acting_user=acting_user)
    except SettingsError as exc:
        _raise_from(exc)
    return envelope(MemberOut.model_validate(member))


@router.post("/accept-terms")
async def accept_terms(
    body: AcceptTermsRequest,
    user: User = Depends(require_role("owner")),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    """API Spec §11. Blocking step in the signup flow (Blueprint §17.8) — the org's Owner
    accepts the AI-action liability terms before the rest of the product unlocks. Owner-only:
    the Terms are accepted on behalf of the organization by its Owner, not by any member."""
    repo = OrganizationRepository(session)
    organization = await repo.get_by_id(user.organization_id)
    assert organization is not None
    organization.terms_accepted_version = body.version
    organization.terms_accepted_at = datetime.now(timezone.utc)
    return envelope(OrganizationOut.model_validate(organization))


@router.post("/request-dpa", status_code=202)
async def request_dpa(
    body: RequestDpaRequest,
    user: User = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = SettingsService(session)
    await service.request_dpa(organization_id=user.organization_id, data=body)
    return envelope({"status": "request_received"})


@router.post("/request-deletion")
async def request_deletion(
    user: User = Depends(require_role("owner")),
) -> dict:
    """API Spec §11 Danger Zone — step one of the required two-step confirmation before
    `DELETE /organization` (below) will act. Owner-only, matching the destructive
    action itself."""
    token, expires_at = create_deletion_confirmation_token(
        organization_id=str(user.organization_id), requested_by_user_id=str(user.id)
    )
    return envelope(RequestDeletionResponse(confirmation_token=token, expires_at=expires_at))


@router.delete("", status_code=204)
async def delete_organization(
    body: DeleteOrganizationRequest,
    user: User = Depends(require_role("owner")),
    session: AsyncSession = Depends(get_scoped_db),
) -> None:
    """API Spec §11 — hard delete, cascading per Database Spec §1.1. Requires a token
    from `POST /organization/request-deletion` issued to *this specific* user for *this
    specific* org (Database Spec §0.1 note: `organizations` carries no RLS policy of its
    own — it's the tenant root, not a tenant-scoped table — so this check is the only
    thing standing between a valid token and deleting the wrong organization; there is
    no path parameter here at all precisely to keep the only "which org" input the
    caller's own authenticated token, never a client-supplied value)."""
    if not verify_deletion_confirmation_token(
        body.confirmation_token, organization_id=str(user.organization_id), user_id=str(user.id)
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "validation_error",
                    "message": "Invalid or expired confirmation token — request a new one.",
                }
            },
        )
    await session.execute(delete(Organization).where(Organization.id == user.organization_id))
