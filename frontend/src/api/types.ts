/*
 * TypeScript mirror of the API's wire contract (`services/api/.../schemas.py`).
 * Datetimes and dates arrive as ISO-8601 strings over JSON, so they are typed as
 * `string` here. Keep these in sync with the Pydantic models if the contract changes.
 */

export type QrFormat = "png" | "svg";

/** Body for `POST /api/links`. Only `url` is required. */
export interface CreateLinkRequest {
  url: string;
  alias?: string | null;
  ttl_seconds?: number | null;
}

/** 201 body for a created link. */
export interface CreateLinkResponse {
  short_code: string;
  short_url: string;
  original_url: string;
  created_at: string;
  expires_at: string;
  qr_url: string;
}

/** Read-side view shared by the listing and detail endpoints. */
export interface LinkView {
  short_code: string;
  short_url: string;
  original_url: string;
  created_at: string;
  expires_at: string;
  qr_url: string;
  is_custom: boolean;
}

/** 200 body for `GET /api/links` — a page of links plus the next cursor. */
export interface ListLinksResponse {
  items: LinkView[];
  next_cursor: string | null;
}

/** One UTC day in the clicks-over-time series. */
export interface DailyClickBucket {
  day: string;
  count: number;
}

/** One row of a breakdown — a dimension value and its click count. */
export interface BreakdownItem {
  value: string;
  count: number;
}

/** 200 body for `GET /api/links/{code}/analytics`. */
export interface LinkAnalyticsResponse {
  short_code: string;
  total_clicks: number;
  daily: DailyClickBucket[];
  by_device_type: BreakdownItem[];
  by_browser_family: BreakdownItem[];
  by_os_family: BreakdownItem[];
  by_referrer_domain: BreakdownItem[];
  by_source: BreakdownItem[];
}

/** 200 body for `GET /api/metrics`. */
export interface MetricsResponse {
  cache_hits: number;
  cache_misses: number;
  cache_hit_ratio: number;
  total_redirects: number;
  average_redirect_latency_ms: number | null;
  queue_pending: number;
  queue_stream_length: number;
  worker_healthy: boolean;
  worker_heartbeat_age_seconds: number | null;
}

/**
 * Error envelope. FastAPI wraps the structured error under `detail`, so a failed
 * request's JSON looks like `{ "detail": { "reason": ..., "message": ... } }`.
 */
export interface ApiErrorDetail {
  reason: string;
  message: string;
}

export interface ApiErrorBody {
  detail: ApiErrorDetail;
}
