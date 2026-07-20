"""Initial schema — full MVP + Phase 2 entity set (Database Spec v1)

Built in one pass per the Phase 0 decision recorded in NeuronOS_Database_Spec.md §9:
the full schema (including Projects/Meetings/Automations-builder tables not yet used
by any Phase 1 application code) is created now via Alembic; app/API code remains
scoped strictly to each Roadmap phase. Tables sit unused until their phase arrives.

Revision ID: 0001
Revises:
Create Date: 2026-07-20

"""
import os
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Read at *initial creation only* (see the `IF NOT EXISTS` guard below) — every real
# environment sets NEURONOS_APP_ROLE_PASSWORD from its own secrets mechanism before first
# running this migration there, so the restricted role never has the dev placeholder as
# its real password outside a local dev/test database. Deliberately NOT re-applied on
# every migration run: if this were unconditional, a migration run with the env var
# unset (e.g. a misconfigured CI job) would silently reset an already-rotated production
# password back to the placeholder. Rotating the password on an existing role is instead
# a deliberate, explicit action (`ALTER ROLE neuronos_app WITH PASSWORD '...'`), not a
# side effect of re-running migrations.
_APP_ROLE_PASSWORD = os.environ.get("NEURONOS_APP_ROLE_PASSWORD", "neuronos_app_dev_only")
# Escaped for safe embedding in a single-quoted SQL string literal (doubling embedded
# single quotes, the standard SQL escape) — this value cannot be passed as a bind
# parameter because DDL inside a DO $$ ... $$ block takes no external parameters.
_APP_ROLE_PASSWORD_SQL_LITERAL = _APP_ROLE_PASSWORD.replace("'", "''")


# Standard RLS policy (Database Spec §0.1) — applied to every table that carries
# organization_id directly. Tables that are only *indirectly* tenant-scoped (joined
# through a parent FK, e.g. project_members, meeting_attendees, document_chunks) are
# left without their own policy, consistent with how the spec defines "tenant-scoped
# table" as one that carries the organization_id column itself.
RLS_TABLES = [
    "users",
    "customers",
    "timeline_events",
    "deals",
    "projects",
    "tasks",
    "risk_flags",
    "meetings",
    "documents",
    "linked_entities",
    "automations",
    "ai_actions",
    "score_history",
    "integration_connections",
]

# updated_at trigger (Database Spec §0.3) — only tables that actually carry an
# updated_at column.
UPDATED_AT_TABLES = [
    "organizations",
    "users",
    "customers",
    "deals",
    "projects",
    "tasks",
    "meetings",
    "documents",
    "automations",
    "integration_connections",
    "ai_actions",
]

UPGRADE_STATEMENTS = [
    # --- Extensions -----------------------------------------------------------------
    'CREATE EXTENSION IF NOT EXISTS pgcrypto;',  # gen_random_uuid()
    'CREATE EXTENSION IF NOT EXISTS citext;',
    'CREATE EXTENSION IF NOT EXISTS vector;',
    # --- updated_at trigger function (Database Spec §0.3) ----------------------------
    """
    CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
    BEGIN
      NEW.updated_at = now();
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """,
    # --- 1.1 organizations -------------------------------------------------------------
    """
    CREATE TABLE organizations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT NOT NULL,
        industry TEXT,
        company_size TEXT CHECK (company_size IN ('1-10','11-50','51-250','251+')),
        timezone TEXT NOT NULL DEFAULT 'UTC',
        plan TEXT NOT NULL DEFAULT 'trial' CHECK (plan IN ('trial','starter','growth','enterprise')),
        business_health_score SMALLINT,
        score_algorithm_version TEXT NOT NULL DEFAULT 'v1_rule_based',
        onboarding_method TEXT CHECK (onboarding_method IN ('integration','documents','manual_customers')),
        onboarding_completed_at TIMESTAMPTZ,
        onboarding_first_insight_at TIMESTAMPTZ,
        terms_accepted_version TEXT,
        terms_accepted_at TIMESTAMPTZ,
        dpa_signed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        deleted_at TIMESTAMPTZ
    );
    """,
    # --- 1.2 users (Decision: email globally unique — see spec §1.2) ------------------
    """
    CREATE TABLE users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        email CITEXT NOT NULL UNIQUE,
        password_hash TEXT,
        name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('owner','admin','member')),
        avatar_url TEXT,
        last_login_at TIMESTAMPTZ,
        invited_by UUID REFERENCES users(id),
        invitation_token_hash TEXT,
        invitation_expires_at TIMESTAMPTZ,
        status TEXT NOT NULL DEFAULT 'invited' CHECK (status IN ('invited','active','suspended')),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        deleted_at TIMESTAMPTZ,
        created_by UUID REFERENCES users(id)
    );
    """,
    "CREATE INDEX ix_users_organization_id_role ON users (organization_id, role);",
    # --- 8.1 integration_connections (created before customers, which references it) --
    """
    CREATE TABLE integration_connections (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        provider TEXT NOT NULL CHECK (provider IN (
            'gmail','google_drive','google_calendar','outlook','microsoft_365',
            'slack','whatsapp','hubspot','salesforce','zoho_crm','zoho_books','quickbooks'
        )),
        connected_by_user_id UUID REFERENCES users(id),
        scopes TEXT[],
        access_token_encrypted TEXT NOT NULL,
        refresh_token_encrypted TEXT,
        status TEXT NOT NULL DEFAULT 'connected' CHECK (status IN ('connected','sync_error','disconnected')),
        last_synced_at TIMESTAMPTZ,
        last_sync_error TEXT,
        provider_review_status TEXT NOT NULL DEFAULT 'not_submitted'
            CHECK (provider_review_status IN ('not_submitted','in_review','approved','rejected')),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        deleted_at TIMESTAMPTZ
    );
    """,
    """
    CREATE UNIQUE INDEX uq_integration_connections_org_provider_active
        ON integration_connections (organization_id, provider) WHERE deleted_at IS NULL;
    """,
    # --- 2.1 customers ------------------------------------------------------------------
    """
    CREATE TABLE customers (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','at_risk','inactive','churned')),
        relationship_score SMALLINT,
        score_algorithm_version TEXT NOT NULL DEFAULT 'v1_rule_based',
        revenue_total NUMERIC(14,2) NOT NULL DEFAULT 0,
        currency CHAR(3) NOT NULL DEFAULT 'INR',
        last_contact_at TIMESTAMPTZ,
        source TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual','integration')),
        source_integration_id UUID REFERENCES integration_connections(id),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        deleted_at TIMESTAMPTZ,
        created_by UUID REFERENCES users(id)
    );
    """,
    "CREATE INDEX ix_customers_organization_id_status ON customers (organization_id, status);",
    "CREATE INDEX ix_customers_organization_id_relationship_score ON customers (organization_id, relationship_score);",
    # --- 2.2 timeline_events (append-only) ----------------------------------------------
    """
    CREATE TABLE timeline_events (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
        event_type TEXT NOT NULL CHECK (event_type IN ('meeting','email','proposal','invoice','note','contract')),
        title TEXT NOT NULL,
        body TEXT,
        occurred_at TIMESTAMPTZ NOT NULL,
        linked_entity_type TEXT,
        linked_entity_id UUID,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        created_by UUID REFERENCES users(id)
    );
    """,
    "CREATE INDEX ix_timeline_events_org_customer_occurred ON timeline_events (organization_id, customer_id, occurred_at DESC);",
    # --- 2.3 deals ------------------------------------------------------------------------
    """
    CREATE TABLE deals (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        stage TEXT NOT NULL DEFAULT 'proposal' CHECK (stage IN ('proposal','negotiation','won','lost')),
        amount NUMERIC(14,2) NOT NULL,
        currency CHAR(3) NOT NULL DEFAULT 'INR',
        expected_close_date DATE,
        closed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        deleted_at TIMESTAMPTZ,
        created_by UUID REFERENCES users(id)
    );
    """,
    "CREATE INDEX ix_deals_organization_id_stage ON deals (organization_id, stage);",
    # --- 4.1 meetings (created before projects/tasks, which reference it) --------------
    """
    CREATE TABLE meetings (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
        title TEXT NOT NULL,
        platform TEXT,
        scheduled_at TIMESTAMPTZ NOT NULL,
        duration_minutes SMALLINT,
        status TEXT NOT NULL DEFAULT 'upcoming' CHECK (status IN ('upcoming','brief_ready','completed','needs_notes')),
        source_calendar_event_id TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        deleted_at TIMESTAMPTZ,
        created_by UUID REFERENCES users(id)
    );
    """,
    "CREATE INDEX ix_meetings_organization_id_scheduled_at ON meetings (organization_id, scheduled_at);",
    # --- 3.1 projects ---------------------------------------------------------------------
    """
    CREATE TABLE projects (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
        name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'on_track'
            CHECK (status IN ('on_track','at_risk','needs_review','in_review','completed')),
        progress_pct SMALLINT NOT NULL DEFAULT 0 CHECK (progress_pct BETWEEN 0 AND 100),
        deadline DATE,
        completed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        deleted_at TIMESTAMPTZ,
        created_by UUID REFERENCES users(id)
    );
    """,
    "CREATE INDEX ix_projects_organization_id_status ON projects (organization_id, status);",
    "CREATE INDEX ix_projects_organization_id_deadline ON projects (organization_id, deadline);",
    # --- 3.2 project_members ----------------------------------------------------------------
    """
    CREATE TABLE project_members (
        project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        role_on_project TEXT DEFAULT 'contributor' CHECK (role_on_project IN ('lead','contributor','reviewer')),
        added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (project_id, user_id)
    );
    """,
    # --- 3.3 tasks (references meetings) --------------------------------------------------
    """
    CREATE TABLE tasks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        assignee_id UUID REFERENCES users(id) ON DELETE SET NULL,
        status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo','in_progress','blocked','done')),
        due_date DATE,
        source TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual','meeting_action_item','automation')),
        source_meeting_id UUID REFERENCES meetings(id) ON DELETE SET NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        deleted_at TIMESTAMPTZ,
        created_by UUID REFERENCES users(id)
    );
    """,
    "CREATE INDEX ix_tasks_organization_id_project_id_status ON tasks (organization_id, project_id, status);",
    # --- 3.4 risk_flags -----------------------------------------------------------------------
    """
    CREATE TABLE risk_flags (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        flag_type TEXT NOT NULL CHECK (flag_type IN ('deadline_risk','dependency_blocked','resourcing','budget')),
        severity TEXT NOT NULL CHECK (severity IN ('low','medium','high')),
        description TEXT NOT NULL,
        reasoning TEXT,
        confidence_score REAL,
        resolved_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        created_by UUID REFERENCES users(id)
    );
    """,
    "CREATE INDEX ix_risk_flags_org_project_unresolved ON risk_flags (organization_id, project_id) WHERE resolved_at IS NULL;",
    # --- 4.2 meeting_attendees -----------------------------------------------------------------
    """
    CREATE TABLE meeting_attendees (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
        attendee_type TEXT NOT NULL CHECK (attendee_type IN ('user','customer_contact')),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        customer_contact_name TEXT,
        customer_contact_email CITEXT
    );
    """,
    # --- 4.3 meeting_summaries -----------------------------------------------------------------
    """
    CREATE TABLE meeting_summaries (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        meeting_id UUID NOT NULL UNIQUE REFERENCES meetings(id) ON DELETE CASCADE,
        summary_text TEXT NOT NULL,
        talking_points JSONB,
        generated_by_model TEXT,
        generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        edited_by_user_id UUID REFERENCES users(id)
    );
    """,
    # --- 4.4 meeting_action_items (references tasks) -------------------------------------------
    """
    CREATE TABLE meeting_action_items (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
        description TEXT NOT NULL,
        task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """,
    # --- 5.1 documents -----------------------------------------------------------------------
    """
    CREATE TABLE documents (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        file_type TEXT NOT NULL CHECK (file_type IN ('pdf','docx','pptx','xlsx','email','other')),
        storage_key TEXT NOT NULL,
        size_bytes BIGINT,
        ai_summary TEXT,
        visibility TEXT NOT NULL DEFAULT 'org' CHECK (visibility IN ('org','admin_only','custom')),
        source TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual','integration')),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        deleted_at TIMESTAMPTZ,
        created_by UUID REFERENCES users(id)
    );
    """,
    "CREATE INDEX ix_documents_organization_id_file_type ON documents (organization_id, file_type);",
    # --- 5.2 document_chunks (pgvector, dimension locked at 1536 — confirm before Phase 1) ---
    """
    CREATE TABLE document_chunks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        embedding VECTOR(1536) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """,
    # HNSW index deliberately deferred (Database Spec §5.2 / §12.4) until chunk volume
    # justifies it — sequential scan is acceptable at MVP scale.
    # --- 5.3 document_tags ------------------------------------------------------------------
    """
    CREATE TABLE document_tags (
        document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        tag TEXT NOT NULL,
        PRIMARY KEY (document_id, tag)
    );
    """,
    # --- 5.4 linked_entities (no FK on source/target — polymorphic, §7.3) -------------------
    """
    CREATE TABLE linked_entities (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        source_type TEXT NOT NULL,
        source_id UUID NOT NULL,
        target_type TEXT NOT NULL,
        target_id UUID NOT NULL,
        relationship TEXT,
        confidence REAL,
        status TEXT NOT NULL DEFAULT 'ai_suggested' CHECK (status IN ('ai_suggested','confirmed','rejected','manual')),
        corrected_by_user_id UUID REFERENCES users(id),
        corrected_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """,
    "CREATE INDEX ix_linked_entities_org_source ON linked_entities (organization_id, source_type, source_id);",
    "CREATE INDEX ix_linked_entities_org_target ON linked_entities (organization_id, target_type, target_id);",
    """
    CREATE INDEX ix_linked_entities_review_queue ON linked_entities (organization_id, status)
        WHERE status = 'ai_suggested' AND confidence < 0.7;
    """,
    # --- 7.1 action_type_registry (before ai_actions, which FKs into it) --------------------
    """
    CREATE TABLE action_type_registry (
        action_type TEXT PRIMARY KEY,
        severity_tier TEXT NOT NULL CHECK (severity_tier IN ('low','medium','high')),
        is_reversible BOOLEAN NOT NULL
    );
    """,
    # --- 6.1 automations ---------------------------------------------------------------------
    """
    CREATE TABLE automations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        mode TEXT NOT NULL DEFAULT 'dry_run' CHECK (mode IN ('dry_run','graduating','live','paused')),
        is_active BOOLEAN NOT NULL DEFAULT true,
        trigger_type TEXT NOT NULL CHECK (trigger_type IN (
            'invoice_overdue','no_reply_days','project_completed','contract_expiring','new_customer'
        )),
        trigger_config JSONB NOT NULL,
        action_type TEXT NOT NULL CHECK (action_type IN ('send_email','create_task','notify_user','send_invoice_reminder')),
        action_config JSONB NOT NULL,
        graduation_threshold INTEGER NOT NULL DEFAULT 5,
        approved_run_count INTEGER NOT NULL DEFAULT 0,
        times_triggered INTEGER NOT NULL DEFAULT 0,
        success_rate_pct SMALLINT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        deleted_at TIMESTAMPTZ,
        created_by UUID REFERENCES users(id)
    );
    """,
    # --- 7.1 ai_actions (FKs into action_type_registry) --------------------------------------
    """
    CREATE TABLE ai_actions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        description TEXT,
        action_type TEXT NOT NULL REFERENCES action_type_registry(action_type),
        severity_tier TEXT NOT NULL DEFAULT 'low' CHECK (severity_tier IN ('low','medium','high')),
        is_reversible BOOLEAN NOT NULL DEFAULT true,
        reasoning TEXT,
        confidence_score REAL,
        priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low','medium','high')),
        status TEXT NOT NULL DEFAULT 'suggested'
            CHECK (status IN ('suggested','approved','rejected','delegated','executed','failed')),
        suggested_amount NUMERIC(14,2),
        related_entity_type TEXT,
        related_entity_id UUID,
        assigned_to_user_id UUID REFERENCES users(id),
        delegated_to_user_id UUID REFERENCES users(id),
        decided_by_user_id UUID REFERENCES users(id),
        decided_at TIMESTAMPTZ,
        executed_at TIMESTAMPTZ,
        generated_by_engine TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """,
    "CREATE INDEX ix_ai_actions_organization_id_status ON ai_actions (organization_id, status);",
    "CREATE INDEX ix_ai_actions_org_assignee_status ON ai_actions (organization_id, assigned_to_user_id, status);",
    # --- 6.2 automation_runs (references automations, ai_actions) -----------------------------
    """
    CREATE TABLE automation_runs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        automation_id UUID NOT NULL REFERENCES automations(id) ON DELETE CASCADE,
        idempotency_key TEXT NOT NULL,
        triggered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        status TEXT NOT NULL CHECK (status IN ('simulated','success','failed','pending_approval')),
        related_ai_action_id UUID REFERENCES ai_actions(id) ON DELETE SET NULL,
        error_message TEXT,
        target_entity_type TEXT,
        target_entity_id UUID,
        CONSTRAINT uq_automation_runs_automation_idempotency UNIQUE (automation_id, idempotency_key)
    );
    """,
    # --- 7.2 ai_action_executions --------------------------------------------------------------
    """
    CREATE TABLE ai_action_executions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        ai_action_id UUID NOT NULL REFERENCES ai_actions(id) ON DELETE CASCADE,
        idempotency_key TEXT NOT NULL UNIQUE,
        executed_action TEXT NOT NULL,
        payload JSONB,
        result TEXT NOT NULL CHECK (result IN ('success','failed')),
        error_message TEXT,
        executed_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """,
    # --- 7.5 score_history ------------------------------------------------------------------
    """
    CREATE TABLE score_history (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        entity_type TEXT NOT NULL CHECK (entity_type IN ('organization','customer')),
        entity_id UUID NOT NULL,
        score SMALLINT NOT NULL,
        algorithm_version TEXT NOT NULL,
        computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """,
    # --- action_type_registry seed data (Database Spec §7.1 severity mapping table) ---------
    """
    INSERT INTO action_type_registry (action_type, severity_tier, is_reversible) VALUES
        ('send_followup_email', 'low', false),
        ('create_task', 'low', true),
        ('prepare_meeting_brief', 'low', true),
        ('send_contract_email', 'high', false),
        ('generate_invoice', 'high', false),
        ('send_invoice_reminder', 'medium', false);
    """,
]

DOWNGRADE_STATEMENTS = [
    "DROP OWNED BY neuronos_app;",
    "DROP ROLE IF EXISTS neuronos_app;",
    "DROP TABLE IF EXISTS score_history CASCADE;",
    "DROP TABLE IF EXISTS ai_action_executions CASCADE;",
    "DROP TABLE IF EXISTS automation_runs CASCADE;",
    "DROP TABLE IF EXISTS ai_actions CASCADE;",
    "DROP TABLE IF EXISTS automations CASCADE;",
    "DROP TABLE IF EXISTS action_type_registry CASCADE;",
    "DROP TABLE IF EXISTS linked_entities CASCADE;",
    "DROP TABLE IF EXISTS document_tags CASCADE;",
    "DROP TABLE IF EXISTS document_chunks CASCADE;",
    "DROP TABLE IF EXISTS documents CASCADE;",
    "DROP TABLE IF EXISTS meeting_action_items CASCADE;",
    "DROP TABLE IF EXISTS meeting_summaries CASCADE;",
    "DROP TABLE IF EXISTS meeting_attendees CASCADE;",
    "DROP TABLE IF EXISTS risk_flags CASCADE;",
    "DROP TABLE IF EXISTS tasks CASCADE;",
    "DROP TABLE IF EXISTS project_members CASCADE;",
    "DROP TABLE IF EXISTS projects CASCADE;",
    "DROP TABLE IF EXISTS meetings CASCADE;",
    "DROP TABLE IF EXISTS deals CASCADE;",
    "DROP TABLE IF EXISTS timeline_events CASCADE;",
    "DROP TABLE IF EXISTS customers CASCADE;",
    "DROP TABLE IF EXISTS integration_connections CASCADE;",
    "DROP TABLE IF EXISTS users CASCADE;",
    "DROP TABLE IF EXISTS organizations CASCADE;",
    "DROP FUNCTION IF EXISTS set_updated_at();",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)

    for table in UPDATED_AT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_set_updated_at BEFORE UPDATE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION set_updated_at();"
        )

    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        # FORCE, not just ENABLE: Postgres does not apply RLS policies to a table's *owner*
        # (or to a superuser) by default, regardless of ENABLE ROW LEVEL SECURITY — this was
        # discovered via the RLS cross-tenant test failing silently during Phase 0
        # implementation (§0.1 addendum), not by inspection. FORCE closes that gap for the
        # owner; the real fix is still that the app connects as the restricted `neuronos_app`
        # role below, never as the owner — FORCE is defense-in-depth on top of that, not a
        # substitute for it (superusers bypass RLS even with FORCE set).
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid);"
        )

    # Narrow, documented exception (Database Spec §0.1 addendum) — the only pre-authentication
    # operations against `users` (login lookup, signup's first insert, invite-accept lookup)
    # have no organization context to scope by yet. This is additive to tenant_isolation
    # (permissive policies OR together), not a replacement for it, and applies to no other table.
    op.execute(
        "CREATE POLICY auth_service_bypass ON users "
        "USING (current_setting('app.bypass_rls_for_auth', true) = 'true') "
        "WITH CHECK (current_setting('app.bypass_rls_for_auth', true) = 'true');"
    )

    # Restricted application role (Database Spec §0.1 addendum): the app connects as this
    # role, never as the table owner, because Postgres exempts owners/superusers from RLS.
    # Password sourced from NEURONOS_APP_ROLE_PASSWORD at creation time (see the module-level
    # comment above) — falls back to a local-dev placeholder only when that env var is unset.
    op.execute(
        f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'neuronos_app') THEN
            CREATE ROLE neuronos_app LOGIN PASSWORD '{_APP_ROLE_PASSWORD_SQL_LITERAL}' NOSUPERUSER NOBYPASSRLS;
          END IF;
        END
        $$;
        """
    )
    op.execute(
        "DO $$ BEGIN "
        "EXECUTE format('GRANT CONNECT ON DATABASE %I TO neuronos_app', current_database()); "
        "END $$;"
    )
    op.execute("GRANT USAGE ON SCHEMA public TO neuronos_app;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO neuronos_app;")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO neuronos_app;"
    )


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
