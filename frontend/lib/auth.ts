import { apiFetch } from "@/lib/api-client";

export type Organization = {
  id: string;
  name: string;
  plan: string;
  terms_accepted_at: string | null;
};

export type User = {
  id: string;
  organization_id: string;
  email: string;
  name: string;
  role: "owner" | "admin" | "member";
  status: "invited" | "active" | "suspended";
};

export type AuthResult = {
  organization: Organization;
  user: User;
  token: string;
  refresh_token: string;
};

const AUTH_STORAGE_KEY = "neuronos_auth";

// localStorage, not an httpOnly cookie — a deliberate Phase 0 simplification (no
// server-rendered session handling exists yet). Revisit before any real design partner
// data is at stake; a stolen token is readable by any script on the page under this scheme.
// Stores the full result (not just the token) since Phase 0 has no `GET /organization`/
// `GET /me` endpoint yet (that's Settings module, Phase 1) — the shell reads org/user
// display info back from here instead of a round-trip that doesn't exist.
export function storeAuth(result: AuthResult) {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(result));
}

export function getStoredAuth(): AuthResult | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthResult;
  } catch {
    return null;
  }
}

export function getStoredToken(): string | null {
  return getStoredAuth()?.token ?? null;
}

export function clearStoredToken() {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

export function signup(input: {
  organization_name: string;
  name: string;
  email: string;
  password: string;
}): Promise<AuthResult> {
  return apiFetch<AuthResult>("/auth/signup", { method: "POST", body: input });
}

export function login(input: { email: string; password: string }): Promise<AuthResult> {
  return apiFetch<AuthResult>("/auth/login", { method: "POST", body: input });
}

export function acceptTerms(version: string, token: string): Promise<Organization> {
  return apiFetch<Organization>("/organization/accept-terms", {
    method: "POST",
    body: { version },
    token,
  });
}

export function inviteTeammate(
  input: { email: string; role: "admin" | "member" },
  token: string,
): Promise<{ invitation_id: string; email: string; status: string }> {
  return apiFetch("/auth/invite", { method: "POST", body: input, token });
}
