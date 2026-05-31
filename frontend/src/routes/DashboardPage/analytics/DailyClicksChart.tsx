import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { DailyClickBucket } from "../../../api/types";
import { CHART_COLORS } from "../chartTheme";
import { fillDailyGaps } from "./fillDailyGaps";
import styles from "./DailyClicksChart.module.css";

interface DailyClicksChartProps {
  daily: DailyClickBucket[];
}

/** Render a UTC day (`2026-06-30`) as a short axis label, e.g. "30 Jun". */
function formatDayTick(day: string): string {
  const date = new Date(`${day}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) {
    return day;
  }
  return date.toLocaleDateString(undefined, { day: "numeric", month: "short", timeZone: "UTC" });
}

/**
 * Clicks-per-day bar chart. The API series is sparse (only days with clicks), so the gaps
 * are filled with zero-count days first for a continuous timeline.
 */
export default function DailyClicksChart({ daily }: DailyClicksChartProps) {
  const series = fillDailyGaps(daily);

  return (
    <section
      className={styles.chartCard}
      id="analytics-daily-chart"
      aria-labelledby="analytics-daily-chart-title"
    >
      <h2 className={styles.title} id="analytics-daily-chart-title">
        Clicks over time
      </h2>
      {series.length === 0 ? (
        <p className={styles.empty} id="analytics-daily-chart-empty">
          No clicks recorded yet.
        </p>
      ) : (
        <div className={styles.plot} id="analytics-daily-chart-plot">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={series} margin={{ top: 8, right: 8, bottom: 8, left: -16 }}>
              <CartesianGrid stroke={CHART_COLORS.grid} vertical={false} />
              <XAxis
                dataKey="day"
                tickFormatter={formatDayTick}
                stroke={CHART_COLORS.grid}
                tick={{ fill: CHART_COLORS.axisText, fontSize: 12 }}
                minTickGap={16}
              />
              <YAxis
                allowDecimals={false}
                stroke={CHART_COLORS.grid}
                tick={{ fill: CHART_COLORS.axisText, fontSize: 12 }}
              />
              <Tooltip
                cursor={{ fill: "rgba(168, 85, 247, 0.12)" }}
                labelFormatter={(label: string) => formatDayTick(label)}
                contentStyle={{
                  backgroundColor: CHART_COLORS.tooltipBackground,
                  border: `1px solid ${CHART_COLORS.tooltipBorder}`,
                  borderRadius: 10,
                  color: "#ffffff",
                }}
              />
              <Bar dataKey="count" name="Clicks" fill={CHART_COLORS.accent} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
