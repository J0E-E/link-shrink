/*
 * Expiry choices for the shorten form, mapped to the API's `ttl_seconds` (the API clamps
 * to 1 hour–30 days). Kept in their own module so the component files only export
 * components (keeps React Fast Refresh happy).
 */

export const EXPIRY_OPTIONS: ReadonlyArray<{ label: string; seconds: number }> = [
  { label: "1 hour", seconds: 3600 },
  { label: "1 day", seconds: 86400 },
  { label: "7 days", seconds: 604800 },
  { label: "30 days", seconds: 2592000 },
];

/** The default expiry (30 days) — matches the API default when `ttl_seconds` is omitted. */
export const DEFAULT_EXPIRY_SECONDS = 2592000;
