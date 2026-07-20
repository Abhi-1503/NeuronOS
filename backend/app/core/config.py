from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment variables (.env in local dev).

    The `*_database_url` defaults below are placeholder credentials for a disposable local
    Postgres container only — every real environment (staging, production, CI against a
    shared DB) sets `DATABASE_URL`/`MIGRATIONS_DATABASE_URL` via its own secrets mechanism
    (Railway env vars, GitHub Actions secrets), never relying on these fallbacks."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    # This is the APPLICATION's runtime connection — it must authenticate as the restricted
    # `neuronos_app` role (Database Spec §0.1 addendum on RLS enforcement), never as the
    # table-owning/migration role. Postgres does not apply RLS policies to a table's owner
    # (or to a superuser) unless that specific behavior is opted into per-table, so if this
    # ever points at the owner role, every RLS policy in the schema silently becomes a no-op
    # — this was caught by the RLS cross-tenant test during Phase 0 implementation, not by
    # code review, precisely because it doesn't fail loudly; it just quietly stops isolating.
    database_url: str = "postgresql+asyncpg://neuronos_app:neuronos_app_dev_only@localhost:5432/neuronos"
    # The migration/admin connection — DDL rights, owns every table, must NOT be used for
    # any application request path. Alembic (alembic/env.py) reads this directly, bypassing
    # the app's `database_url` entirely, so the two can never be accidentally swapped by a
    # config default.
    migrations_database_url: str = "postgresql+asyncpg://neuronos:neuronos@localhost:5432/neuronos"
    # Decision record: NeuronOS relies on `set_config('app.current_org_id', ..., true)` per
    # request to enforce Postgres RLS (Database Spec §0.1). That pattern requires each request
    # to hold a dedicated connection for its lifetime — a transaction-mode pooler (e.g.
    # PgBouncer's default, or a managed provider's default proxy) can hand the same physical
    # connection to a *different* tenant's request between transactions, which would silently
    # defeat RLS under concurrent load. `db_pool_mode` documents that this deployment must run
    # session-mode pooling, not transaction-mode — see Database Spec §0.1's decision record
    # before ever changing this.
    db_pool_mode: str = "session"
    db_pool_size: int = 10
    db_pool_max_overflow: int = 5

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 12
    jwt_refresh_token_expire_days: int = 30

    invitation_token_expire_days: int = 7

    redis_url: str = "redis://localhost:6379/0"

    sentry_dsn: str | None = None

    cors_allowed_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
