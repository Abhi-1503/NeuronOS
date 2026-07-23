import uuid
from datetime import datetime

from pydantic import BaseModel


class OverviewOut(BaseModel):
    total_revenue: float
    new_deals: int
    revenue_at_risk: float
    revenue_at_risk_customer_count: int
    open_invoices: int
    deltas: dict[str, float]


class RevenueTrendPoint(BaseModel):
    day_of_period: int
    this_period: float
    last_period: float | None


class RevenueBySourceSlice(BaseModel):
    label: str
    revenue: float
    pct: float


class TopCustomerOut(BaseModel):
    id: uuid.UUID
    name: str
    revenue_total: float
    deal_count: int
    relationship_score: int | None


class ScoreHistoryPoint(BaseModel):
    score: int
    algorithm_version: str
    computed_at: datetime
