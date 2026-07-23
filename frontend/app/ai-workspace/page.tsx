"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { NeuronMark } from "@/components/shared/neuron-mark";
import { Shell } from "@/components/shared/shell";
import {
  getConversation,
  listConversations,
  sendMessage,
  type ChatMessageHistory,
  type Citation,
} from "@/lib/chat";
import { getStoredAuth, type AuthResult } from "@/lib/auth";

const CITATION_LABEL: Record<Citation["type"], string> = {
  document: "Document",
  customer: "Customer",
  project: "Project",
};

function CitationChip({ citation }: { citation: Citation }) {
  return (
    <span
      className="rounded-full px-2 py-0.5 text-[10.5px] font-semibold"
      style={{ background: "var(--neuron-border)", color: "var(--neuron-text-dim)" }}
      title={citation.excerpt}
    >
      {CITATION_LABEL[citation.type]}
    </span>
  );
}

function MessageBubble({ message }: { message: ChatMessageHistory }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex items-end gap-2 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div
          className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full"
          style={{ background: "linear-gradient(135deg,#8B7CF6,#5A48D8)" }}
        >
          <NeuronMark size={13} variant="mono" color="#fff" />
        </div>
      )}
      <div
        className="max-w-[75%] rounded-2xl px-4 py-2.5 text-[13.5px] leading-relaxed"
        style={
          isUser
            ? { background: "var(--neuron-primary)", color: "white" }
            : { background: "var(--neuron-card)", border: "1px solid var(--neuron-border)" }
        }
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.citations.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {message.citations.map((c, i) => (
              <CitationChip key={`${c.type}-${c.id}-${i}`} citation={c} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function AIWorkspacePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [auth, setAuth] = useState<AuthResult | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  useEffect(() => {
    const stored = getStoredAuth();
    if (!stored) {
      router.replace("/login");
      return;
    }
    setAuth(stored);
  }, [router]);

  const { data: conversations } = useQuery({
    queryKey: ["conversations"],
    queryFn: () => listConversations(auth!.token),
    enabled: !!auth,
  });

  const { data: conversation } = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () => getConversation(conversationId!, auth!.token),
    enabled: !!auth && !!conversationId,
  });

  const sendMutation = useMutation({
    mutationFn: (message: string) =>
      sendMessage({ conversation_id: conversationId ?? undefined, message }, auth!.token),
    onSuccess: (response) => {
      setDraft("");
      setConversationId(response.conversation_id);
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      queryClient.invalidateQueries({ queryKey: ["conversation", response.conversation_id] });
    },
  });

  function handleSend() {
    const trimmed = draft.trim();
    if (!trimmed || sendMutation.isPending) return;
    sendMutation.mutate(trimmed);
  }

  if (!auth) return null;

  const messages = conversation?.messages ?? [];

  return (
    <Shell organizationName={auth.organization.name} userName={auth.user.name} token={auth.token}>
      <div className="mx-auto flex h-[calc(100vh-64px)] max-w-4xl gap-6">
        <aside className="flex w-[220px] shrink-0 flex-col gap-2">
          <button
            onClick={() => setConversationId(null)}
            className="rounded-lg px-3 py-2 text-left text-[12.5px] font-semibold text-white"
            style={{ background: "var(--neuron-primary)" }}
          >
            + New conversation
          </button>
          <div className="mt-2 flex flex-col gap-1 overflow-y-auto">
            {conversations?.map((c) => (
              <button
                key={c.id}
                onClick={() => setConversationId(c.id)}
                className="truncate rounded-md px-2.5 py-2 text-left text-[12.5px] font-medium"
                style={
                  c.id === conversationId
                    ? { background: "var(--neuron-primary-tint)", color: "var(--neuron-primary-dark)" }
                    : { color: "var(--neuron-text-dim)" }
                }
              >
                {c.title || "New conversation"}
              </button>
            ))}
            {conversations?.length === 0 && (
              <p className="px-2.5 text-[12px]" style={{ color: "var(--neuron-text-faint)" }}>
                No conversations yet.
              </p>
            )}
          </div>
        </aside>

        <div className="flex flex-1 flex-col">
          <h1 className="text-[20px] font-bold tracking-tight">AI Workspace</h1>
          <p className="mt-1 text-[12.5px]" style={{ color: "var(--neuron-text-dim)" }}>
            Ask about your customers or documents — answers cite what they&rsquo;re based on.
          </p>

          <div className="mt-4 flex flex-1 flex-col gap-3 overflow-y-auto pb-4">
            {messages.length === 0 && !sendMutation.isPending && (
              <p className="mt-8 text-center text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
                Ask a question to get started — e.g. &ldquo;What&rsquo;s the status of Acme Corp?&rdquo;
              </p>
            )}
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
            {sendMutation.isPending && (
              <div className="flex justify-start">
                <div
                  className="rounded-2xl px-4 py-2.5 text-[13px]"
                  style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)", color: "var(--neuron-text-faint)" }}
                >
                  Thinking…
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 border-t pt-3" style={{ borderColor: "var(--neuron-border)" }}>
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Ask the AI Workspace…"
              className="h-10 flex-1 rounded-lg border px-3 text-[13.5px] outline-none"
              style={{ borderColor: "var(--neuron-border)", background: "var(--neuron-card)" }}
            />
            <button
              onClick={handleSend}
              disabled={sendMutation.isPending || !draft.trim()}
              className="h-10 rounded-lg px-4 text-[13px] font-bold text-white disabled:opacity-50"
              style={{ background: "var(--neuron-primary)" }}
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </Shell>
  );
}
