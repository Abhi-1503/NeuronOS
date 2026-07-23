"""Add conversations/chat_messages for the AI Workspace (API Spec §6)

Gap addressed: API Spec §6 documents `POST /chat/messages`, `GET /chat/conversations`,
and `GET /chat/conversations/{id}`, but no table for either entity exists anywhere in
the Database Spec or migration history — the AI Workspace has zero backing schema.
Added here, following the same tenant-isolation pattern as every other tenant-scoped
table (Database Spec §0.1): `conversations` carries `organization_id` directly and gets
the standard `tenant_isolation` RLS policy; `chat_messages` is only *indirectly*
tenant-scoped (joined through `conversation_id`), so — consistent with how
`document_chunks` is treated relative to `documents` — it gets no RLS policy of its
own. "Own conversations only" (API Spec §6's permission note) is an application-layer
filter on `user_id`, the same pattern already used for `ai_actions.assigned_to_user_id`
scoping, not a second RLS policy.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-21

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE conversations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_conversations_organization_id_user_id ON conversations (organization_id, user_id);"
    )
    op.execute(
        "CREATE TRIGGER trg_set_updated_at BEFORE UPDATE ON conversations "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at();"
    )
    op.execute("ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE conversations FORCE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY tenant_isolation ON conversations "
        "USING (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid);"
    )

    op.execute(
        """
        CREATE TABLE chat_messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK (role IN ('user','assistant')),
            content TEXT NOT NULL,
            citations JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX ix_chat_messages_conversation_id ON chat_messages (conversation_id);")

    # Belt-and-suspenders alongside migration 0001's `ALTER DEFAULT PRIVILEGES` (which only
    # covers tables created by the same role going forward) — explicit here so the restricted
    # app role's access to these two new tables never depends on that default silently holding.
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON conversations, chat_messages TO neuronos_app;")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chat_messages CASCADE;")
    op.execute("DROP TABLE IF EXISTS conversations CASCADE;")
