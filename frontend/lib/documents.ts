import { ApiError, apiFetch } from "@/lib/api-client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export type NeuronDocument = {
  id: string;
  title: string;
  file_type: string;
  size_bytes: number | null;
  ai_summary: string | null;
  visibility: string;
  source: string;
  tags: string[];
  created_at: string;
  updated_at: string;
};

export type DocumentSearchResult = {
  id: string;
  title: string;
  file_type: string;
  excerpt: string;
};

export type LinkedEntity = {
  id: string;
  source_type: string;
  source_id: string;
  target_type: string;
  target_id: string;
  relationship: string | null;
  confidence: number | null;
  status: "ai_suggested" | "confirmed" | "rejected" | "manual";
};

export function listDocuments(token: string, limit = 25): Promise<NeuronDocument[]> {
  return apiFetch<NeuronDocument[]>(`/documents?limit=${limit}`, { token });
}

export function searchDocuments(q: string, token: string): Promise<DocumentSearchResult[]> {
  return apiFetch<DocumentSearchResult[]>(`/documents/search?q=${encodeURIComponent(q)}`, { token });
}

export function getDocument(documentId: string, token: string): Promise<NeuronDocument> {
  return apiFetch<NeuronDocument>(`/documents/${documentId}`, { token });
}

export function deleteDocument(documentId: string, token: string): Promise<void> {
  return apiFetch<void>(`/documents/${documentId}`, { method: "DELETE", token });
}

export function getReviewQueue(token: string): Promise<LinkedEntity[]> {
  return apiFetch<LinkedEntity[]>("/linked-entities/review-queue", { token });
}

export function confirmLink(linkId: string, token: string): Promise<LinkedEntity> {
  return apiFetch<LinkedEntity>(`/linked-entities/${linkId}/confirm`, { method: "POST", token });
}

export function rejectLink(linkId: string, token: string): Promise<LinkedEntity> {
  return apiFetch<LinkedEntity>(`/linked-entities/${linkId}/reject`, { method: "POST", body: {}, token });
}

type Envelope<T> = { data: T; meta: { request_id: string | null } };
type ErrorEnvelope = { error: { code: string; message: string }; meta: { request_id: string | null } };

/**
 * Multipart upload can't go through `apiFetch` — that helper always JSON-encodes the body
 * and sets `Content-Type: application/json`, which would break the file part of the form.
 */
export async function uploadDocument(
  input: { file: File; title?: string; visibility?: string; force?: boolean },
  token: string,
): Promise<{ document_id: string; status: string }> {
  const form = new FormData();
  form.append("file", input.file);
  if (input.title) form.append("title", input.title);
  if (input.visibility) form.append("visibility", input.visibility);
  if (input.force) form.append("force", "true");

  const response = await fetch(`${API_BASE_URL}/documents`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });

  const body = (await response.json()) as Envelope<{ document_id: string; status: string }> | ErrorEnvelope;

  if (!response.ok || "error" in body) {
    const err = (body as ErrorEnvelope).error;
    throw new ApiError(err?.code ?? "internal_error", err?.message ?? "Upload failed", response.status);
  }

  return (body as Envelope<{ document_id: string; status: string }>).data;
}
