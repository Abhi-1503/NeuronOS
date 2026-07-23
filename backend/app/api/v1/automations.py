import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_scoped_db, require_role
from app.api.v1.envelope import envelope
from app.models.user import User
from app.schemas.automation import (
    AutomationCreate,
    AutomationOut,
    AutomationRunOut,
    AutomationUpdate,
    PromoteModeRequest,
)
from app.services.automation_service import AutomationError, AutomationService

router = APIRouter(prefix="/automations", tags=["automations"])


def _raise_from(exc: AutomationError):
    raise HTTPException(
        status_code=exc.status_code, detail={"error": {"code": exc.code, "message": exc.message}}
    ) from exc


@router.get("")
async def list_automations(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = AutomationService(session)
    automations = await service.list_automations()
    return envelope([AutomationOut.model_validate(a) for a in automations])


@router.post("", status_code=201)
async def create_automation(
    body: AutomationCreate,
    user: User = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = AutomationService(session)
    automation = await service.create(organization_id=user.organization_id, data=body)
    return envelope(AutomationOut.model_validate(automation))


@router.patch("/{automation_id}")
async def update_automation(
    automation_id: uuid.UUID,
    body: AutomationUpdate,
    _: User = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = AutomationService(session)
    try:
        automation = await service.update(automation_id, body)
    except AutomationError as exc:
        _raise_from(exc)
    return envelope(AutomationOut.model_validate(automation))


@router.post("/{automation_id}/promote-mode")
async def promote_mode(
    automation_id: uuid.UUID,
    body: PromoteModeRequest,
    _: User = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = AutomationService(session)
    try:
        automation = await service.promote_mode(automation_id, body)
    except AutomationError as exc:
        _raise_from(exc)
    return envelope(AutomationOut.model_validate(automation))


@router.get("/{automation_id}/dry-run-results")
async def dry_run_results(
    automation_id: uuid.UUID,
    limit: int = Query(default=25, le=100),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = AutomationService(session)
    try:
        runs = await service.get_dry_run_results(automation_id, limit=limit)
    except AutomationError as exc:
        _raise_from(exc)
    return envelope([AutomationRunOut.model_validate(r) for r in runs])


@router.get("/{automation_id}/runs")
async def get_runs(
    automation_id: uuid.UUID,
    limit: int = Query(default=25, le=100),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = AutomationService(session)
    try:
        runs = await service.get_runs(automation_id, limit=limit)
    except AutomationError as exc:
        _raise_from(exc)
    return envelope([AutomationRunOut.model_validate(r) for r in runs])


@router.post("/{automation_id}/evaluate")
async def evaluate_automation(
    automation_id: uuid.UUID,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    user: User = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = AutomationService(session)
    try:
        automation = await service.get(automation_id)
    except AutomationError as exc:
        _raise_from(exc)
    runs = await service.evaluate_single(
        automation, organization_id=user.organization_id, now=datetime.now(timezone.utc)
    )
    return envelope([AutomationRunOut.model_validate(r) for r in runs])
