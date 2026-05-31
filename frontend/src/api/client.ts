/*
 * Typed client for the LinkShrink API. Every call uses a relative `/api/...` path:
 * in production Nginx serves the SPA and the API on the same origin, and in
 * development the Vite dev server proxies `/api` to the local API (see vite.config.ts).
 *
 * Failed requests throw an `ApiError` carrying the HTTP status plus the `reason` and
 * `message` the API returns under `detail`, so callers (Epics 15/16) can branch on the
 * symbolic reason rather than matching message strings.
 */

import type {
  ApiErrorBody,
  CreateLinkRequest,
  CreateLinkResponse,
  LinkAnalyticsResponse,
  LinkView,
  ListLinksResponse,
  MetricsResponse,
  QrFormat,
} from "./types";

const API_BASE_PATH = "/api";

/** An error raised for any non-2xx API response. */
export class ApiError extends Error {
  readonly status: number;
  readonly reason: string;

  constructor(status: number, reason: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.reason = reason;
  }
}

function isErrorBody(body: unknown): body is ApiErrorBody {
  return (
    typeof body === "object" &&
    body !== null &&
    "detail" in body &&
    typeof (body as ApiErrorBody).detail === "object" &&
    (body as ApiErrorBody).detail !== null
  );
}

async function buildApiError(response: Response): Promise<ApiError> {
  let reason = "unknown_error";
  let message = `request failed with status ${response.status}`;
  try {
    const body: unknown = await response.json();
    if (isErrorBody(body)) {
      reason = body.detail.reason ?? reason;
      message = body.detail.message ?? message;
    }
  } catch {
    // Non-JSON or empty error body — keep the status-based defaults above.
  }
  return new ApiError(response.status, reason, message);
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
}

async function request<TResponse>(path: string, options: RequestOptions = {}): Promise<TResponse> {
  const { method = "GET", body, signal } = options;
  const response = await fetch(`${API_BASE_PATH}${path}`, {
    method,
    signal,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    throw await buildApiError(response);
  }
  return (await response.json()) as TResponse;
}

/** Create a short link (`POST /api/links`). */
export function createLink(
  payload: CreateLinkRequest,
  signal?: AbortSignal,
): Promise<CreateLinkResponse> {
  return request<CreateLinkResponse>("/links", { method: "POST", body: payload, signal });
}

/** List links newest-first with keyset paging (`GET /api/links`). */
export function listLinks(cursor?: string | null, limit?: number, signal?: AbortSignal) {
  const query = new URLSearchParams();
  if (cursor) {
    query.set("cursor", cursor);
  }
  if (limit !== undefined) {
    query.set("limit", String(limit));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<ListLinksResponse>(`/links${suffix}`, { signal });
}

/** Fetch a single link's detail (`GET /api/links/{code}`). */
export function getLink(shortCode: string, signal?: AbortSignal): Promise<LinkView> {
  return request<LinkView>(`/links/${encodeURIComponent(shortCode)}`, { signal });
}

/** Fetch a link's aggregated analytics (`GET /api/links/{code}/analytics`). */
export function getLinkAnalytics(
  shortCode: string,
  signal?: AbortSignal,
): Promise<LinkAnalyticsResponse> {
  return request<LinkAnalyticsResponse>(
    `/links/${encodeURIComponent(shortCode)}/analytics`,
    { signal },
  );
}

/** Fetch live operational metrics (`GET /api/metrics`). */
export function getMetrics(signal?: AbortSignal): Promise<MetricsResponse> {
  return request<MetricsResponse>("/metrics", { signal });
}

/**
 * Build the URL of a link's QR image (`GET /api/links/{code}/qr`). The QR endpoint
 * returns an image, not JSON, so this is a plain URL for use in `src`/download links
 * rather than a fetch call.
 */
export function buildQrUrl(shortCode: string, format: QrFormat = "png"): string {
  return `${API_BASE_PATH}/links/${encodeURIComponent(shortCode)}/qr?format=${format}`;
}
