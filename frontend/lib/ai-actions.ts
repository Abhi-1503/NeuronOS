import { apiFetch } from "@/lib/api-client";

export type AIAction = {
  id: string;
  organization_id: string;
  title: string;
  description: string | null;
  action_type: string;
  severity_tier: "low" | "medium" | "high";
  is_reversible: boolean;
  reasoning: string | null;
  confidence_score: number | null;
  priority: "low" | "medium" | "high";
  status: "suggested" | "approved" | "rejected" | "delegated" | "executed" | "failed";
  suggested_amount: number | null;
  related_entity_type: string | null;
  related_entity_id: string | null;
  assigned_to_user_id: string | null;
  delegated_to_user_id: string | null;
  decided_by_user_id: string | null;
  decided_at: string | null;
  executed_at: string | null;
  generated_by_engine: string;
  created_at: string;
  updated_at: string;
};

export function listAIActions(token: string, status?: string): Promise<AIAction[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiFetch<AIAction[]>(`/ai-actions${query}`, { token });
}

export function getAIAction(id: string, token: string): Promise<AIAction> {
  return apiFetch<AIAction>(`/ai-actions/${id}`, { token });
}

// A fresh key per logical click, reused only if the *same* click is retried after a
// network failure (API Spec §0.5) — generating a new key per render/call would defeat
// the point, so callers must generate this once per user action, not per function call.
export function approveAIAction(
  id: string,
  input: { confirm_high_severity?: boolean; edited_content?: Record<string, unknown> },
  token: string,
  idempotencyKey: string,
): Promise<AIAction> {
  return apiFetch<AIAction>(`/ai-actions/${id}/approve`, {
    method: "POST",
    body: input,
    token,
    idempotencyKey,
  });
}

export function rejectAIAction(
  id: string,
  input: { reason?: string },
  token: string,
): Promise<AIAction> {
  return apiFetch<AIAction>(`/ai-actions/${id}/reject`, { method: "POST", body: input, token });
}
