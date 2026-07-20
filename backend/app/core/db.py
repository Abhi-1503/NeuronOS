from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# Session-mode pooling (Database Spec §0.1 decision record): each checked-out connection
# is held for the lifetime of one request/session, never handed to a different tenant's
# request mid-flight. `pool_size`/`max_overflow` bound how many *dedicated* connections
# this instance holds — this is deliberately a smaller, session-scoped pool, not a large
# transaction-multiplexing one. The deployment's Postgres proxy (Railway) must also be
# configured for session-mode pooling, not transaction-mode, for this guarantee to hold
# end-to-end — an app-level setting alone cannot fix a transaction-mode proxy in front of it.
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_pool_max_overflow,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db_session(organization_id: str | None = None) -> AsyncGenerator[AsyncSession, None]:
    """Yields a session with `app.current_org_id` set for the duration of the transaction
    (Database Spec §0.1), enforcing the RLS tenant-isolation policy at the database layer
    regardless of any application-layer scoping bug. `organization_id` is always derived
    server-side from the authenticated token (API Spec §0.1) — never accepted as a parameter
    from the client.

    Uses `set_config(..., true)` rather than `SET LOCAL app.current_org_id = :org_id` — Postgres's
    `SET`/`SET LOCAL` statements don't accept bind parameters at all (only literals), so a
    parameterized `SET LOCAL` fails at the protocol level with a syntax error. `set_config` is a
    regular function call and takes a normal bind parameter; its third argument (`true`) makes
    the setting transaction-local, the equivalent of `SET LOCAL`.
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            if organization_id is not None:
                await session.execute(
                    text("SELECT set_config('app.current_org_id', :org_id, true)"),
                    {"org_id": organization_id},
                )
            yield session


async def get_auth_service_db_session() -> AsyncGenerator[AsyncSession, None]:
    """For the three pre-authentication operations that have no organization context to scope
    by (login lookup, signup's first insert, invite-accept lookup — Database Spec §0.1
    addendum): sets `app.bypass_rls_for_auth` instead of `app.current_org_id`, which the
    narrow `auth_service_bypass` policy on `users` (and only `users`) checks. Do not use this
    for any request that has an authenticated organization context — use `get_db_session` with
    the real `organization_id` for everything else.
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.bypass_rls_for_auth', 'true', true)")
            )
            yield session
