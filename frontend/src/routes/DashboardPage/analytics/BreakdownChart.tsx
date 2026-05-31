import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { BreakdownItem } from "../../../api/types";
import { CHART_COLORS } from "../chartTheme";
import styles from "./BreakdownChart.module.css";

interface BreakdownChartProps {
  /** Unique id stem for this breakdown's elements, e.g. "device-type". */
  breakdownId: string;
  title: string;
  items: BreakdownItem[];
}

const ROW_HEIGHT_PIXELS = 32;
const MINIMUM_PLOT_HEIGHT_PIXELS = 64;

/**
 * A horizontal bar chart for one analytics breakdown dimension (device type, browser, OS,
 * referrer domain, or source). Bars are ordered most-clicks-first by the API; an empty
 * dimension shows a short fallback instead of an empty plot.
 */
export default function BreakdownChart({ breakdownId, title, items }: BreakdownChartProps) {
  const sectionId = `analytics-breakdown-${breakdownId}`;
  const plotHeight = Math.max(MINIMUM_PLOT_HEIGHT_PIXELS, items.length * ROW_HEIGHT_PIXELS);

  return (
    <section
      className={styles.card}
      id={sectionId}
      aria-labelledby={`${sectionId}-title`}
    >
      <h3 className={styles.title} id={`${sectionId}-title`}>
        {title}
      </h3>
      {items.length === 0 ? (
        <p className={styles.empty} id={`${sectionId}-empty`}>
          No data yet.
        </p>
      ) : (
        <div className={styles.plot} id={`${sectionId}-plot`}>
          <ResponsiveContainer width="100%" height={plotHeight}>
            <BarChart
              data={items}
              layout="vertical"
              margin={{ top: 0, right: 16, bottom: 0, left: 8 }}
            >
              <XAxis type="number" hide allowDecimals={false} />
              <YAxis
                type="category"
                dataKey="value"
                width={110}
                stroke={CHART_COLORS.grid}
                tick={{ fill: CHART_COLORS.axisText, fontSize: 12 }}
              />
              <Tooltip
                cursor={{ fill: "rgba(34, 197, 94, 0.12)" }}
                contentStyle={{
                  backgroundColor: CHART_COLORS.tooltipBackground,
                  border: `1px solid ${CHART_COLORS.tooltipBorder}`,
                  borderRadius: 10,
                  color: "#ffffff",
                }}
              />
              <Bar
                dataKey="count"
                name="Clicks"
                fill={CHART_COLORS.success}
                radius={[0, 4, 4, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
