"""Make document_chunks.embedding nullable (Phase 1 Knowledge gap)

Gap addressed (surfaced during Phase 1 Knowledge implementation): `document_chunks.embedding`
was `NOT NULL`, but Roadmap Phase 1's actual Knowledge scope is "keyword search," not
semantic/RAG search — embeddings are a real, working feature here (via OpenAI's embeddings
API) but only when `OPENAI_API_KEY` is configured, which is genuinely optional at this
stage. A chunk is fundamentally "a piece of a document's text"; requiring an embedding
vector to exist before a chunk could even be stored made keyword search impossible to
support without an API key, which contradicts Phase 1's own stated scope. Chunks without
an embedding still support keyword search over `content`; embeddings, when present, are
what upgrades that same chunk to also support semantic search later.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-21

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding DROP NOT NULL;")


def downgrade() -> None:
    # Reversible only if no NULL embeddings actually exist yet — matches this
    # migration's own concern (a real environment might have chunks with no embedding
    # by the time anyone downgrades, so this is not silently forced through).
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding SET NOT NULL;")
