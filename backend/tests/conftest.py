import os

# Must be set before any `app.*` module is imported, since `app.core.config.get_settings()`
# is called at import time (e.g. by app/core/db.py and app/core/security.py) and cached.
# `DATABASE_URL` is the app's restricted `neuronos_app` role (Database Spec §0.1 addendum —
# RLS is a no-op against the table-owning role, so tests must exercise the same restricted
# role production uses, not the migration/owner role). `MIGRATIONS_DATABASE_URL` is the owner
# role, used only for running migrations and for test setup/teardown that needs to see and
# truncate across every organization.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://neuronos_app:neuronos_app_dev_only@localhost:5432/neuronos_test",
)
os.environ.setdefault(
    "MIGRATIONS_DATABASE_URL",
    "postgresql+asyncpg://neuronos:neuronos@localhost:5432/neuronos_test",
)
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-production")

from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from app.core.config import get_settings
from app.main import app

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _alembic_config() -> Config:
    config = Config(os.path.join(_BACKEND_DIR, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(_BACKEND_DIR, "alembic"))
    return config


@pytest.fixture(scope="session", autouse=True)
def _migrated_database():
    """Runs the real Alembic migration (as the owner role) against a disposable Postgres
    test database — not `Base.metadata.create_all`, since RLS policies, the update trigger,
    the citext/pgvector extensions, the restricted `neuronos_app` role, and the
    action_type_registry seed data only exist via the actual migration (Database Spec
    §0.1/§0.3/§7.1). Requires a reachable Postgres at `MIGRATIONS_DATABASE_URL`."""
    config = _alembic_config()
    command.upgrade(config, "head")
    yield
    command.downgrade(config, "base")


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@asynccontextmanager
async def drive_session(session_gen):
    """Drives a generator-based session dependency (`get_db_session` /
    `get_auth_service_db_session`) the same way FastAPI's dependency injection actually
    does, for tests that call `AuthService` directly instead of going through the real
    HTTP/FastAPI layer: resuming the generator past its `yield` — not closing it — is
    what lets the `async with session.begin():` inside it exit normally and commit;
    closing the generator (`aclose()`) instead sends `GeneratorExit` at the yield point,
    which is an exception as far as that `async with` block is concerned and rolls back.

    A test that uses `aclose()` after a *successful* operation it needs a later,
    separate session to see will silently roll that operation back and then get a
    confusing "not found" from the second session — this is exactly the bug this helper
    exists to make impossible to write by accident.
    """
    session = await anext(session_gen)
    try:
        yield session
    except BaseException:
        await session_gen.aclose()
        raise
    else:
        try:
            await anext(session_gen)
        except StopAsyncIteration:
            pass


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables():
    """Truncates tenant tables between tests so each test starts from an empty database
    without re-running the (slow) full migration per test. Deliberately uses the owner role
    (`MIGRATIONS_DATABASE_URL`), not the app's restricted role — the restricted role has no
    TRUNCATE privilege by design (Database Spec §0.1 addendum grants only SELECT/INSERT/
    UPDATE/DELETE), and this cleanup is test infrastructure, not applic behavior under test."""
    yield
    admin_engine = create_async_engine(get_settings().migrations_database_url)
    try:
        async with admin_engine.connect() as conn:
            async with conn.begin():
                await conn.execute(
                    text(
                        "TRUNCATE TABLE organizations, users, action_type_registry "
                        "RESTART IDENTITY CASCADE"
                    )
                )
                await conn.execute(
                    text(
                        """
                        INSERT INTO action_type_registry (action_type, severity_tier, is_reversible) VALUES
                            ('send_followup_email', 'low', false),
                            ('create_task', 'low', true),
                            ('prepare_meeting_brief', 'low', true),
                            ('send_contract_email', 'high', false),
                            ('generate_invoice', 'high', false),
                            ('send_invoice_reminder', 'medium', false);
                        """
                    )
                )
    finally:
        await admin_engine.dispose()
