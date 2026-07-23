"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Shell } from "@/components/shared/shell";
import { getStoredAuth, type AuthResult } from "@/lib/auth";
import { deleteDocument, getDocument } from "@/lib/documents";

const FILE_TYPE_LABEL: Record<string, string> = {
  pdf: "PDF",
  docx: "Word document",
  pptx: "Slides",
  xlsx: "Spreadsheet",
  email: "Email",
  other: "File",
};

function formatBytes(bytes: number | null): string {
  if (!bytes) return "Unknown size";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [auth, setAuth] = useState<AuthResult | null>(null);

  useEffect(() => {
    const stored = getStoredAuth();
    if (!stored) {
      router.replace("/login");
      return;
    }
    setAuth(stored);
  }, [router]);

  const { data: doc, isLoading } = useQuery({
    queryKey: ["document", params.id],
    queryFn: () => getDocument(params.id, auth!.token),
    enabled: !!auth,
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteDocument(params.id, auth!.token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      router.push("/knowledge");
    },
  });

  if (!auth) return null;

  return (
    <Shell organizationName={auth.organization.name} userName={auth.user.name} token={auth.token}>
      <div className="mx-auto max-w-2xl">
        <button
          onClick={() => router.push("/knowledge")}
          className="text-[12.5px] font-medium"
          style={{ color: "var(--neuron-text-faint)" }}
        >
          ← Back to Knowledge
        </button>

        {isLoading && (
          <p className="mt-4 text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
            Loading…
          </p>
        )}

        {doc && (
          <>
            <div className="mt-3 flex items-start justify-between">
              <div>
                <h1 className="text-[20px] font-bold tracking-tight">{doc.title}</h1>
                <div className="mt-1 flex items-center gap-2 text-[12.5px]" style={{ color: "var(--neuron-text-faint)" }}>
                  <span>{FILE_TYPE_LABEL[doc.file_type] ?? doc.file_type}</span>
                  <span>·</span>
                  <span>{formatBytes(doc.size_bytes)}</span>
                  <span>·</span>
                  <span>Uploaded {new Date(doc.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <button
                onClick={() => {
                  if (confirm(`Delete "${doc.title}"? This can't be undone from the UI.`)) {
                    deleteMutation.mutate();
                  }
                }}
                disabled={deleteMutation.isPending}
                className="rounded-lg px-3 py-1.5 text-[12px] font-semibold"
                style={{ background: "var(--neuron-red-tint)", color: "var(--neuron-red)" }}
              >
                Delete
              </button>
            </div>

            <div
              className="mt-5 rounded-xl p-4"
              style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)" }}
            >
              <div className="text-[11px] font-bold uppercase tracking-wide" style={{ color: "var(--neuron-text-faint)" }}>
                AI Summary
              </div>
              <p className="mt-2 text-[13.5px] leading-relaxed">
                {doc.ai_summary ?? "No summary available — no extractable text was found in this file."}
              </p>
            </div>

            {doc.tags.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {doc.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full px-2.5 py-1 text-[11.5px] font-semibold"
                    style={{ background: "var(--neuron-border)", color: "var(--neuron-text-dim)" }}
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </Shell>
  );
}
