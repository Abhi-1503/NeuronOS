import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

# bcrypt's own limit is 72 bytes of input — anything an attacker could type well
# exceeds that anyway, so a longer password is truncated rather than rejected or
# silently mishandled (bcrypt raises ValueError past 72 bytes as of bcrypt>=4.1).
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    truncated = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    truncated = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.checkpw(truncated, password_hash.encode("ascii"))


def create_access_token(*, user_id: str, organization_id: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": user_id,
        "organization_id": organization_id,
        "exp": expires_at,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(*, user_id: str, organization_id: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    payload: dict[str, Any] = {
        "sub": user_id,
        "organization_id": organization_id,
        "exp": expires_at,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("invalid or expired token") from exc


def generate_invitation_token() -> tuple[str, str, datetime]:
    """Returns (raw_token, token_hash, expires_at). Only the hash is ever persisted —
    the raw token is emailed to the invitee and is not recoverable from the database
    (Database Spec §1.2)."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_invitation_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.invitation_token_expire_days
    )
    return raw_token, token_hash, expires_at


def hash_invitation_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


DELETION_CONFIRMATION_MINUTES = 10


def create_deletion_confirmation_token(*, organization_id: str, requested_by_user_id: str) -> tuple[str, datetime]:
    """API Spec §11's `DELETE /organization` two-step confirmation (Danger Zone) — a
    short-lived, purpose-scoped JWT rather than a new database table, since this needs
    no persistence beyond its own short validity window. Binds to *both* the
    organization and the specific user who requested it, so a stolen/leaked token from
    a different session can't be replayed to confirm a different org's deletion."""
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=DELETION_CONFIRMATION_MINUTES)
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "requested_by_user_id": requested_by_user_id,
        "exp": expires_at,
        "type": "delete_organization_confirmation",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def verify_deletion_confirmation_token(
    token: str, *, organization_id: str, user_id: str
) -> bool:
    try:
        payload = decode_token(token)
    except ValueError:
        return False
    return (
        payload.get("type") == "delete_organization_confirmation"
        and payload.get("organization_id") == organization_id
        and payload.get("requested_by_user_id") == user_id
    )
