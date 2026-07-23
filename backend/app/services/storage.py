import uuid
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings


class StorageBackend(Protocol):
    """Blueprint §8's stated production choice is Cloudflare R2 — this interface is
    what a future `R2Storage` implementation would satisfy without any caller (the
    Documents service) needing to change. `LocalFileStorage` below is the real, working
    Phase 1 implementation, not a stand-in that pretends to work."""

    async def save(self, *, organization_id: uuid.UUID, filename: str, content: bytes) -> str:
        """Returns a storage key that `read`/`delete` can use to find this file again."""
        ...

    async def read(self, storage_key: str) -> bytes: ...

    async def delete(self, storage_key: str) -> None: ...


class LocalFileStorage:
    """Writes to a local directory (`LOCAL_STORAGE_DIR`), namespaced by organization so
    a filesystem-level mistake can't serve one org's file under another's request —
    defense-in-depth alongside the RLS-enforced `documents` row that actually gates
    access (Database Spec §0.1)."""

    def __init__(self, base_dir: str | None = None) -> None:
        self._base_dir = Path(base_dir or get_settings().local_storage_dir)

    async def save(self, *, organization_id: uuid.UUID, filename: str, content: bytes) -> str:
        org_dir = self._base_dir / str(organization_id)
        org_dir.mkdir(parents=True, exist_ok=True)
        # A UUID prefix, not the raw filename alone — two uploads named "contract.pdf"
        # must not collide on disk.
        storage_key = f"{organization_id}/{uuid.uuid4()}-{filename}"
        path = self._base_dir / storage_key
        path.write_bytes(content)
        return storage_key

    async def read(self, storage_key: str) -> bytes:
        path = self._base_dir / storage_key
        return path.read_bytes()

    async def delete(self, storage_key: str) -> None:
        path = self._base_dir / storage_key
        path.unlink(missing_ok=True)
