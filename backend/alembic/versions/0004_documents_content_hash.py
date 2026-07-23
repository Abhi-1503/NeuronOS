"""Add documents.content_hash for duplicate-upload detection (API Spec §0.5)

Gap addressed (surfaced during Phase 1 Knowledge implementation): API Spec §0.5
recommends detecting a duplicate upload via content hash (an Idempotency-Key alone only
catches a *retried* request, not a user manually re-uploading the same file as a second,
separate logical action) — but no column existed to actually check against. Added here,
with an index scoped by organization since the duplicate check is always org-local.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-21

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE documents ADD COLUMN content_hash TEXT;")
    op.execute(
        "CREATE INDEX ix_documents_organization_id_content_hash "
        "ON documents (organization_id, content_hash) WHERE deleted_at IS NULL;"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_documents_organization_id_content_hash;")
    op.execute("ALTER TABLE documents DROP COLUMN content_hash;")
