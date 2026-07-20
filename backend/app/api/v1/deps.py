import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_auth_service_db_session, get_db_session
from app.core.logging import organization_id_ctx
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user_repository import UserRepository


@dataclass(frozen=True)
class AuthContext:
    user_id: uuid.UUID
    organization_id: uuid.UUID


def _unauthenticated() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"error": {"code": "unauthenticated", "message": "Missing or invalid credentials."}},
    )


async def get_auth_context(authorization: str | None = Header(default=None)) -> AuthContext:
    """Derives (user_id, organization_id) from the bearer token — organization_id is never
    accepted as a request parameter (API Spec §0.1), only ever from the token itself."""
    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthenticated()
    raw_token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(raw_token)
    except ValueError as exc:
        raise _unauthenticated() from exc
    if payload.get("type") != "access":
        raise _unauthenticated()
    try:
        return AuthContext(
            user_id=uuid.UUID(payload["sub"]),
            organization_id=uuid.UUID(payload["organization_id"]),
        )
    except (KeyError, ValueError) as exc:
        raise _unauthenticated() from exc


async def get_scoped_db(
    auth: AuthContext = Depends(get_auth_context),
) -> AsyncGenerator[AsyncSession, None]:
    """A DB session with RLS's `app.current_org_id` set from the authenticated token
    (Database Spec §0.1) — the standard dependency for any endpoint that requires auth."""
    organization_id_ctx.set(str(auth.organization_id))
    async for session in get_db_session(organization_id=str(auth.organization_id)):
        yield session
    organization_id_ctx.set(None)


async def get_public_db() -> AsyncGenerator[AsyncSession, None]:
    """For the pre-authentication auth endpoints only (signup, login, accept-invite) —
    see Database Spec §0.1 addendum and `get_auth_service_db_session`."""
    async for session in get_auth_service_db_session():
        yield session


async def get_current_user(
    auth: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_scoped_db),
) -> User:
    user = await UserRepository(session).get_by_id(auth.user_id)
    if user is None or user.status != "active":
        raise _unauthenticated()
    return user


def require_role(*allowed_roles: str):
    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": "permission_denied",
                        "message": f"Requires one of roles: {', '.join(allowed_roles)}.",
                    }
                },
            )
        return user

    return _check
