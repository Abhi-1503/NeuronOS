import { apiFetch } from "@/lib/api-client";

export type OrganizationProfile = {
  id: string;
  name: string;
  industry: string | null;
  company_size: string | null;
  timezone: string;
  plan: string;
  business_health_score: number | null;
  terms_accepted_version: string | null;
  terms_accepted_at: string | null;
  dpa_signed_at: string | null;
};

export function getOrganization(token: string): Promise<OrganizationProfile> {
  return apiFetch<OrganizationProfile>("/organization", { token });
}
