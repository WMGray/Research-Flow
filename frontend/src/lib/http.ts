export type APIEnvelope<T> = {
  data: T;
  meta: Record<string, unknown>;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  } | null;
};

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export type RequestOptions = {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
};

export class APIError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(message: string, status: number, code: string) {
    super(message);
    this.name = "APIError";
    this.status = status;
    this.code = code;
  }
}

export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<APIEnvelope<T>> {
  const headers = new Headers();
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    cache: "no-store",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = payload?.detail ?? payload?.error;
    const code = detail?.code ?? `HTTP_${response.status}`;
    const message = detail?.message ?? response.statusText ?? "Request failed.";
    throw new APIError(message, response.status, code);
  }

  return payload as APIEnvelope<T>;
}
