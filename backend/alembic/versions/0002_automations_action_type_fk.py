"""Fix automations.action_type to reference action_type_registry (Phase 1 gap)

Gap addressed (surfaced during Phase 1 Automations implementation): `automations.action_type`
had its own, separate CHECK constraint (`send_email`, `create_task`, `notify_user`,
`send_invoice_reminder`) that never matched `action_type_registry`'s actual registered
values (`send_followup_email`, `create_task`, `prepare_meeting_brief`, `send_contract_email`,
`generate_invoice`, `send_invoice_reminder`) — a mismatch the original Database Spec had
already flagged as an open item ("automations use a different, broader action_type enum...
not itself constrained by FK into action_type_registry") but never actually resolved. It
surfaced concretely once Automations needed to create real `ai_actions` rows (graduating
mode) using its own `action_type` value — those two columns must speak the same vocabulary.
Resolved the same way `ai_actions.action_type` already was: a real foreign key into
`action_type_registry`, not a second, independently-maintained CHECK constraint.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-21

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Auto-generated Postgres name (0001 used raw inline `CHECK (...)` SQL, not
    # SQLAlchemy's naming convention, so this follows Postgres's own default
    # `{table}_{column}_check` pattern — confirmed against a live database rather
    # than assumed, since guessing wrong here fails loudly but unhelpfully).
    op.execute("ALTER TABLE automations DROP CONSTRAINT automations_action_type_check;")
    op.execute(
        "ALTER TABLE automations "
        "ADD CONSTRAINT fk_automations_action_type_action_type_registry "
        "FOREIGN KEY (action_type) REFERENCES action_type_registry(action_type);"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE automations DROP CONSTRAINT fk_automations_action_type_action_type_registry;"
    )
    op.execute(
        "ALTER TABLE automations ADD CONSTRAINT automations_action_type_check "
        "CHECK (action_type IN ('send_email','create_task','notify_user','send_invoice_reminder'));"
    )
