import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_scoped_db
from app.api.v1.envelope import envelope
from app.models.user import User
from app.schemas.customer import (
    CustomerCreate,
    CustomerOut,
    CustomerSummaryOut,
    CustomerUpdate,
    DealCreate,
    DealOut,
    DealUpdate,
    RecommendedActionOut,
    TimelineEventCreate,
    TimelineEventOut,
)
from app.services.customer_service import CustomerNotFoundError, CustomerService, DealNotFoundError

router = APIRouter(prefix="/customers", tags=["customers"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=404, detail={"error": {"code": "not_found", "message": "Customer not found."}}
    )


async def _customer_out(service: CustomerService, customer) -> CustomerOut:
    recommended = await service.get_recommended_next_action(customer.id)
    return CustomerOut(
        id=customer.id,
        organization_id=customer.organization_id,
        name=customer.name,
        owner_user_id=customer.owner_user_id,
        status=customer.status,
        relationship_score=customer.relationship_score,
        score_algorithm_version=customer.score_algorithm_version,
        revenue_total=float(customer.revenue_total),
        currency=customer.currency,
        last_contact_at=customer.last_contact_at,
        source=customer.source,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        recommended_next_action=RecommendedActionOut.model_validate(recommended)
        if recommended
        else None,
    )


@router.get("")
async def list_customers(
    status: str | None = None,
    cursor: uuid.UUID | None = None,
    limit: int = Query(default=25, le=100),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = CustomerService(session)
    customers = await service.list_customers(status=status, cursor=cursor, limit=limit)
    return envelope([CustomerSummaryOut.model_validate(c) for c in customers])


@router.post("", status_code=201)
async def create_customer(
    body: CustomerCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = CustomerService(session)
    customer = await service.create(organization_id=user.organization_id, data=body)
    return envelope(await _customer_out(service, customer))


@router.get("/{customer_id}")
async def get_customer(
    customer_id: uuid.UUID,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = CustomerService(session)
    try:
        customer = await service.get(customer_id)
    except CustomerNotFoundError:
        raise _not_found()
    return envelope(await _customer_out(service, customer))


@router.patch("/{customer_id}")
async def update_customer(
    customer_id: uuid.UUID,
    body: CustomerUpdate,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = CustomerService(session)
    try:
        customer = await service.update(customer_id, body)
    except CustomerNotFoundError:
        raise _not_found()
    return envelope(await _customer_out(service, customer))


@router.delete("/{customer_id}", status_code=204)
async def delete_customer(
    customer_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> None:
    if user.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "permission_denied", "message": "Requires Admin or Owner."}},
        )
    service = CustomerService(session)
    try:
        await service.soft_delete(customer_id)
    except CustomerNotFoundError:
        raise _not_found()


@router.get("/{customer_id}/timeline")
async def get_timeline(
    customer_id: uuid.UUID,
    event_type: str | None = None,
    limit: int = Query(default=25, le=100),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = CustomerService(session)
    events = await service.get_timeline(customer_id, event_type=event_type, limit=limit)
    return envelope([TimelineEventOut.model_validate(e) for e in events])


@router.post("/{customer_id}/timeline", status_code=201)
async def add_timeline_event(
    customer_id: uuid.UUID,
    body: TimelineEventCreate,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = CustomerService(session)
    try:
        event = await service.add_timeline_event(customer_id, body)
    except CustomerNotFoundError:
        raise _not_found()
    return envelope(TimelineEventOut.model_validate(event))


@router.get("/{customer_id}/deals")
async def get_deals(
    customer_id: uuid.UUID,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = CustomerService(session)
    deals = await service.get_deals(customer_id)
    return envelope([DealOut.model_validate(d) for d in deals])


@router.post("/{customer_id}/deals", status_code=201)
async def add_deal(
    customer_id: uuid.UUID,
    body: DealCreate,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = CustomerService(session)
    try:
        deal = await service.add_deal(customer_id, body)
    except CustomerNotFoundError:
        raise _not_found()
    return envelope(DealOut.model_validate(deal))


@router.patch("/{customer_id}/deals/{deal_id}")
async def update_deal(
    customer_id: uuid.UUID,
    deal_id: uuid.UUID,
    body: DealUpdate,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = CustomerService(session)
    try:
        deal = await service.update_deal(customer_id, deal_id, body)
    except (CustomerNotFoundError, DealNotFoundError):
        raise HTTPException(
            status_code=404, detail={"error": {"code": "not_found", "message": "Deal not found."}}
        )
    return envelope(DealOut.model_validate(deal))
