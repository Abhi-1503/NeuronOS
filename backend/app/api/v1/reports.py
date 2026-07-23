import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_scoped_db
from app.api.v1.envelope import envelope
from app.models.user import User
from app.services.reports_service import ReportsError, ReportsService

router = APIRouter(prefix="/reports", tags=["reports"])


def _raise_from(exc: ReportsError):
    raise HTTPException(
        status_code=exc.status_code, detail={"error": {"code": exc.code, "message": exc.message}}
    ) from exc


@router.get("/overview")
async def overview(
    period: str = Query(default="this_month", pattern="^(this_month|last_month|custom)$"),
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = None,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = ReportsService(session)
    try:
        result = await service.overview(period=period, from_=from_, to=to)
    except ReportsError as exc:
        _raise_from(exc)
    return envelope(result)


@router.get("/revenue-trend")
async def revenue_trend(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = ReportsService(session)
    return envelope(await service.revenue_trend())


@router.get("/revenue-by-source")
async def revenue_by_source(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = ReportsService(session)
    return envelope(await service.revenue_by_source())


@router.get("/top-customers")
async def top_customers(
    limit: int = Query(default=10, le=50),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = ReportsService(session)
    return envelope(await service.top_customers(limit=limit))


@router.get("/score-history")
async def score_history(
    entity_type: str = Query(pattern="^(organization|customer)$"),
    entity_id: uuid.UUID | None = None,
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    """API Spec §9 — 'fixes a real gap found during verification': `score_history` had
    no retrieval endpoint at all until now."""
    resolved_entity_id = entity_id or (
        user.organization_id if entity_type == "organization" else None
    )
    if resolved_entity_id is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "validation_error",
                    "message": "entity_id is required unless entity_type=organization.",
                }
            },
        )
    service = ReportsService(session)
    return envelope(
        await service.score_history(
            entity_type=entity_type, entity_id=resolved_entity_id, from_=from_, to=to
        )
    )
