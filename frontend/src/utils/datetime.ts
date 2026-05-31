/**
 * Shared date/time formatters for the result card, dashboard cards, and analytics view.
 * Keeps timestamp display in one place so the whole app reads dates the same way.
 */

/** Format an ISO timestamp as a readable local date and time, e.g. "30 Jun 2026, 14:30". */
export function formatDateTime(isoTimestamp: string): string {
  const date = new Date(isoTimestamp);
  if (Number.isNaN(date.getTime())) {
    return isoTimestamp;
  }
  return date.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Format an ISO date (no time) as a readable local date, e.g. "30 Jun 2026". */
export function formatDate(isoTimestamp: string): string {
  const date = new Date(isoTimestamp);
  if (Number.isNaN(date.getTime())) {
    return isoTimestamp;
  }
  return date.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

const SECOND_IN_MILLISECONDS = 1000;
const MINUTE_IN_SECONDS = 60;
const HOUR_IN_SECONDS = 60 * MINUTE_IN_SECONDS;
const DAY_IN_SECONDS = 24 * HOUR_IN_SECONDS;

/**
 * Format an ISO timestamp relative to now, e.g. "2d ago" for the past or "in 28d" for the
 * future. Falls back to coarser units the further out it is, and to a calendar date past a
 * year so the phrasing stays short.
 */
export function formatRelative(isoTimestamp: string, now: Date = new Date()): string {
  const date = new Date(isoTimestamp);
  if (Number.isNaN(date.getTime())) {
    return isoTimestamp;
  }

  const differenceInSeconds = Math.round((date.getTime() - now.getTime()) / SECOND_IN_MILLISECONDS);
  const isFuture = differenceInSeconds > 0;
  const absoluteSeconds = Math.abs(differenceInSeconds);

  const phrase = describeSpan(absoluteSeconds);
  if (phrase === null) {
    return formatDate(isoTimestamp);
  }
  return isFuture ? `in ${phrase}` : `${phrase} ago`;
}

/** Return a short magnitude phrase like "2d" or "5h", or null when older than a year. */
function describeSpan(absoluteSeconds: number): string | null {
  if (absoluteSeconds < MINUTE_IN_SECONDS) {
    return `${absoluteSeconds}s`;
  }
  if (absoluteSeconds < HOUR_IN_SECONDS) {
    return `${Math.round(absoluteSeconds / MINUTE_IN_SECONDS)}m`;
  }
  if (absoluteSeconds < DAY_IN_SECONDS) {
    return `${Math.round(absoluteSeconds / HOUR_IN_SECONDS)}h`;
  }
  const days = Math.round(absoluteSeconds / DAY_IN_SECONDS);
  if (days <= 365) {
    return `${days}d`;
  }
  return null;
}
