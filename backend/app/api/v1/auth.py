from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_public_db, get_scoped_db, require_role
from app.api.v1.envelope import envelope
from app.models.user import User
from app.schemas.auth import (
    AcceptInviteRequest,
    AuthResponse,
    InviteRequest,
    InviteResponse,
    LoginRequest,
    OrganizationOut,
    RefreshRequest,
    SignupRequest,
    UserOut,
)
from app.services.auth_service import AuthError, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _raise_from(exc: AuthError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"error": {"code": exc.code, "message": exc.message}},
    ) from exc


def _auth_response(organization, user, token: str, refresh_token: str) -> AuthResponse:
    return AuthResponse(
        organization=OrganizationOut.model_validate(organization),
        user=UserOut.model_validate(user),
        token=token,
        refresh_token=refresh_token,
    )


@router.post("/signup", status_code=201)
async def signup(body: SignupRequest, session: AsyncSession = Depends(get_public_db)) -> dict:
    service = AuthService(session)
    try:
        organization, user, token, refresh_token = await service.signup(body)
    except AuthError as exc:
        _raise_from(exc)
    return envelope(_auth_response(organization, user, token, refresh_token))


@router.post("/login")
async def login(body: LoginRequest, session: AsyncSession = Depends(get_public_db)) -> dict:
    service = AuthService(session)
    try:
        organization, user, token, refresh_token = await service.login(body)
    except AuthError as exc:
        _raise_from(exc)
    return envelope(_auth_response(organization, user, token, refresh_token))


@router.post("/logout", status_code=204)
async def logout(user: User = Depends(get_current_user)) -> None:
    """Tokens are stateless JWTs at Phase 0 — there is no server-side revocation list yet,
    so this endpoint's contract is "the client discards its token," not "the token becomes
    unusable before it naturally expires." A revocation/blocklist mechanism is a real gap to
    close before this matters for a security-sensitive session (e.g. a stolen token), flagged
    here rather than silently implied by the 204 response."""
    return None


@router.post("/invite", status_code=201)
async def invite(
    body: InviteRequest,
    user: User = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = AuthService(session)
    try:
        invited_user, _raw_token = await service.invite(
            organization_id=user.organization_id, data=body
        )
    except AuthError as exc:
        _raise_from(exc)
    # Sending the actual invite notification (email) is an integrations/notifications
    # concern out of scope for Phase 0 — _raw_token is where that notification payload
    # would be built from once that piece exists.
    return envelope(
        InviteResponse(invitation_id=invited_user.id, email=invited_user.email, status=invited_user.status)
    )


@router.post("/invitations/{token}/accept")
async def accept_invite(
    token: str, body: AcceptInviteRequest, session: AsyncSession = Depends(get_public_db)
) -> dict:
    service = AuthService(session)
    try:
        organization, user, access_token, refresh_token = await service.accept_invite(
            raw_token=token, data=body
        )
    except AuthError as exc:
        _raise_from(exc)
    return envelope(_auth_response(organization, user, access_token, refresh_token))


@router.post("/refresh")
async def refresh(body: RefreshRequest, session: AsyncSession = Depends(get_public_db)) -> dict:
    service = AuthService(session)
    try:
        token = await service.refresh(body.refresh_token)
    except AuthError as exc:
        _raise_from(exc)
    return envelope({"token": token})
