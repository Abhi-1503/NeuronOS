import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_scoped_db
from app.api.v1.envelope import envelope
from app.models.user import User
from app.schemas.document import LinkedEntityOut, RejectLinkRequest
from app.services.linked_entity_service import LinkedEntityNotFoundError, LinkedEntityService

router = APIRouter(prefix="/linked-entities", tags=["linked-entities"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=404, detail={"error": {"code": "not_found", "message": "Linked entity not found."}}
    )


@router.get("/review-queue")
async def review_queue(
    entity_type: str | None = None,
    limit: int = Query(default=25, le=100),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = LinkedEntityService(session)
    links = await service.review_queue(entity_type=entity_type, limit=limit)
    return envelope([LinkedEntityOut.model_validate(link) for link in links])


@router.post("/{link_id}/confirm")
async def confirm_link(
    link_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = LinkedEntityService(session)
    try:
        link = await service.confirm(link_id, user=user)
    except LinkedEntityNotFoundError:
        raise _not_found()
    return envelope(LinkedEntityOut.model_validate(link))


@router.post("/{link_id}/reject")
async def reject_link(
    link_id: uuid.UUID,
    body: RejectLinkRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = LinkedEntityService(session)
    try:
        rejected, created = await service.reject(
            link_id,
            user=user,
            correct_target_type=body.correct_target_type,
            correct_target_id=body.correct_target_id,
        )
    except LinkedEntityNotFoundError:
        raise _not_found()
    return envelope(
        {
            "rejected": LinkedEntityOut.model_validate(rejected),
            "created": LinkedEntityOut.model_validate(created) if created else None,
        }
    )
