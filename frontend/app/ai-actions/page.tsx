"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Shell } from "@/components/shared/shell";
import { TabBar } from "@/components/shared/tab-bar";
import { approveAIAction, listAIActions, rejectAIAction, type AIAction } from "@/lib/ai-actions";
import { getStoredAuth, type AuthResult } from "@/lib/auth";

const TABS = ["Suggested", "All Tasks", "Completed", "Delegated"] as const;
type Tab = (typeof TABS)[number];

const TAB_STATUS: Record<Tab, string | undefined> = {
  Suggested: "suggested",
  "All Tasks": undefined,
  Completed: "executed",
  Delegated: "delegated",
};

const SEVERITY_COLOR: Record<string, { fg: string; bg: string; border: string }> = {
  low: { fg: "var(--neuron-text-dim)", bg: "var(--neuron-border)", border: "var(--neuron-text-faint)" },
  medium: { fg: "var(--neuron-amber)", bg: "var(--neuron-amber-tint)", border: "var(--neuron-amber)" },
  high: { fg: "var(--neuron-red)", bg: "var(--neuron-red-tint)", border: "var(--neuron-red)" },
};

function formatINR(value: number): string {
  if (value >= 100000) return `₹${(value / 100000).toFixed(2)}L`;
  return `₹${value.toLocaleString("en-IN")}`;
}

function confidenceColor(score: number): string {
  if (score >= 0.8) return "var(--neuron-green)";
  if (score >= 0.5) return "var(--neuron-amber)";
  return "var(--neuron-red)";
}

function InfoIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4M12 8h.01" />
    </svg>
  );
}

function ActionCard({ action, token }: { action: AIAction; token: string }) {
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const severity = SEVERITY_COLOR[action.severity_tier];

  const approveMutation = useMutation({
    mutationFn: (confirmHighSeverity: boolean) =>
      approveAIAction(
        action.id,
        confirmHighSeverity ? { confirm_high_severity: true } : {},
        token,
        crypto.randomUUID(),
      ),
    onSuccess: () => {
      setConfirming(false);
      queryClient.invalidateQueries({ queryKey: ["ai-actions"] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: () => rejectAIAction(action.id, {}, token),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ai-actions"] }),
  });

  function handleApproveClick() {
    if (action.severity_tier === "high" && !confirming) {
      setConfirming(true);
      return;
    }
    approveMutation.mutate(action.severity_tier === "high");
  }

  return (
    <div
      className="neuron-hover-lift rounded-2xl p-4"
      style={{
        background:
          action.severity_tier === "high"
            ? "linear-gradient(180deg,#FEFBFB,#ffffff)"
            : "var(--neuron-card)",
        border: action.severity_tier === "high" ? "1px solid #F3C6C6" : "1px solid var(--neuron-border)",
        borderLeftWidth: "4px",
        borderLeftColor: severity.border,
      }}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[14px] font-bold">{action.title}</span>
            <span
              className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide"
              style={{ background: severity.bg, color: severity.fg }}
            >
              {action.severity_tier}
            </span>
            <span
              className="rounded-full px-2 py-0.5 text-[10px] font-semibold"
              style={{ border: "1px solid var(--neuron-border)", color: "var(--neuron-text-faint)" }}
            >
              {action.is_reversible ? "Reversible" : "Not reversible once sent"}
            </span>
          </div>
          {action.description && (
            <div className="mt-0.5 text-[12px]" style={{ color: "var(--neuron-text-faint)" }}>
              {action.description}
            </div>
          )}
        </div>
        {action.suggested_amount !== null && (
          <div className="shrink-0 text-right text-[15px] font-bold">
            {formatINR(action.suggested_amount)}
          </div>
        )}
      </div>

      {/* Reasoning next to the conclusion, not behind a "why?" expander — non-negotiable
          per Blueprint §2.7 / API Spec §7. */}
      {action.reasoning && (
        <div
          className="mt-3 flex items-start gap-2 rounded-lg p-2.5"
          style={{ background: "var(--neuron-bg)" }}
        >
          <span className="mt-0.5" style={{ color: "var(--neuron-text-faint)" }}>
            <InfoIcon />
          </span>
          <div>
            <div
              className="text-[10.5px] font-bold uppercase tracking-wide"
              style={{ color: "var(--neuron-text-faint)" }}
            >
              Reasoning
            </div>
            <div className="text-[12px] leading-relaxed" style={{ color: "var(--neuron-text-dim)" }}>
              {action.reasoning}
            </div>
          </div>
        </div>
      )}

      {action.confidence_score !== null && (
        <div className="mt-2.5 flex items-center gap-2">
          <span className="text-[11px] font-semibold whitespace-nowrap" style={{ color: "var(--neuron-text-faint)" }}>
            Confidence
          </span>
          <div className="h-1.25 w-30 rounded-full" style={{ background: "#EEF0F5" }}>
            <div
              className="h-full rounded-full"
              style={{
                width: `${Math.round(action.confidence_score * 100)}%`,
                background: confidenceColor(action.confidence_score),
              }}
            />
          </div>
          <span className="text-[11px] font-bold" style={{ color: confidenceColor(action.confidence_score) }}>
            {Math.round(action.confidence_score * 100)}%
          </span>
        </div>
      )}

      {/* Severity-gated confirmation: a distinct, harder-to-misclick panel for high
          severity — not merely a different button color (Blueprint §3.4). */}
      {confirming && action.severity_tier === "high" ? (
        <div
          className="mt-3.5 rounded-xl p-3.5"
          style={{ background: "var(--neuron-red-tint)", border: "1px solid #F3C6C6" }}
        >
          <div className="text-[12.5px] font-bold" style={{ color: "#9C2E2E" }}>
            ⚠ This action is high-severity and hard to reverse
          </div>
          <p className="mt-1 text-[12px]" style={{ color: "#7A2C2C" }}>
            Confirm you want to proceed — this cannot be undone.
          </p>
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => setConfirming(false)}
              className="rounded-lg px-3.5 py-2 text-[12.5px] font-semibold"
              style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)", color: "var(--neuron-text-dim)" }}
            >
              Cancel
            </button>
            <button
              onClick={handleApproveClick}
              disabled={approveMutation.isPending}
              className="rounded-lg px-4 py-2 text-[12.5px] font-bold text-white"
              style={{ background: "var(--neuron-red)" }}
            >
              Confirm &amp; Send
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-3.5 flex items-center gap-2">
          <button
            className="rounded-lg px-3.5 py-2 text-[12.5px] font-semibold"
            style={{ background: "#fff", border: "1px solid var(--neuron-border)" }}
          >
            Review
          </button>
          <button
            onClick={() => rejectMutation.mutate()}
            disabled={rejectMutation.isPending}
            className="rounded-lg px-3.5 py-2 text-[12.5px] font-semibold"
            style={{ background: "var(--neuron-border)", color: "var(--neuron-text-dim)" }}
          >
            Dismiss
          </button>
          <button
            onClick={handleApproveClick}
            disabled={approveMutation.isPending}
            className="rounded-lg px-4 py-2 text-[12.5px] font-bold text-white"
            style={{
              background:
                action.severity_tier === "high"
                  ? "var(--neuron-red)"
                  : action.severity_tier === "medium"
                    ? "var(--neuron-amber)"
                    : "var(--neuron-primary)",
            }}
          >
            {action.severity_tier === "high" ? "⚠ Review & Confirm" : "Approve"}
          </button>
        </div>
      )}
    </div>
  );
}

export default function AIActionsPage() {
  const router = useRouter();
  const [auth, setAuth] = useState<AuthResult | null>(null);
  const [tab, setTab] = useState<Tab>("Suggested");

  useEffect(() => {
    const stored = getStoredAuth();
    if (!stored) {
      router.replace("/login");
      return;
    }
    setAuth(stored);
  }, [router]);

  const { data: actions, isLoading } = useQuery({
    queryKey: ["ai-actions", tab],
    queryFn: () => listAIActions(auth!.token, TAB_STATUS[tab]),
    enabled: !!auth,
  });

  if (!auth) return null;

  return (
    <Shell organizationName={auth.organization.name} userName={auth.user.name} token={auth.token}>
      <div className="mx-auto max-w-2xl">
        <h1 className="text-[22px] font-bold tracking-tight">AI Actions</h1>
        <p className="mt-1 text-[13px]" style={{ color: "var(--neuron-text-dim)" }}>
          Tasks NeuronOS can do for you — every suggestion shows its reasoning, confidence,
          and how much confirmation it needs.
        </p>

        <div className="mt-5">
          <TabBar tabs={TABS} active={tab} onChange={setTab} layoutId="ai-actions-tab" />
        </div>

        <div
          className="mt-4 flex flex-wrap items-center gap-3.5 rounded-xl p-3"
          style={{ background: "#fff", border: "1px solid var(--neuron-border)" }}
        >
          <span className="text-[11.5px] font-bold">Severity:</span>
          <span className="flex items-center gap-1.5 text-[11.5px]" style={{ color: "var(--neuron-text-dim)" }}>
            <span className="h-2 w-2 rounded-full" style={{ background: "var(--neuron-text-faint)" }} />
            Low — routine, single-click approve
          </span>
          <span className="flex items-center gap-1.5 text-[11.5px]" style={{ color: "var(--neuron-text-dim)" }}>
            <span className="h-2 w-2 rounded-full" style={{ background: "var(--neuron-amber)" }} />
            Medium — one click, visually flagged
          </span>
          <span className="flex items-center gap-1.5 text-[11.5px]" style={{ color: "var(--neuron-text-dim)" }}>
            <span className="h-2 w-2 rounded-full" style={{ background: "var(--neuron-red)" }} />
            High — irreversible/financial, requires explicit confirm
          </span>
        </div>

        <h2 className="mt-5 text-[13px] font-bold">
          {tab === "Suggested" ? "Suggested for you" : tab}
        </h2>
        <div className="mt-3 flex flex-col gap-3">
          {isLoading && (
            <p className="text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
              Loading…
            </p>
          )}
          {actions?.length === 0 && (
            <p className="text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
              Nothing here right now.
            </p>
          )}
          {actions?.map((action: AIAction, i) => (
            <motion.div
              key={action.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: Math.min(i, 8) * 0.05 }}
            >
              <ActionCard action={action} token={auth.token} />
            </motion.div>
          ))}
        </div>
      </div>
    </Shell>
  );
}
