from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_scoped_db, require_role
from app.api.v1.envelope import envelope
from app.models.user import User
from app.schemas.onboarding import SelectMethodRequest
from app.services.onboarding_service import OnboardingError, OnboardingService

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _raise_from(exc: OnboardingError):
    raise HTTPException(
        status_code=exc.status_code, detail={"error": {"code": exc.code, "message": exc.message}}
    ) from exc


@router.get("/status")
async def get_status(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = OnboardingService(session)
    status = await service.get_status(user.organization_id)
    return envelope(status)


@router.post("/select-method")
async def select_method(
    body: SelectMethodRequest,
    user: User = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = OnboardingService(session)
    try:
        status = await service.select_method(user.organization_id, body.method)
    except OnboardingError as exc:
        _raise_from(exc)
    return envelope(status)


@router.post("/complete")
async def complete(
    user: User = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = OnboardingService(session)
    try:
        result = await service.complete(user.organization_id)
    except OnboardingError as exc:
        _raise_from(exc)
    return envelope(result)
