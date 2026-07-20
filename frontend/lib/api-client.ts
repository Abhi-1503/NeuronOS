const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

type Envelope<T> = { data: T; meta: { request_id: string | null } };
type ErrorEnvelope = { error: { code: string; message: string }; meta: { request_id: string | null } };

/**
 * Thin wrapper around the standard request/response envelope (API Spec §0.2/§0.3) —
 * every caller gets back the unwrapped `data`, or an `ApiError` carrying the server's
 * `error.code`/`message` rather than a generic HTTP failure.
 */
export async function apiFetch<T>(
  path: string,
  options: { method?: string; body?: unknown; token?: string; idempotencyKey?: string } = {},
): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (options.token) headers.Authorization = `Bearer ${options.token}`;
  if (options.idempotencyKey) headers["Idempotency-Key"] = options.idempotencyKey;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (response.status === 204) return undefined as T;

  const body = (await response.json()) as Envelope<T> | ErrorEnvelope;

  if (!response.ok || "error" in body) {
    const err = (body as ErrorEnvelope).error;
    throw new ApiError(err?.code ?? "internal_error", err?.message ?? "Request failed", response.status);
  }

  return (body as Envelope<T>).data;
}
