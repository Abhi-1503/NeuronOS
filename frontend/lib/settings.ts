import { apiFetch } from "@/lib/api-client";

export type Member = {
  id: string;
  name: string;
  email: string;
  role: "owner" | "admin" | "member";
  status: "invited" | "active" | "suspended";
  last_login_at: string | null;
};

export type Integration = {
  provider: string;
  status: string;
  provider_review_status: string;
  last_synced_at: string | null;
};

export function updateOrganizationProfile(
  input: { name?: string; industry?: string; company_size?: string; timezone?: string },
  token: string,
) {
  return apiFetch("/organization", { method: "PATCH", body: input, token });
}

export function listMembers(token: string): Promise<Member[]> {
  return apiFetch<Member[]>("/organization/members", { token });
}

export function updateMember(
  userId: string,
  input: { role?: string; status?: string },
  token: string,
): Promise<Member> {
  return apiFetch<Member>(`/organization/members/${userId}`, { method: "PATCH", body: input, token });
}

export function listIntegrations(token: string): Promise<Integration[]> {
  return apiFetch<Integration[]>("/integrations", { token });
}

export function requestDeletion(token: string): Promise<{ confirmation_token: string; expires_at: string }> {
  return apiFetch("/organization/request-deletion", { method: "POST", token });
}

export function deleteOrganization(confirmationToken: string, token: string): Promise<void> {
  return apiFetch("/organization", {
    method: "DELETE",
    body: { confirmation_token: confirmationToken },
    token,
  });
}
