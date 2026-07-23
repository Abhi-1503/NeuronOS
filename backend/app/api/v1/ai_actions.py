import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_scoped_db
from app.api.v1.envelope import envelope
from app.models.user import User
from app.schemas.ai_action import AIActionOut, ApproveRequest, DelegateRequest, RejectRequest
from app.services.ai_action_service import AIActionError, AIActionService

router = APIRouter(prefix="/ai-actions", tags=["ai-actions"])


def _raise_from(exc: AIActionError):
    raise HTTPException(
        status_code=exc.status_code, detail={"error": {"code": exc.code, "message": exc.message}}
    ) from exc


@router.get("")
async def list_actions(
    status: str | None = None,
    assigned_to_me: bool = False,
    cursor: uuid.UUID | None = None,
    limit: int = Query(default=25, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = AIActionService(session)
    assigned_to_user_id = user.id if assigned_to_me else None
    actions = await service.list_actions(
        status=status, assigned_to_user_id=assigned_to_user_id, cursor=cursor, limit=limit
    )
    return envelope([AIActionOut.model_validate(a) for a in actions])


@router.get("/{action_id}")
async def get_action(
    action_id: uuid.UUID,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = AIActionService(session)
    try:
        action = await service.get(action_id)
    except AIActionError as exc:
        _raise_from(exc)
    return envelope(AIActionOut.model_validate(action))


@router.post("/{action_id}/approve")
async def approve_action(
    action_id: uuid.UUID,
    body: ApproveRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = AIActionService(session)
    try:
        action = await service.approve(
            action_id, user=user, idempotency_key=idempotency_key, body=body
        )
    except AIActionError as exc:
        _raise_from(exc)
    return envelope(AIActionOut.model_validate(action))


@router.post("/{action_id}/reject")
async def reject_action(
    action_id: uuid.UUID,
    body: RejectRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = AIActionService(session)
    try:
        action = await service.reject(action_id, user=user, body=body)
    except AIActionError as exc:
        _raise_from(exc)
    return envelope(AIActionOut.model_validate(action))


@router.post("/{action_id}/delegate")
async def delegate_action(
    action_id: uuid.UUID,
    body: DelegateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = AIActionService(session)
    try:
        action = await service.delegate(
            action_id, user=user, delegated_to_user_id=body.delegated_to_user_id
        )
    except AIActionError as exc:
        _raise_from(exc)
    return envelope(AIActionOut.model_validate(action))
