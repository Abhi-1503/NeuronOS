"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { NeuronMark } from "@/components/shared/neuron-mark";
import { Shell } from "@/components/shared/shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { approveAIAction, listAIActions, rejectAIAction, type AIAction } from "@/lib/ai-actions";
import { listAutomations, type Automation } from "@/lib/automations";
import { getStoredAuth, type AuthResult } from "@/lib/auth";
import { sendMessage } from "@/lib/chat";
import { createCustomer } from "@/lib/customers";
import { listDocuments, type NeuronDocument } from "@/lib/documents";
import {
  completeOnboarding,
  getOnboardingStatus,
  selectOnboardingMethod,
  type FirstInsight,
} from "@/lib/onboarding";
import { getOrganization } from "@/lib/organization";

const SEVERITY_RANK: Record<AIAction["severity_tier"], number> = { high: 2, medium: 1, low: 0 };

const MODE_LABEL: Record<Automation["mode"], string> = {
  dry_run: "Dry Run",
  graduating: "Graduating",
  live: "Live",
  paused: "Paused",
};

const ACTION_CTA_LABEL: Record<string, string> = {
  send_followup_email: "Follow up now",
  send_invoice_reminder: "Send reminder",
  send_contract_email: "Send email",
  generate_invoice: "Review",
  create_task: "Review",
  prepare_meeting_brief: "Review",
};

function severityButtonColor(severity: AIAction["severity_tier"]): string {
  if (severity === "high") return "var(--neuron-red)";
  if (severity === "medium") return "var(--neuron-amber)";
  return "var(--neuron-primary)";
}

const SUGGESTION_CHIPS = [
  "What's my biggest risk?",
  "Who needs follow-up?",
  "Summarize this week",
];

function formatINR(value: number): string {
  if (value >= 100000) return `₹${(value / 100000).toFixed(2)}L`;
  return `₹${value.toLocaleString("en-IN")}`;
}

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good Morning";
  if (hour < 17) return "Good Afternoon";
  return "Good Evening";
}

function AIInsightCard({ action, token }: { action: AIAction; token: string }) {
  const queryClient = useQueryClient();
  const approveMutation = useMutation({
    mutationFn: () => approveAIAction(action.id, {}, token, crypto.randomUUID()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-actions"] });
    },
  });
  const rejectMutation = useMutation({
    mutationFn: () => rejectAIAction(action.id, {}, token),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ai-actions"] }),
  });

  return (
    <div
      className="neuron-hover-lift rounded-2xl p-4"
      style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)" }}
    >
      <div className="flex items-center justify-between">
        <div className="text-[11px] font-bold uppercase tracking-wide" style={{ color: "var(--neuron-text-faint)" }}>
          NeuronOS Insight
        </div>
        <div
          className="flex h-6 w-6 items-center justify-center rounded-full"
          style={{ background: "linear-gradient(135deg,#8B7CF6,#5A48D8)" }}
        >
          <NeuronMark size={13} variant="mono" color="#fff" />
        </div>
      </div>

      {action.suggested_amount !== null && action.severity_tier !== "low" && (
        <>
          <p className="mt-3 text-[12px]" style={{ color: "var(--neuron-text-dim)" }}>
            You are about to lose
          </p>
          <p className="text-[22px] font-bold" style={{ color: "var(--neuron-red)" }}>
            {formatINR(action.suggested_amount)}
          </p>
        </>
      )}

      <div className="mt-3 text-[10.5px] font-bold uppercase tracking-wide" style={{ color: "var(--neuron-text-faint)" }}>
        Reason
      </div>
      <p className="mt-1 text-[13px] font-semibold">{action.title}</p>
      {/* Blueprint §2.7: reasoning shown inline, never behind a "why?" expander. */}
      {action.reasoning && (
        <p className="mt-1 text-[12px]" style={{ color: "var(--neuron-text-dim)" }}>
          {action.reasoning}
        </p>
      )}

      <div className="mt-3 flex gap-2">
        <button
          onClick={() => rejectMutation.mutate()}
          disabled={rejectMutation.isPending}
          className="rounded-lg px-3.5 py-2 text-[12.5px] font-semibold"
          style={{ background: "var(--neuron-border)", color: "var(--neuron-text-dim)" }}
        >
          Ignore
        </button>
        <button
          onClick={() => approveMutation.mutate()}
          disabled={approveMutation.isPending}
          className="rounded-lg px-3.5 py-2 text-[12.5px] font-bold text-white"
          style={{ background: "var(--neuron-primary)" }}
        >
          Approve
        </button>
      </div>
    </div>
  );
}

function KnowledgePreview({ documents }: { documents: NeuronDocument[] | undefined }) {
  return (
    <div className="neuron-hover-lift rounded-2xl p-4" style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)" }}>
      <div className="flex items-center justify-between">
        <h3 className="text-[12px] font-bold uppercase tracking-wide" style={{ color: "var(--neuron-text-faint)" }}>
          Knowledge
        </h3>
        <Link href="/knowledge" className="text-[11.5px] font-semibold" style={{ color: "var(--neuron-primary-dark)" }}>
          View all →
        </Link>
      </div>
      <div className="mt-2 flex flex-col gap-2">
        {documents?.length === 0 && (
          <p className="text-[12px]" style={{ color: "var(--neuron-text-faint)" }}>
            No documents yet.
          </p>
        )}
        {documents?.slice(0, 3).map((doc) => (
          <Link key={doc.id} href={`/knowledge/${doc.id}`} className="block text-[12.5px] font-medium">
            {doc.title}
          </Link>
        ))}
      </div>
    </div>
  );
}

function AutomationsPreview({ automations }: { automations: Automation[] | undefined }) {
  return (
    <div className="neuron-hover-lift rounded-2xl p-4" style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)" }}>
      <div className="flex items-center justify-between">
        <h3 className="text-[12px] font-bold uppercase tracking-wide" style={{ color: "var(--neuron-text-faint)" }}>
          Automations
        </h3>
        <Link href="/automations" className="text-[11.5px] font-semibold" style={{ color: "var(--neuron-primary-dark)" }}>
          View all →
        </Link>
      </div>
      <div className="mt-2 flex flex-col gap-2">
        {automations?.length === 0 && (
          <p className="text-[12px]" style={{ color: "var(--neuron-text-faint)" }}>
            None set up yet.
          </p>
        )}
        {automations?.slice(0, 3).map((automation) => (
          <div key={automation.id} className="flex items-center justify-between text-[12.5px] font-medium">
            <span>{automation.name}</span>
            <span className="text-[11px]" style={{ color: "var(--neuron-text-faint)" }}>
              {MODE_LABEL[automation.mode]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function QuickAskBox({ token }: { token: string }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);

  const askMutation = useMutation({
    mutationFn: (message: string) => sendMessage({ message }, token),
    onSuccess: (response) => {
      setAnswer(response.message.content);
    },
  });

  return (
    <div className="neuron-hover-lift rounded-2xl p-4" style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)" }}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (question.trim()) askMutation.mutate(question.trim());
        }}
        className="flex items-center gap-2"
      >
        <Input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask anything about your business…"
        />
        <Button type="submit" disabled={!question.trim() || askMutation.isPending}>
          {askMutation.isPending ? "…" : "Ask"}
        </Button>
      </form>
      {answer && (
        <div className="mt-3 rounded-xl p-3 text-[12.5px]" style={{ background: "var(--neuron-bg)" }}>
          <p className="whitespace-pre-wrap">{answer}</p>
          <Link href="/ai-workspace" className="mt-2 inline-block text-[11.5px] font-semibold" style={{ color: "var(--neuron-primary-dark)" }}>
            Continue in AI Workspace →
          </Link>
        </div>
      )}
    </div>
  );
}

const OTHER_PATHS = [
  {
    key: "integration" as const,
    title: "Connect an integration",
    description:
      "Connect Gmail (or another supported provider) and NeuronOS syncs recent email only — not your full mailbox history — to get to a first insight in minutes.",
    availability: "Available once Integrations ship (Phase 2)",
  },
  {
    key: "documents" as const,
    title: "Upload your key documents",
    description:
      "Upload 3–5 documents — a customer list, a contract, a proposal. One document is enough to generate a real AI summary.",
    availability: "Available once Knowledge ships (Phase 1)",
  },
];

function QuickAddCustomers({ token, onDone }: { token: string; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [addedCount, setAddedCount] = useState(0);
  const [name, setName] = useState("");
  const [lastContact, setLastContact] = useState("");
  const [insight, setInsight] = useState<FirstInsight | null>(null);

  const addMutation = useMutation({
    mutationFn: () =>
      createCustomer(
        { name, last_contact_at: lastContact ? new Date(lastContact).toISOString() : undefined },
        token,
      ),
    onSuccess: () => {
      setAddedCount((n) => n + 1);
      setName("");
      setLastContact("");
    },
  });

  const completeMutation = useMutation({
    mutationFn: () => completeOnboarding(token),
    onSuccess: (result) => {
      setInsight(result.first_insight);
      queryClient.invalidateQueries({ queryKey: ["organization"] });
      queryClient.invalidateQueries({ queryKey: ["ai-actions"] });
    },
  });

  if (insight) {
    return (
      <div
        className="rounded-2xl p-6"
        style={{
          background: insight.type === "risk_flag" ? "var(--neuron-primary-tint)" : "var(--neuron-green-tint)",
          border: "1px solid var(--neuron-border)",
        }}
      >
        <div className="text-[13px] font-bold" style={{ color: "var(--neuron-primary-dark)" }}>
          {insight.type === "risk_flag" ? "Here's what I found" : "All clear"}
        </div>
        <p className="mt-2 text-[13.5px]" style={{ color: "var(--neuron-text)" }}>
          {insight.message}
        </p>
        <Button className="mt-4" onClick={onDone}>
          Go to Pulse
        </Button>
      </div>
    );
  }

  return (
    <div
      className="rounded-2xl p-6"
      style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)" }}
    >
      <h2 className="text-[14px] font-bold">Add your top customers</h2>
      <p className="mt-1 text-[12.5px]" style={{ color: "var(--neuron-text-dim)" }}>
        Name + last contact date is enough to start. Added so far: {addedCount}.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim()) addMutation.mutate();
        }}
        className="mt-4 flex items-end gap-2"
      >
        <div className="flex-1">
          <label className="text-[12px] font-medium" style={{ color: "var(--neuron-text-dim)" }}>
            Customer name
          </label>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="ABC Ltd" />
        </div>
        <div className="flex-1">
          <label className="text-[12px] font-medium" style={{ color: "var(--neuron-text-dim)" }}>
            Last contact date (optional)
          </label>
          <Input type="date" value={lastContact} onChange={(e) => setLastContact(e.target.value)} />
        </div>
        <Button type="submit" disabled={!name.trim() || addMutation.isPending}>
          Add
        </Button>
      </form>

      {addedCount > 0 && (
        <Button
          className="mt-4 w-full"
          onClick={() => completeMutation.mutate()}
          disabled={completeMutation.isPending}
        >
          {completeMutation.isPending ? "Finding your first insight…" : "Get my first insight"}
        </Button>
      )}
    </div>
  );
}

export default function PulsePage() {
  const router = useRouter();
  const [auth, setAuth] = useState<AuthResult | null>(null);
  const [quickAddOpen, setQuickAddOpen] = useState(false);

  useEffect(() => {
    const stored = getStoredAuth();
    if (!stored) {
      router.replace("/login");
      return;
    }
    setAuth(stored);
  }, [router]);

  const { data: onboarding, refetch: refetchOnboarding } = useQuery({
    queryKey: ["onboarding-status"],
    queryFn: () => getOnboardingStatus(auth!.token),
    enabled: !!auth,
  });

  // Primed here (same query key the Shell's Business Health card reads) so it's already
  // cached by the time the sidebar mounts — the value itself isn't needed on this page.
  useQuery({
    queryKey: ["organization"],
    queryFn: () => getOrganization(auth!.token),
    enabled: !!auth && !!onboarding?.first_insight_at,
  });

  const { data: actions } = useQuery({
    queryKey: ["ai-actions"],
    queryFn: () => listAIActions(auth!.token, "suggested"),
    enabled: !!auth && !!onboarding?.first_insight_at,
  });

  const { data: documents } = useQuery({
    queryKey: ["documents"],
    queryFn: () => listDocuments(auth!.token, 3),
    enabled: !!auth && !!onboarding?.first_insight_at,
  });

  const { data: automations } = useQuery({
    queryKey: ["automations"],
    queryFn: () => listAutomations(auth!.token),
    enabled: !!auth && !!onboarding?.first_insight_at,
  });

  async function handleStartManualPath() {
    await selectOnboardingMethod("manual_customers", auth!.token);
    setQuickAddOpen(true);
  }

  if (!auth || !onboarding) return null;

  const isOnboarded = !!onboarding.first_insight_at;

  const topInsightAction = actions
    ?.slice()
    .sort((a, b) => {
      const severityDiff = SEVERITY_RANK[b.severity_tier] - SEVERITY_RANK[a.severity_tier];
      if (severityDiff !== 0) return severityDiff;
      return (b.confidence_score ?? 0) - (a.confidence_score ?? 0);
    })[0];

  return (
    <Shell
      organizationName={auth.organization.name}
      userName={auth.user.name}
      token={auth.token}
      rightRail={
        isOnboarded ? (
          <div className="flex flex-col gap-4">
            {topInsightAction && <AIInsightCard action={topInsightAction} token={auth.token} />}
            <KnowledgePreview documents={documents} />
            <AutomationsPreview automations={automations} />
          </div>
        ) : undefined
      }
    >
      <div className="mx-auto max-w-2xl">
        {!isOnboarded ? (
          quickAddOpen ? (
            <>
              <h1 className="text-[22px] font-bold tracking-tight">Add your top customers</h1>
              <div className="mt-6">
                <QuickAddCustomers token={auth.token} onDone={() => refetchOnboarding()} />
              </div>
            </>
          ) : (
            <>
              <h1 className="text-[22px] font-bold tracking-tight">
                How do you want to get started?
              </h1>
              <p className="mt-2 text-[13.5px]" style={{ color: "var(--neuron-text-dim)" }}>
                Pick one — you can add the others later. NeuronOS surfaces one real, specific
                insight from whatever you provide, usually within minutes.
              </p>

              <div className="mt-6 flex flex-col gap-3">
                <div
                  className="rounded-2xl p-5"
                  style={{
                    background: "var(--neuron-card)",
                    border: "1px solid var(--neuron-border)",
                    boxShadow: "var(--neuron-shadow)",
                  }}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h2 className="text-[14px] font-bold">Add your top customers</h2>
                      <p className="mt-1 text-[12.5px]" style={{ color: "var(--neuron-text-dim)" }}>
                        Add name + last contact date for your 5 most important customers — no
                        processing wait at all.
                      </p>
                    </div>
                    <Button onClick={handleStartManualPath} className="shrink-0">
                      Start
                    </Button>
                  </div>
                </div>

                {OTHER_PATHS.map((path) => (
                  <div
                    key={path.key}
                    className="rounded-2xl p-5"
                    style={{
                      background: "var(--neuron-card)",
                      border: "1px solid var(--neuron-border)",
                      boxShadow: "var(--neuron-shadow)",
                    }}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h2 className="text-[14px] font-bold">{path.title}</h2>
                        <p className="mt-1 text-[12.5px]" style={{ color: "var(--neuron-text-dim)" }}>
                          {path.description}
                        </p>
                      </div>
                      <button
                        disabled
                        className="shrink-0 rounded-lg px-3 py-1.5 text-[12.5px] font-semibold"
                        style={{
                          background: "var(--neuron-border)",
                          color: "var(--neuron-text-faint)",
                          cursor: "not-allowed",
                        }}
                      >
                        Start
                      </button>
                    </div>
                    <div className="mt-3 text-[11px] font-medium" style={{ color: "var(--neuron-text-faint)" }}>
                      {path.availability}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )
        ) : (
          <>
            <div>
              <h1 className="text-[22px] font-bold tracking-tight">
                {greeting()}, {auth.user.name.split(" ")[0]} 👋
              </h1>
              <p className="mt-0.5 text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
                {new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}
              </p>
            </div>

            <div className="mt-6">
              <QuickAskBox token={auth.token} />
              <div className="mt-2.5 flex flex-wrap gap-2">
                {SUGGESTION_CHIPS.map((chip) => (
                  <span
                    key={chip}
                    className="rounded-full px-3 py-1.5 text-[12px] font-medium"
                    style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)", color: "var(--neuron-text-dim)" }}
                  >
                    {chip}
                  </span>
                ))}
              </div>
            </div>

            <div className="mt-6">
              <h2 className="text-[14px] font-bold">Today&apos;s Focus</h2>
              <div className="mt-3 flex flex-col gap-2">
                {actions?.length === 0 && (
                  <p className="text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
                    Nothing needs your attention right now.
                  </p>
                )}
                {actions?.slice(0, 4).map((action: AIAction, i) => (
                  <div
                    key={action.id}
                    className="neuron-hover-lift flex items-start gap-3 rounded-xl p-4"
                    style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)", boxShadow: "var(--neuron-shadow)" }}
                  >
                    <div
                      className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white"
                      style={{ background: "var(--neuron-primary)" }}
                    >
                      {i + 1}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="text-[13.5px] font-bold">{action.title}</div>
                          {action.reasoning && (
                            <div className="mt-1 text-[12px]" style={{ color: "var(--neuron-text-dim)" }}>
                              {action.reasoning}
                            </div>
                          )}
                        </div>
                        {action.suggested_amount !== null && (
                          <div className="shrink-0 text-[13px] font-bold">{formatINR(action.suggested_amount)}</div>
                        )}
                      </div>
                      <Link
                        href="/ai-actions"
                        className="mt-2.5 inline-block rounded-lg px-3 py-1.5 text-[12px] font-bold text-white"
                        style={{ background: severityButtonColor(action.severity_tier) }}
                      >
                        {ACTION_CTA_LABEL[action.action_type] ?? "Review"}
                      </Link>
                    </div>
                  </div>
                ))}
                {actions && actions.length > 4 && (
                  <Link
                    href="/ai-actions"
                    className="text-[12.5px] font-semibold"
                    style={{ color: "var(--neuron-primary-dark)" }}
                  >
                    +{actions.length - 4} more — view all →
                  </Link>
                )}
              </div>
            </div>

            <div className="mt-8">
              <Link
                href="/customers"
                className="text-[13px] font-semibold"
                style={{ color: "var(--neuron-primary-dark)" }}
              >
                View all customers →
              </Link>
            </div>
          </>
        )}
      </div>
    </Shell>
  );
}
