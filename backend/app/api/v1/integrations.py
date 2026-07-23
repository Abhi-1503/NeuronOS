from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_scoped_db
from app.api.v1.envelope import envelope
from app.models.user import User
from app.schemas.settings import IntegrationOut
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("")
async def list_integrations(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    """API Spec §10. Roadmap Phase 1: 'integration stubs (UI only, "Coming soon" for
    most)' — every row here is real (every provider NeuronOS actually plans to
    support), just uniformly `not_connected` until Phase 2 OAuth flows exist. This is
    the honest current state, not placeholder data standing in for something else."""
    service = SettingsService(session)
    integrations = await service.list_integrations()
    return envelope([IntegrationOut(**i) for i in integrations])
