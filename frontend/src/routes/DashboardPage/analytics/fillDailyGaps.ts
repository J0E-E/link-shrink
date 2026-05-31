import type { DailyClickBucket } from "../../../api/types";

const DAY_IN_MILLISECONDS = 24 * 60 * 60 * 1000;

/**
 * The analytics API returns a sparse daily series — only UTC days that actually had clicks.
 * For a readable timeline the chart needs every day in between, so this fills the gaps
 * between the first and last day with `count: 0` buckets. An empty input stays empty, and a
 * single-day series is returned unchanged.
 */
export function fillDailyGaps(daily: DailyClickBucket[]): DailyClickBucket[] {
  if (daily.length === 0) {
    return [];
  }

  const countByDay = new Map(daily.map((bucket) => [bucket.day, bucket.count]));
  const firstDay = Date.parse(`${daily[0].day}T00:00:00Z`);
  const lastDay = Date.parse(`${daily[daily.length - 1].day}T00:00:00Z`);

  // Guard against unparseable dates — fall back to the original series rather than loop wildly.
  if (Number.isNaN(firstDay) || Number.isNaN(lastDay) || lastDay < firstDay) {
    return daily;
  }

  const filled: DailyClickBucket[] = [];
  for (let dayMillis = firstDay; dayMillis <= lastDay; dayMillis += DAY_IN_MILLISECONDS) {
    const day = new Date(dayMillis).toISOString().slice(0, 10);
    filled.push({ day, count: countByDay.get(day) ?? 0 });
  }
  return filled;
}
