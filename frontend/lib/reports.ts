import { apiFetch } from "@/lib/api-client";

export type Overview = {
  total_revenue: number;
  new_deals: number;
  revenue_at_risk: number;
  revenue_at_risk_customer_count: number;
  open_invoices: number;
  deltas: Record<string, number>;
};

export type RevenueTrendPoint = {
  day_of_period: number;
  this_period: number;
  last_period: number | null;
};

export type RevenueBySourceSlice = { label: string; revenue: number; pct: number };

export type TopCustomer = {
  id: string;
  name: string;
  revenue_total: number;
  deal_count: number;
  relationship_score: number | null;
};

export function getOverview(token: string, period = "this_month"): Promise<Overview> {
  return apiFetch<Overview>(`/reports/overview?period=${period}`, { token });
}

export function getRevenueTrend(token: string): Promise<RevenueTrendPoint[]> {
  return apiFetch<RevenueTrendPoint[]>("/reports/revenue-trend", { token });
}

export function getRevenueBySource(token: string): Promise<RevenueBySourceSlice[]> {
  return apiFetch<RevenueBySourceSlice[]>("/reports/revenue-by-source", { token });
}

export function getTopCustomers(token: string): Promise<TopCustomer[]> {
  return apiFetch<TopCustomer[]>("/reports/top-customers", { token });
}

export type ScoreHistoryPoint = {
  score: number;
  algorithm_version: string;
  computed_at: string;
};

export function getOrganizationScoreHistory(token: string): Promise<ScoreHistoryPoint[]> {
  return apiFetch<ScoreHistoryPoint[]>("/reports/score-history?entity_type=organization", { token });
}
