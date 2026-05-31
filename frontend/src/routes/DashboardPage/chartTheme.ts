/**
 * Palette constants for the analytics charts. recharts takes colors as inline `fill`/
 * `stroke` props and cannot read CSS custom properties, so these mirror the matching
 * tokens in `src/styles/tokens.css` (kept in sync by hand). Dark-theme only.
 */
export const CHART_COLORS = {
  /** Primary accent (purple) — the daily clicks series. */
  accent: "#a855f7",
  /** Success accent (green) — breakdown bars / highlights. */
  success: "#22c55e",
  /** Grid lines and axes — matches `--color-border`. */
  grid: "#2e3445",
  /** Axis tick / label text — matches `--color-text-secondary`. */
  axisText: "#b4bac8",
  /** Tooltip background — matches `--color-surface-raised`. */
  tooltipBackground: "#262b3b",
  /** Tooltip border — matches `--color-border`. */
  tooltipBorder: "#2e3445",
} as const;
