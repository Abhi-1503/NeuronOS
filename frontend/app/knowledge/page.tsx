"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { File, FileSpreadsheet, FileText, Mail, Presentation } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Shell } from "@/components/shared/shell";
import { TabBar } from "@/components/shared/tab-bar";
import { getStoredAuth, type AuthResult } from "@/lib/auth";
import {
  confirmLink,
  getReviewQueue,
  listDocuments,
  rejectLink,
  searchDocuments,
  uploadDocument,
  type DocumentSearchResult,
  type NeuronDocument,
} from "@/lib/documents";
import { ApiError } from "@/lib/api-client";

const TABS = ["Documents", "Review Queue"] as const;

const FILE_TYPE_LABEL: Record<string, string> = {
  pdf: "PDF",
  docx: "Word",
  pptx: "Slides",
  xlsx: "Excel",
  email: "Email",
  other: "File",
};

const FILE_TYPE_ICON: Record<string, typeof File> = {
  pdf: FileText,
  docx: FileText,
  pptx: Presentation,
  xlsx: FileSpreadsheet,
  email: Mail,
  other: File,
};

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="neuron-hover-lift rounded-2xl p-4"
      style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)", boxShadow: "var(--neuron-shadow)" }}
    >
      <div className="text-[11px] font-semibold" style={{ color: "var(--neuron-text-faint)" }}>
        {label}
      </div>
      <div className="mt-1 text-[20px] font-bold">{value}</div>
    </div>
  );
}

function formatBytes(bytes: number | null): string {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function DocumentCard({ doc, onOpen }: { doc: NeuronDocument | DocumentSearchResult; onOpen: () => void }) {
  const summary = "excerpt" in doc ? doc.excerpt : doc.ai_summary;
  const Icon = FILE_TYPE_ICON[doc.file_type] ?? File;
  return (
    <button
      onClick={onOpen}
      className="neuron-hover-lift flex w-full items-start gap-3 rounded-xl p-4 text-left"
      style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)" }}
    >
      <div
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
        style={{ background: "var(--neuron-primary-tint)", color: "var(--neuron-primary-dark)" }}
      >
        <Icon size={17} strokeWidth={2} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex w-full items-center justify-between gap-2">
          <span className="truncate text-[13.5px] font-bold">{doc.title}</span>
          <span
            className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase"
            style={{ background: "var(--neuron-border)", color: "var(--neuron-text-dim)" }}
          >
            {FILE_TYPE_LABEL[doc.file_type] ?? doc.file_type}
          </span>
        </div>
        {summary && (
          <p className="mt-0.5 line-clamp-2 text-[12.5px]" style={{ color: "var(--neuron-text-faint)" }}>
            {summary}
          </p>
        )}
        {"size_bytes" in doc && doc.size_bytes && (
          <span className="mt-0.5 block text-[11px]" style={{ color: "var(--neuron-text-faint)" }}>
            {formatBytes(doc.size_bytes)}
          </span>
        )}
      </div>
    </button>
  );
}

function UploadForm({ token }: { token: string }) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingDuplicate, setPendingDuplicate] = useState<File | null>(null);

  const uploadMutation = useMutation({
    mutationFn: (input: { file: File; force?: boolean }) => uploadDocument(input, token),
    onSuccess: () => {
      setError(null);
      setPendingDuplicate(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["review-queue"] });
    },
    onError: (err: unknown, variables) => {
      if (err instanceof ApiError && err.code === "duplicate_content") {
        setPendingDuplicate(variables.file);
        setError(err.message);
      } else {
        setError(err instanceof Error ? err.message : "Upload failed.");
      }
    },
  });

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setPendingDuplicate(null);
    uploadMutation.mutate({ file });
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <input ref={fileInputRef} type="file" onChange={handleFileChange} className="text-[12.5px]" />
        {uploadMutation.isPending && (
          <span className="text-[12px]" style={{ color: "var(--neuron-text-faint)" }}>
            Uploading…
          </span>
        )}
      </div>
      {error && (
        <div className="flex items-center gap-2 text-[12px]" style={{ color: "var(--neuron-red)" }}>
          <span>{error}</span>
          {pendingDuplicate && (
            <button
              className="font-semibold underline"
              onClick={() => uploadMutation.mutate({ file: pendingDuplicate, force: true })}
            >
              Upload anyway
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function ReviewQueueTab({ token }: { token: string }) {
  const queryClient = useQueryClient();
  const { data: links, isLoading } = useQuery({
    queryKey: ["review-queue"],
    queryFn: () => getReviewQueue(token),
  });

  const confirmMutation = useMutation({
    mutationFn: (linkId: string) => confirmLink(linkId, token),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["review-queue"] }),
  });

  const rejectMutation = useMutation({
    mutationFn: (linkId: string) => rejectLink(linkId, token),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["review-queue"] }),
  });

  if (isLoading) {
    return (
      <p className="text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
        Loading…
      </p>
    );
  }

  if (!links || links.length === 0) {
    return (
      <p className="text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
        Nothing waiting on review — every AI-suggested link has already been confirmed, rejected,
        or was confident enough to skip this queue.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {links.map((link) => (
        <div
          key={link.id}
          className="neuron-hover-lift flex items-center justify-between rounded-xl p-4"
          style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)" }}
        >
          <div>
            <div className="text-[13px] font-semibold">
              Document mentions a {link.target_type} — {link.relationship ?? "related"}
            </div>
            <div className="mt-1 text-[11.5px]" style={{ color: "var(--neuron-text-faint)" }}>
              Confidence {link.confidence !== null ? `${Math.round(link.confidence * 100)}%` : "n/a"} · AI
              suggested, not yet confirmed
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => rejectMutation.mutate(link.id)}
              disabled={rejectMutation.isPending}
              className="rounded-lg px-3 py-1.5 text-[12px] font-semibold"
              style={{ background: "var(--neuron-border)", color: "var(--neuron-text-dim)" }}
            >
              Reject
            </button>
            <button
              onClick={() => confirmMutation.mutate(link.id)}
              disabled={confirmMutation.isPending}
              className="rounded-lg px-3 py-1.5 text-[12px] font-bold text-white"
              style={{ background: "var(--neuron-primary)" }}
            >
              Confirm
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function KnowledgePage() {
  const router = useRouter();
  const [auth, setAuth] = useState<AuthResult | null>(null);
  const [tab, setTab] = useState<(typeof TABS)[number]>("Documents");
  const [query, setQuery] = useState("");

  useEffect(() => {
    const stored = getStoredAuth();
    if (!stored) {
      router.replace("/login");
      return;
    }
    setAuth(stored);
  }, [router]);

  const { data: documents, isLoading: documentsLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => listDocuments(auth!.token),
    enabled: !!auth,
  });

  const { data: searchResults, isLoading: searchLoading } = useQuery({
    queryKey: ["documents-search", query],
    queryFn: () => searchDocuments(query, auth!.token),
    enabled: !!auth && query.trim().length > 0,
  });

  if (!auth) return null;

  const isSearching = query.trim().length > 0;
  const items = isSearching ? searchResults : documents;
  const isLoading = isSearching ? searchLoading : documentsLoading;

  return (
    <Shell organizationName={auth.organization.name} userName={auth.user.name} token={auth.token}>
      <div className="mx-auto max-w-2xl">
        <h1 className="text-[22px] font-bold tracking-tight">Knowledge</h1>
        <p className="mt-1 text-[13px]" style={{ color: "var(--neuron-text-dim)" }}>
          Upload contracts, proposals, and notes — NeuronOS extracts text, summarizes, and
          suggests links to the customers they mention.
        </p>

        <div
          className="relative mt-5 overflow-hidden rounded-2xl p-6"
          style={{ background: "linear-gradient(135deg,#F6F3FF,#EEF4FF)", border: "1px solid #E4DDFB" }}
        >
          <div
            className="pointer-events-none absolute -top-10 -right-10 h-40 w-40 rounded-full opacity-40"
            style={{ background: "linear-gradient(135deg,#8B7CF6,#5A48D8)" }}
          />
          <h2 className="relative text-[16px] font-bold" style={{ color: "var(--neuron-primary-dark)" }}>
            Your Knowledge Hub
          </h2>
          <p className="relative mt-1 max-w-md text-[12.5px]" style={{ color: "#4B4D63" }}>
            NeuronOS automatically organizes your knowledge and can answer anything about your
            business.
          </p>
          <div
            className="relative mt-4 flex max-w-md items-center gap-2 rounded-xl px-3 py-2"
            style={{ background: "#fff", border: "1px solid var(--neuron-border)" }}
          >
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask anything about your knowledge…"
              className="flex-1 bg-transparent text-[13px] outline-none"
            />
          </div>
        </div>

        {documents && documents.length > 0 && (
          <div className="mt-5 grid grid-cols-4 gap-3">
            <StatTile label="Total Documents" value={String(documents.length)} />
            <StatTile
              label="PDFs"
              value={String(documents.filter((d) => d.file_type === "pdf").length)}
            />
            <StatTile
              label="Word Docs"
              value={String(documents.filter((d) => d.file_type === "docx").length)}
            />
            <StatTile
              label="Other"
              value={String(documents.filter((d) => !["pdf", "docx"].includes(d.file_type)).length)}
            />
          </div>
        )}

        <div className="mt-5">
          <UploadForm token={auth.token} />
        </div>

        <div className="mt-6">
          <TabBar tabs={TABS} active={tab} onChange={setTab} layoutId="knowledge-tab" />
        </div>

        <div className="mt-4">
          {tab === "Documents" ? (
            <>
              <div className="flex flex-col gap-2">
                {isLoading && (
                  <p className="text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
                    Loading…
                  </p>
                )}
                {items?.length === 0 && (
                  <p className="text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
                    {isSearching ? "No documents match that search." : "No documents yet — upload one above."}
                  </p>
                )}
                {items?.map((doc, i) => (
                  <motion.div
                    key={doc.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: Math.min(i, 8) * 0.04 }}
                  >
                    <DocumentCard doc={doc} onOpen={() => router.push(`/knowledge/${doc.id}`)} />
                  </motion.div>
                ))}
              </div>
            </>
          ) : (
            <ReviewQueueTab token={auth.token} />
          )}
        </div>
      </div>
    </Shell>
  );
}
