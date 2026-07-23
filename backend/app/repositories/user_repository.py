import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Data access for `users`. Kept separate from `AuthService` so the service layer
    stays testable without hitting the database directly (Blueprint §10)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        # Global uniqueness (Database Spec §1.2) — this is a cross-tenant lookup by design,
        # so it must run without an organization-scoped RLS context in effect (the caller,
        # e.g. login/signup, is by definition not yet authenticated into any organization).
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_invitation_token_hash(self, token_hash: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.invitation_token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def list_for_organization(self) -> list[User]:
        """RLS-scoped (Database Spec §0.1) — no explicit organization_id filter needed
        here, unlike `get_by_email`/`get_by_invitation_token_hash` above, which are
        deliberately pre-authentication, cross-tenant lookups."""
        result = await self._session.execute(
            select(User).where(User.deleted_at.is_(None)).order_by(User.created_at)
        )
        return list(result.scalars().all())

    async def count_owners(self) -> int:
        result = await self._session.execute(
            select(User).where(User.role == "owner", User.deleted_at.is_(None))
        )
        return len(result.scalars().all())

    def add(self, user: User) -> None:
        self._session.add(user)
