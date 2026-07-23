"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Mail, UserPlus, Workflow } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Shell } from "@/components/shared/shell";
import { TabBar } from "@/components/shared/tab-bar";
import { Button } from "@/components/ui/button";
import {
  CANNED_TEMPLATES,
  createAutomation,
  evaluateAutomation,
  listAutomations,
  promoteMode,
  type Automation,
} from "@/lib/automations";
import { getStoredAuth, type AuthResult } from "@/lib/auth";

const TABS = ["My Automations", "Templates"] as const;

const MODE_STYLE: Record<string, { bg: string; fg: string; label: string }> = {
  dry_run: { bg: "var(--neuron-blue-tint)", fg: "var(--neuron-blue)", label: "Dry Run" },
  graduating: { bg: "var(--neuron-amber-tint)", fg: "var(--neuron-amber)", label: "Graduating" },
  live: { bg: "var(--neuron-green-tint)", fg: "var(--neuron-green)", label: "Live" },
  paused: { bg: "var(--neuron-border)", fg: "var(--neuron-text-faint)", label: "Paused" },
};

const TRIGGER_TYPE_ICON: Record<string, typeof Workflow> = {
  no_reply_days: Mail,
  invoice_overdue: Mail,
  new_customer: UserPlus,
};

const TRIGGER_TYPE_DESCRIPTION: Record<string, string> = {
  no_reply_days: "Automatically send follow-up email if no response",
  invoice_overdue: "Automatically send a reminder once an invoice is overdue",
  new_customer: "Send welcome email and onboarding docs to a new customer",
};

function AutomationRow({ automation, token }: { automation: Automation; token: string }) {
  const queryClient = useQueryClient();
  const mode = MODE_STYLE[automation.mode];
  const Icon = TRIGGER_TYPE_ICON[automation.trigger_type] ?? Workflow;

  const evaluateMutation = useMutation({
    mutationFn: () => evaluateAutomation(automation.id, token, crypto.randomUUID()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["automations"] });
      queryClient.invalidateQueries({ queryKey: ["ai-actions"] });
    },
  });

  const promoteMutation = useMutation({
    mutationFn: (mode: string) => promoteMode(automation.id, { mode }, token),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["automations"] }),
  });

  return (
    <div
      className="neuron-hover-lift rounded-2xl p-4"
      style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)" }}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex gap-3">
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
            style={{ background: "var(--neuron-primary-tint)", color: "var(--neuron-primary-dark)" }}
          >
            <Icon size={17} strokeWidth={2} />
          </div>
          <div>
            <div className="text-[14px] font-bold">{automation.name}</div>
            <div className="mt-0.5 text-[12px]" style={{ color: "var(--neuron-text-faint)" }}>
              {TRIGGER_TYPE_DESCRIPTION[automation.trigger_type] ?? "Custom trigger"}
            </div>
          </div>
        </div>
        <span
          className="shrink-0 rounded-full px-2.5 py-1 text-[10.5px] font-bold uppercase tracking-wide"
          style={{ background: mode.bg, color: mode.fg }}
        >
          {mode.label}
          {automation.mode === "graduating" && ` · ${automation.approved_run_count}/${automation.graduation_threshold}`}
        </span>
      </div>

      {automation.mode === "graduating" && (
        <div className="mt-2.5">
          <div className="text-[11px] font-semibold" style={{ color: "var(--neuron-amber)" }}>
            {automation.approved_run_count} of {automation.graduation_threshold} approved runs needed before
            this runs unsupervised
          </div>
          <div className="mt-1 h-1.5 w-full rounded-full" style={{ background: "#EEF0F5" }}>
            <div
              className="h-full rounded-full"
              style={{
                width: `${Math.round((automation.approved_run_count / automation.graduation_threshold) * 100)}%`,
                background: "var(--neuron-amber)",
              }}
            />
          </div>
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-5">
        <div className="text-[11.5px]" style={{ color: "var(--neuron-text-faint)" }}>
          Triggered <b style={{ color: "var(--neuron-text)" }}>{automation.times_triggered} times</b>
        </div>
        {automation.success_rate_pct !== null && (
          <div className="text-[11.5px]" style={{ color: "var(--neuron-text-faint)" }}>
            Success <b style={{ color: "var(--neuron-text)" }}>{automation.success_rate_pct}%</b>
          </div>
        )}
      </div>

      {automation.mode === "graduating" && (
        <div className="mt-2 text-[11px] italic" style={{ color: "var(--neuron-text-faint)" }}>
          A rejection resets this progress to 0 — it&rsquo;s a signal the logic needs another look, not just
          a delay.
        </div>
      )}

      <div className="mt-3.5 flex flex-wrap gap-2">
        {automation.mode === "dry_run" && (
          <>
            <button
              onClick={() => evaluateMutation.mutate()}
              disabled={evaluateMutation.isPending}
              className="rounded-lg px-3.5 py-2 text-[12.5px] font-semibold"
              style={{ background: "#fff", border: "1px solid var(--neuron-border)" }}
            >
              {evaluateMutation.isPending ? "Checking…" : "Check Now"}
            </button>
            <button
              onClick={() => promoteMutation.mutate("graduating")}
              disabled={promoteMutation.isPending}
              className="rounded-lg px-3.5 py-2 text-[12.5px] font-bold text-white"
              style={{ background: "var(--neuron-primary)" }}
            >
              Advance to Graduating
            </button>
          </>
        )}
        {automation.mode === "graduating" && (
          <button
            onClick={() => evaluateMutation.mutate()}
            disabled={evaluateMutation.isPending}
            className="rounded-lg px-3.5 py-2 text-[12.5px] font-semibold"
            style={{ background: "#fff", border: "1px solid var(--neuron-border)" }}
          >
            {evaluateMutation.isPending ? "Checking…" : "Check Now"}
          </button>
        )}
        {automation.mode === "live" && (
          <button
            onClick={() => promoteMutation.mutate("paused")}
            disabled={promoteMutation.isPending}
            className="rounded-lg px-3.5 py-2 text-[12.5px] font-semibold"
            style={{ background: "#fff", border: "1px solid var(--neuron-border)" }}
          >
            Pause
          </button>
        )}
        {automation.mode === "paused" && (
          <button
            onClick={() => promoteMutation.mutate("graduating")}
            disabled={promoteMutation.isPending}
            className="rounded-lg px-3.5 py-2 text-[12.5px] font-semibold"
            style={{ background: "#fff", border: "1px solid var(--neuron-border)" }}
          >
            Resume as Graduating
          </button>
        )}
      </div>
    </div>
  );
}

export default function AutomationsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [auth, setAuth] = useState<AuthResult | null>(null);
  const [tab, setTab] = useState<(typeof TABS)[number]>("My Automations");

  useEffect(() => {
    const stored = getStoredAuth();
    if (!stored) {
      router.replace("/login");
      return;
    }
    setAuth(stored);
  }, [router]);

  const { data: automations, isLoading } = useQuery({
    queryKey: ["automations"],
    queryFn: () => listAutomations(auth!.token),
    enabled: !!auth,
  });

  const createMutation = useMutation({
    mutationFn: (template: (typeof CANNED_TEMPLATES)[number]) => createAutomation(template, auth!.token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["automations"] });
      setTab("My Automations");
    },
  });

  if (!auth) return null;

  const existingTriggerTypes = new Set(automations?.map((a) => a.trigger_type));
  const availableTemplates = CANNED_TEMPLATES.filter((t) => !existingTriggerTypes.has(t.trigger_type));

  return (
    <Shell organizationName={auth.organization.name} userName={auth.user.name} token={auth.token}>
      <div className="mx-auto max-w-2xl">
        <h1 className="text-[22px] font-bold tracking-tight">Automations</h1>
        <p className="mt-1 text-[13px]" style={{ color: "var(--neuron-text-dim)" }}>
          Every automation earns trust in stages — nothing skips straight to sending on its own.
        </p>

        <div className="mt-5">
          <TabBar tabs={TABS} active={tab} onChange={setTab} layoutId="automations-tab" />
        </div>

        <div
          className="mt-4 flex flex-wrap items-center gap-4 rounded-xl p-3"
          style={{ background: "#fff", border: "1px solid var(--neuron-border)" }}
        >
          <span className="flex items-center gap-1.5 text-[11.5px]" style={{ color: "var(--neuron-text-dim)" }}>
            <span
              className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase"
              style={{ background: "var(--neuron-blue-tint)", color: "var(--neuron-blue)" }}
            >
              Dry Run
            </span>
            Simulates only — nothing sent
          </span>
          <span className="flex items-center gap-1.5 text-[11.5px]" style={{ color: "var(--neuron-text-dim)" }}>
            <span
              className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase"
              style={{ background: "var(--neuron-amber-tint)", color: "var(--neuron-amber)" }}
            >
              Graduating
            </span>
            Each run needs approval until trust is earned
          </span>
          <span className="flex items-center gap-1.5 text-[11.5px]" style={{ color: "var(--neuron-text-dim)" }}>
            <span
              className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase"
              style={{ background: "var(--neuron-green-tint)", color: "var(--neuron-green)" }}
            >
              Live
            </span>
            Runs unsupervised — earned, not default
          </span>
        </div>

        {tab === "My Automations" ? (
          <div className="mt-5 flex flex-col gap-3">
            {isLoading && (
              <p className="text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
                Loading…
              </p>
            )}
            {automations?.length === 0 && (
              <p className="text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
                No automations yet — add one from the Templates tab.
              </p>
            )}
            {automations?.map((a, i) => (
              <motion.div
                key={a.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: Math.min(i, 8) * 0.05 }}
              >
                <AutomationRow automation={a} token={auth.token} />
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="mt-5 flex flex-col gap-2">
            {availableTemplates.length === 0 && (
              <p className="text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
                You&rsquo;ve added every available template.
              </p>
            )}
            {availableTemplates.map((template) => (
              <div
                key={template.trigger_type}
                className="neuron-hover-lift flex items-center justify-between rounded-xl p-4"
                style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)" }}
              >
                <span className="text-[13px] font-semibold">{template.name}</span>
                <Button onClick={() => createMutation.mutate(template)} disabled={createMutation.isPending}>
                  Add
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </Shell>
  );
}
