from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_invitation_token,
    hash_invitation_token,
    hash_password,
    verify_password,
)
from app.models.organization import Organization
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AcceptInviteRequest, InviteRequest, LoginRequest, SignupRequest


class AuthError(Exception):
    """Raised for auth failures the API layer maps to the standard error envelope
    (API Spec §0.3). `code` matches one of the documented `error.code` values."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthService:
    """Business logic for signup/login/invite/accept-invite/refresh (API Spec §1).

    Callers are responsible for handing this service the *correct kind* of session:
    `signup`, `login`, and `accept_invite` require a session opened via
    `get_auth_service_db_session` (Database Spec §0.1 addendum) since none of them have an
    organization context yet. `invite` requires a normal org-scoped session, since the
    inviter is already authenticated into a specific organization.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._organizations = OrganizationRepository(session)

    async def signup(self, data: SignupRequest) -> tuple[Organization, User, str, str]:
        existing = await self._users.get_by_email(data.email)
        if existing is not None:
            raise AuthError("conflict", "An account with this email already exists.", 409)

        organization = Organization(name=data.organization_name)
        self._organizations.add(organization)
        await self._session.flush()  # populate organization.id before the user row references it

        user = User(
            organization_id=organization.id,
            email=data.email,
            password_hash=hash_password(data.password),
            name=data.name,
            role="owner",
            status="active",
        )
        self._users.add(user)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            # Defense-in-depth against a genuine race, not just the sequential-duplicate
            # case the `existing is None` check above already handles: two concurrent
            # signups with the same email can both pass that check before either commits
            # (classic check-then-act TOCTOU). `users.email`'s global UNIQUE constraint
            # (Database Spec §1.2) is the actual source of truth; this converts the
            # resulting low-level constraint violation into the same clean 409 the
            # sequential path returns, rather than letting it surface as a raw 500. The
            # only unique constraint reachable from this insert is on `email`, so no
            # further inspection of `exc.orig` is needed to know what raised it.
            raise AuthError("conflict", "An account with this email already exists.", 409) from exc

        token = create_access_token(user_id=str(user.id), organization_id=str(organization.id))
        refresh_token = create_refresh_token(user_id=str(user.id), organization_id=str(organization.id))
        return organization, user, token, refresh_token

    async def login(self, data: LoginRequest) -> tuple[Organization, User, str, str]:
        user = await self._users.get_by_email(data.email)
        if user is None or user.password_hash is None:
            raise AuthError("unauthenticated", "Incorrect email or password.", 401)
        if not verify_password(data.password, user.password_hash):
            raise AuthError("unauthenticated", "Incorrect email or password.", 401)
        if user.status == "suspended":
            raise AuthError("permission_denied", "This account has been suspended.", 403)

        organization = await self._organizations.get_by_id(user.organization_id)
        assert organization is not None  # FK guarantees this; asserted for type-narrowing only

        user.last_login_at = datetime.now(timezone.utc)

        token = create_access_token(user_id=str(user.id), organization_id=str(user.organization_id))
        refresh_token = create_refresh_token(
            user_id=str(user.id), organization_id=str(user.organization_id)
        )
        return organization, user, token, refresh_token

    async def invite(self, *, organization_id, data: InviteRequest) -> tuple[User, str]:
        existing = await self._users.get_by_email(data.email)
        if existing is not None:
            raise AuthError(
                "conflict", "This email is already registered to an account.", 409
            )

        raw_token, token_hash, expires_at = generate_invitation_token()
        user = User(
            organization_id=organization_id,
            email=data.email,
            name=data.email,  # placeholder until the invitee sets their real name on accept
            role=data.role,
            status="invited",
            invitation_token_hash=token_hash,
            invitation_expires_at=expires_at,
        )
        self._users.add(user)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            # Same race as `signup` above, on the same constraint — see that comment.
            raise AuthError(
                "conflict", "This email is already registered to an account.", 409
            ) from exc

        # `raw_token` is handed back to the caller so it can go out in the invite
        # notification — it is never persisted (only its hash is) or returned in any
        # other API response (API Spec §1's `POST /auth/invite` note).
        return user, raw_token

    async def accept_invite(
        self, *, raw_token: str, data: AcceptInviteRequest
    ) -> tuple[Organization, User, str, str]:
        token_hash = hash_invitation_token(raw_token)
        user = await self._users.get_by_invitation_token_hash(token_hash)
        if user is None:
            raise AuthError("not_found", "This invitation link is invalid.", 404)
        if user.invitation_expires_at is not None and user.invitation_expires_at < datetime.now(
            timezone.utc
        ):
            raise AuthError("gone", "This invitation has expired.", 410)

        user.name = data.name
        user.password_hash = hash_password(data.password)
        user.status = "active"
        user.invitation_token_hash = None
        user.invitation_expires_at = None

        organization = await self._organizations.get_by_id(user.organization_id)
        assert organization is not None

        token = create_access_token(user_id=str(user.id), organization_id=str(user.organization_id))
        refresh_token = create_refresh_token(
            user_id=str(user.id), organization_id=str(user.organization_id)
        )
        return organization, user, token, refresh_token

    async def refresh(self, refresh_token: str) -> str:
        try:
            payload = decode_token(refresh_token)
        except ValueError as exc:
            raise AuthError("unauthenticated", "Invalid or expired refresh token.", 401) from exc
        if payload.get("type") != "refresh":
            raise AuthError("unauthenticated", "Invalid or expired refresh token.", 401)
        return create_access_token(user_id=payload["sub"], organization_id=payload["organization_id"])
