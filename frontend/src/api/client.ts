export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000';

/** Thrown for any non-2xx response. `detail` is the backend's own message
 * (FastAPI's {"detail": "..."} shape) when present — callers should show
 * that verbatim rather than inventing their own wording, so the UI never
 * says more than the API already chose to reveal (e.g. auth errors are
 * deliberately identical for "wrong password" and "unknown email").
 */
export class ApiError extends Error {
  status: number;
  detail: string | null;

  constructor(status: number, detail: string | null) {
    super(detail ?? `Request failed with status ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

/** Thrown when the request never reached the server at all (network down,
 * backend not running, CORS misconfiguration). Distinct from ApiError so
 * the UI can tell "the server said no" apart from "there is no server".
 */
export class NetworkError extends Error {
  constructor() {
    super('Unable to reach the server.');
    this.name = 'NetworkError';
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
  query?: Record<string, string | number | undefined>;
}

function buildUrl(path: string, query?: RequestOptions['query']): string {
  const url = new URL(path, API_BASE_URL);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

/** All requests send credentials: 'include' so the httpOnly session
 * cookie rides along — this app never reads, stores, or attaches a token
 * itself. That's the whole point of an httpOnly cookie: the frontend
 * can't touch it even if it wanted to.
 */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.query), {
      method: options.method ?? 'GET',
      credentials: 'include',
      headers: options.body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new NetworkError();
  }

  if (!response.ok) {
    let detail: string | null = null;
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail ?? null;
    } catch {
      // Non-JSON error body (e.g. a proxy error page) — no detail to surface.
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
