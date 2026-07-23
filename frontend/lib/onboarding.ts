import { apiFetch } from "@/lib/api-client";

export type OnboardingStep = { key: string; label: string; completed: boolean };

export type OnboardingStatus = {
  onboarding_method: string | null;
  steps: OnboardingStep[];
  first_insight_at: string | null;
};

export type FirstInsight = {
  type: "risk_flag" | "all_clear";
  message: string;
  ai_action_id: string | null;
};

export type OnboardingCompleteResult = OnboardingStatus & {
  first_insight: FirstInsight | null;
};

export function getOnboardingStatus(token: string): Promise<OnboardingStatus> {
  return apiFetch<OnboardingStatus>("/onboarding/status", { token });
}

export function selectOnboardingMethod(
  method: "integration" | "documents" | "manual_customers",
  token: string,
): Promise<OnboardingStatus> {
  return apiFetch<OnboardingStatus>("/onboarding/select-method", {
    method: "POST",
    body: { method },
    token,
  });
}

export function completeOnboarding(token: string): Promise<OnboardingCompleteResult> {
  return apiFetch<OnboardingCompleteResult>("/onboarding/complete", { method: "POST", token });
}
