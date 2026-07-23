import { apiFetch } from "@/lib/api-client";

export type RecommendedAction = {
  id: string;
  title: string;
  reasoning: string | null;
  confidence_score: number | null;
  severity_tier: "low" | "medium" | "high";
  status: string;
};

export type CustomerSummary = {
  id: string;
  name: string;
  status: string;
  relationship_score: number | null;
  revenue_total: number;
  last_contact_at: string | null;
};

export type Customer = CustomerSummary & {
  organization_id: string;
  owner_user_id: string | null;
  score_algorithm_version: string;
  currency: string;
  source: string;
  created_at: string;
  updated_at: string;
  ai_summary: string | null;
  recommended_next_action: RecommendedAction | null;
};

export type TimelineEvent = {
  id: string;
  customer_id: string;
  event_type: string;
  title: string;
  body: string | null;
  occurred_at: string;
  created_at: string;
};

export function listCustomers(token: string): Promise<CustomerSummary[]> {
  return apiFetch<CustomerSummary[]>("/customers", { token });
}

export function createCustomer(
  input: { name: string; last_contact_at?: string },
  token: string,
): Promise<Customer> {
  return apiFetch<Customer>("/customers", { method: "POST", body: input, token });
}

export function getCustomer(id: string, token: string): Promise<Customer> {
  return apiFetch<Customer>(`/customers/${id}`, { token });
}

export function getCustomerTimeline(id: string, token: string): Promise<TimelineEvent[]> {
  return apiFetch<TimelineEvent[]>(`/customers/${id}/timeline`, { token });
}

export function addTimelineEvent(
  customerId: string,
  input: { event_type: string; title: string; body?: string },
  token: string,
): Promise<TimelineEvent> {
  return apiFetch<TimelineEvent>(`/customers/${customerId}/timeline`, {
    method: "POST",
    body: input,
    token,
  });
}
