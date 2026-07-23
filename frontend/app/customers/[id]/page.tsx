"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Calendar, FileSignature, FileText, Mail, Receipt, StickyNote } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Avatar } from "@/components/shared/avatar";
import { Shell } from "@/components/shared/shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getStoredAuth, type AuthResult } from "@/lib/auth";
import {
  addTimelineEvent,
  getCustomer,
  getCustomerTimeline,
  type TimelineEvent,
} from "@/lib/customers";

const EVENT_ICON: Record<string, typeof Mail> = {
  meeting: Calendar,
  email: Mail,
  proposal: FileText,
  invoice: Receipt,
  contract: FileSignature,
  note: StickyNote,
};

export default function CustomerDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [auth, setAuth] = useState<AuthResult | null>(null);
  const [noteTitle, setNoteTitle] = useState("");

  useEffect(() => {
    const stored = getStoredAuth();
    if (!stored) {
      router.replace("/login");
      return;
    }
    setAuth(stored);
  }, [router]);

  const { data: customer } = useQuery({
    queryKey: ["customer", params.id],
    queryFn: () => getCustomer(params.id, auth!.token),
    enabled: !!auth,
  });

  const { data: timeline } = useQuery({
    queryKey: ["customer-timeline", params.id],
    queryFn: () => getCustomerTimeline(params.id, auth!.token),
    enabled: !!auth,
  });

  const addNoteMutation = useMutation({
    mutationFn: () =>
      addTimelineEvent(params.id, { event_type: "note", title: noteTitle }, auth!.token),
    onSuccess: () => {
      setNoteTitle("");
      queryClient.invalidateQueries({ queryKey: ["customer-timeline", params.id] });
      queryClient.invalidateQueries({ queryKey: ["customer", params.id] });
    },
  });

  if (!auth || !customer) return null;

  const action = customer.recommended_next_action;

  return (
    <Shell
      organizationName={auth.organization.name}
      userName={auth.user.name}
      token={auth.token}
      rightRail={
        <div className="flex flex-col gap-4">
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wide" style={{ color: "var(--neuron-text-faint)" }}>
              Relationship Score
            </div>
            <div className="mt-1 text-[28px] font-bold">{customer.relationship_score ?? "—"}</div>
          </div>

          {action && (
            <div
              className="rounded-xl p-4"
              style={{
                background:
                  action.severity_tier === "high" ? "var(--neuron-red-tint)" : "var(--neuron-primary-tint)",
                border:
                  action.severity_tier === "high"
                    ? "1px solid #F3C6C6"
                    : "1px solid var(--neuron-border)",
              }}
            >
              <div className="text-[12.5px] font-bold" style={{ color: "var(--neuron-primary-dark)" }}>
                Recommended Action
              </div>
              <div className="mt-1 text-[13px] font-semibold">{action.title}</div>
              {/* Reasoning shown inline, always visible — never behind a "why?" click
                  (Blueprint §2.7, Database Spec §7.1/§3.4). */}
              {action.reasoning && (
                <div
                  className="mt-2 rounded-lg p-2 text-[12px]"
                  style={{ background: "var(--neuron-card)", color: "var(--neuron-text-dim)" }}
                >
                  {action.reasoning}
                </div>
              )}
              {action.confidence_score !== null && (
                <div className="mt-2 flex items-center gap-2 text-[11px]" style={{ color: "var(--neuron-text-faint)" }}>
                  <span>Confidence</span>
                  <div className="h-1 w-16 rounded-full" style={{ background: "var(--neuron-border)" }}>
                    <div
                      className="h-1 rounded-full"
                      style={{
                        width: `${Math.round((action.confidence_score ?? 0) * 100)}%`,
                        background: "var(--neuron-primary)",
                      }}
                    />
                  </div>
                  <span>{Math.round((action.confidence_score ?? 0) * 100)}%</span>
                </div>
              )}
              <div className="mt-3">
                <a
                  href="/ai-actions"
                  className="text-[12px] font-semibold"
                  style={{ color: "var(--neuron-primary-dark)" }}
                >
                  Review in AI Actions →
                </a>
              </div>
            </div>
          )}
        </div>
      }
    >
      <div className="mx-auto max-w-2xl">
        <div className="flex items-center gap-3">
          <Avatar name={customer.name} size={40} />
          <div>
            <h1 className="text-[22px] font-bold tracking-tight">{customer.name}</h1>
            <p className="text-[13px]" style={{ color: "var(--neuron-text-dim)" }}>
              {customer.last_contact_at
                ? `Last contact ${new Date(customer.last_contact_at).toLocaleDateString()}`
                : "No contact logged yet"}
            </p>
          </div>
        </div>

        <div className="mt-6">
          <h2 className="text-[14px] font-bold">Timeline</h2>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (noteTitle.trim()) addNoteMutation.mutate();
            }}
            className="mt-2 flex gap-2"
          >
            <Input
              value={noteTitle}
              onChange={(e) => setNoteTitle(e.target.value)}
              placeholder="Add a note…"
            />
            <Button type="submit" disabled={!noteTitle.trim() || addNoteMutation.isPending}>
              Add
            </Button>
          </form>

          <div className="mt-4 flex flex-col gap-2">
            {timeline?.length === 0 && (
              <p className="text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
                Nothing logged yet.
              </p>
            )}
            {timeline?.map((event: TimelineEvent) => {
              const Icon = EVENT_ICON[event.event_type] ?? StickyNote;
              return (
                <div
                  key={event.id}
                  className="flex items-start gap-3 rounded-lg p-3"
                  style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)" }}
                >
                  <div
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full"
                    style={{ background: "var(--neuron-primary-tint)", color: "var(--neuron-primary-dark)" }}
                  >
                    <Icon size={14} strokeWidth={2} />
                  </div>
                  <div>
                    <div className="text-[13px] font-semibold">{event.title}</div>
                    <div className="text-[11px]" style={{ color: "var(--neuron-text-faint)" }}>
                      {event.event_type} · {new Date(event.occurred_at).toLocaleString()}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </Shell>
  );
}
