import { apiFetch } from "@/lib/api-client";

export type Automation = {
  id: string;
  name: string;
  mode: "dry_run" | "graduating" | "live" | "paused";
  is_active: boolean;
  trigger_type: string;
  trigger_config: Record<string, unknown>;
  action_type: string;
  action_config: Record<string, unknown>;
  graduation_threshold: number;
  approved_run_count: number;
  times_triggered: number;
  success_rate_pct: number | null;
  created_at: string;
};

export type AutomationRun = {
  id: string;
  automation_id: string;
  triggered_at: string;
  status: "simulated" | "success" | "failed" | "pending_approval";
  related_ai_action_id: string | null;
  error_message: string | null;
  target_entity_type: string | null;
  target_entity_id: string | null;
};

export const CANNED_TEMPLATES = [
  {
    name: "Follow up if no reply in 3 days",
    trigger_type: "no_reply_days",
    trigger_config: { days: 3 },
    action_type: "send_followup_email",
    action_config: {},
  },
  {
    name: "Invoice overdue reminder",
    trigger_type: "invoice_overdue",
    trigger_config: {},
    action_type: "send_invoice_reminder",
    action_config: {},
  },
  {
    name: "Welcome new client",
    trigger_type: "new_customer",
    trigger_config: { within_hours: 24 },
    action_type: "send_followup_email",
    action_config: {},
  },
] as const;

export function listAutomations(token: string): Promise<Automation[]> {
  return apiFetch<Automation[]>("/automations", { token });
}

export function createAutomation(
  input: {
    name: string;
    trigger_type: string;
    trigger_config: Record<string, unknown>;
    action_type: string;
    action_config: Record<string, unknown>;
  },
  token: string,
): Promise<Automation> {
  return apiFetch<Automation>("/automations", { method: "POST", body: input, token });
}

export function promoteMode(
  automationId: string,
  input: { mode: string; reason?: string },
  token: string,
): Promise<Automation> {
  return apiFetch<Automation>(`/automations/${automationId}/promote-mode`, {
    method: "POST",
    body: input,
    token,
  });
}

export function evaluateAutomation(
  automationId: string,
  token: string,
  idempotencyKey: string,
): Promise<AutomationRun[]> {
  return apiFetch<AutomationRun[]>(`/automations/${automationId}/evaluate`, {
    method: "POST",
    token,
    idempotencyKey,
  });
}

export function getDryRunResults(automationId: string, token: string): Promise<AutomationRun[]> {
  return apiFetch<AutomationRun[]>(`/automations/${automationId}/dry-run-results`, { token });
}
