"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Avatar } from "@/components/shared/avatar";
import { Shell } from "@/components/shared/shell";
import { TabBar } from "@/components/shared/tab-bar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getStoredAuth, type AuthResult } from "@/lib/auth";
import { getOrganization, type OrganizationProfile } from "@/lib/organization";
import {
  deleteOrganization,
  listIntegrations,
  listMembers,
  requestDeletion,
  updateMember,
  updateOrganizationProfile,
  type Member,
} from "@/lib/settings";

const TABS = ["Profile", "Team", "Integrations", "Billing", "Preferences", "Security", "API"] as const;

const PROVIDER_LABELS: Record<string, string> = {
  gmail: "Gmail",
  google_drive: "Google Drive",
  google_calendar: "Google Calendar",
  outlook: "Outlook",
  microsoft_365: "Microsoft 365",
  slack: "Slack",
  whatsapp: "WhatsApp Business",
  hubspot: "HubSpot",
  salesforce: "Salesforce",
  zoho_crm: "Zoho CRM",
  zoho_books: "Zoho Books",
  quickbooks: "QuickBooks",
};

function ProfileTab({ token, organization }: { token: string; organization?: OrganizationProfile }) {
  const queryClient = useQueryClient();
  const [industry, setIndustry] = useState(organization?.industry ?? "");
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deletionToken, setDeletionToken] = useState<string | null>(null);

  const saveMutation = useMutation({
    mutationFn: () => updateOrganizationProfile({ industry }, token),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["organization"] }),
  });

  const requestDeletionMutation = useMutation({
    mutationFn: () => requestDeletion(token),
    onSuccess: (result) => setDeletionToken(result.confirmation_token),
  });

  const confirmDeleteMutation = useMutation({
    mutationFn: () => deleteOrganization(deletionToken!, token),
    onSuccess: () => {
      window.location.href = "/signup";
    },
  });

  return (
    <div className="mt-6 flex flex-col gap-6">
      <div
        className="rounded-2xl p-5"
        style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)", boxShadow: "var(--neuron-shadow)" }}
      >
        <div className="flex items-center gap-3">
          {organization && <Avatar name={organization.name} size={36} />}
          <h2 className="text-[13px] font-bold">Company Profile</h2>
        </div>
        <div className="mt-3 max-w-sm">
          <label className="text-[12px] font-medium" style={{ color: "var(--neuron-text-dim)" }}>
            Industry
          </label>
          <Input value={industry} onChange={(e) => setIndustry(e.target.value)} placeholder="Marketing Agency" />
          <Button className="mt-3" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? "Saving…" : "Save"}
          </Button>
        </div>
      </div>

      <div className="rounded-2xl p-5" style={{ background: "var(--neuron-red-tint)", border: "1px solid #F3C6C6" }}>
        <h2 className="text-[13px] font-bold" style={{ color: "#9C2E2E" }}>
          Danger Zone
        </h2>
        <p className="mt-1 text-[12px]" style={{ color: "#7A2C2C" }}>
          Deleting your account is permanent and cannot be undone.
        </p>
        {!confirmingDelete ? (
          <button
            onClick={() => setConfirmingDelete(true)}
            className="mt-3 rounded-lg px-3 py-1.5 text-[12.5px] font-bold text-white"
            style={{ background: "var(--neuron-red)" }}
          >
            Delete Account
          </button>
        ) : !deletionToken ? (
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => setConfirmingDelete(false)}
              className="rounded-lg px-3 py-1.5 text-[12.5px] font-semibold"
              style={{ background: "var(--neuron-card)", color: "var(--neuron-text-dim)" }}
            >
              Cancel
            </button>
            <button
              onClick={() => requestDeletionMutation.mutate()}
              disabled={requestDeletionMutation.isPending}
              className="rounded-lg px-3 py-1.5 text-[12.5px] font-bold text-white"
              style={{ background: "var(--neuron-red)" }}
            >
              I understand — continue
            </button>
          </div>
        ) : (
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => {
                setConfirmingDelete(false);
                setDeletionToken(null);
              }}
              className="rounded-lg px-3 py-1.5 text-[12.5px] font-semibold"
              style={{ background: "var(--neuron-card)", color: "var(--neuron-text-dim)" }}
            >
              Cancel
            </button>
            <button
              onClick={() => confirmDeleteMutation.mutate()}
              disabled={confirmDeleteMutation.isPending}
              className="rounded-lg px-3 py-1.5 text-[12.5px] font-bold text-white"
              style={{ background: "var(--neuron-red)" }}
            >
              Confirm — permanently delete everything
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function TeamTab({ token }: { token: string }) {
  const queryClient = useQueryClient();
  const { data: members } = useQuery({ queryKey: ["members"], queryFn: () => listMembers(token) });

  const roleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) => updateMember(userId, { role }, token),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["members"] }),
  });

  return (
    <div className="mt-6 rounded-2xl p-5" style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)" }}>
      <h2 className="text-[13px] font-bold">Team</h2>
      <div className="mt-3 flex flex-col gap-2">
        {members?.map((m: Member) => (
          <div key={m.id} className="flex items-center justify-between rounded-lg p-2 transition-colors hover:bg-(--neuron-bg)" style={{ borderBottom: "1px solid var(--neuron-border)" }}>
            <div className="flex items-center gap-2.5">
              <Avatar name={m.name} size={30} />
              <div>
                <div className="text-[13px] font-semibold">{m.name}</div>
                <div className="text-[11.5px]" style={{ color: "var(--neuron-text-faint)" }}>
                  {m.email} · {m.status}
                </div>
              </div>
            </div>
            {m.role === "owner" ? (
              <span className="text-[11.5px] font-semibold" style={{ color: "var(--neuron-text-faint)" }}>
                Owner
              </span>
            ) : (
              <select
                value={m.role}
                onChange={(e) => roleMutation.mutate({ userId: m.id, role: e.target.value })}
                className="rounded-md border px-2 py-1 text-[12px]"
                style={{ borderColor: "var(--neuron-border)" }}
              >
                <option value="member">Member</option>
                <option value="admin">Admin</option>
              </select>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function IntegrationsTab({ token }: { token: string }) {
  const { data: integrations } = useQuery({
    queryKey: ["integrations"],
    queryFn: () => listIntegrations(token),
  });

  return (
    <div className="mt-6 grid grid-cols-2 gap-3">
      {integrations?.map((i) => (
        <div
          key={i.provider}
          className="flex items-center justify-between rounded-xl p-4"
          style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)" }}
        >
          <span className="text-[13px] font-semibold">{PROVIDER_LABELS[i.provider] ?? i.provider}</span>
          <span
            className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase"
            style={{ background: "var(--neuron-border)", color: "var(--neuron-text-faint)" }}
          >
            Not connected
          </span>
        </div>
      ))}
    </div>
  );
}

export default function SettingsPage() {
  const router = useRouter();
  const [auth, setAuth] = useState<AuthResult | null>(null);
  const [tab, setTab] = useState<(typeof TABS)[number]>("Profile");

  useEffect(() => {
    const stored = getStoredAuth();
    if (!stored) {
      router.replace("/login");
      return;
    }
    setAuth(stored);
  }, [router]);

  const { data: organization } = useQuery({
    queryKey: ["organization"],
    queryFn: () => getOrganization(auth!.token),
    enabled: !!auth,
  });

  if (!auth) return null;

  return (
    <Shell organizationName={auth.organization.name} userName={auth.user.name} token={auth.token}>
      <div className="mx-auto max-w-3xl">
        <h1 className="text-[22px] font-bold tracking-tight">Settings</h1>
        <p className="mt-1 text-[13px]" style={{ color: "var(--neuron-text-dim)" }}>
          Manage your account and preferences.
        </p>

        <div className="mt-4">
          <TabBar tabs={TABS} active={tab} onChange={setTab} layoutId="settings-tab" />
        </div>

        {tab === "Profile" && <ProfileTab token={auth.token} organization={organization} />}
        {tab === "Team" && <TeamTab token={auth.token} />}
        {tab === "Integrations" && <IntegrationsTab token={auth.token} />}
        {["Billing", "Preferences", "Security", "API"].includes(tab) && (
          <p className="mt-6 text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
            {tab} isn&apos;t built yet — Roadmap Phase 1 scopes Settings to Profile, Team, and
            Integrations (as &quot;Coming soon&quot; stubs), with the rest deferred.
          </p>
        )}
      </div>
    </Shell>
  );
}
