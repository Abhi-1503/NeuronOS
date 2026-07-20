from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_scoped_db, require_role
from app.api.v1.envelope import envelope
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.auth import OrganizationOut

router = APIRouter(prefix="/organization", tags=["organization"])


class AcceptTermsRequest(BaseModel):
    version: str = Field(min_length=1)


@router.post("/accept-terms")
async def accept_terms(
    body: AcceptTermsRequest,
    user: User = Depends(require_role("owner")),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    """API Spec §11. Blocking step in the signup flow (Blueprint §17.8) — the org's Owner
    accepts the AI-action liability terms before the rest of the product unlocks. Owner-only:
    the Terms are accepted on behalf of the organization by its Owner, not by any member."""
    repo = OrganizationRepository(session)
    organization = await repo.get_by_id(user.organization_id)
    assert organization is not None
    organization.terms_accepted_version = body.version
    organization.terms_accepted_at = datetime.now(timezone.utc)
    return envelope(OrganizationOut.model_validate(organization))
