import type { MetricsResponse } from "../../api/types";
import MetricStat from "./MetricStat";
import { useLiveMetrics } from "./useLiveMetrics";
import styles from "./LiveMetricsPanel.module.css";

/** Format the heartbeat age into a short hint for the worker-health stat. */
function describeWorkerHeartbeat(metrics: MetricsResponse): string {
  if (metrics.worker_heartbeat_age_seconds === null) {
    return "No heartbeat yet";
  }
  return `Heartbeat ${Math.round(metrics.worker_heartbeat_age_seconds)}s ago`;
}

/**
 * The live operational metrics panel — the only part of the How-It-Works page that is not
 * static. It reads `/api/metrics` via `useLiveMetrics` (polled every 10s) and shows the
 * cache hit ratio, redirect total, queue backlog vs volume, and worker health.
 */
export default function LiveMetricsPanel() {
  const { status, metrics, isRefreshing, errorMessage, reload } = useLiveMetrics();

  return (
    <div className={styles.panel} id="live-metrics-panel">
      <div className={styles.panelHeader} id="live-metrics-header">
        <p className={styles.caption} id="live-metrics-caption">
          Live from <code id="live-metrics-endpoint">/api/metrics</code>, refreshed every 10
          seconds. Redirect latency is measured at the proxy and is not exposed here.
        </p>
        <span className={styles.refreshStatus} id="live-metrics-refresh-status" aria-hidden="true">
          {status === "success" && isRefreshing ? "Refreshing…" : ""}
        </span>
      </div>

      {status === "loading" && (
        <p className={styles.notice} id="live-metrics-loading" role="status">
          Loading live metrics…
        </p>
      )}

      {status === "error" && (
        <div className={styles.notice} id="live-metrics-error" role="alert">
          <p className={styles.noticeText} id="live-metrics-error-text">
            {errorMessage ?? "Could not load live metrics."}
          </p>
          <button
            type="button"
            className={styles.retryButton}
            id="live-metrics-retry-button"
            onClick={reload}
          >
            Try again
          </button>
        </div>
      )}

      {status === "success" && metrics && (
        <div className={styles.grid} id="live-metrics-grid">
          <MetricStat
            id="live-metric-cache-hit-ratio"
            label="Cache hit ratio"
            value={`${(metrics.cache_hit_ratio * 100).toFixed(1)}%`}
            hint={`${metrics.cache_hits.toLocaleString()} hits / ${metrics.cache_misses.toLocaleString()} misses`}
            tone="success"
          />
          <MetricStat
            id="live-metric-total-redirects"
            label="Total redirects"
            value={metrics.total_redirects.toLocaleString()}
          />
          <MetricStat
            id="live-metric-queue-pending"
            label="Queue backlog"
            value={metrics.queue_pending.toLocaleString()}
            hint="Delivered but not yet processed"
          />
          <MetricStat
            id="live-metric-queue-stream-length"
            label="Queue volume"
            value={metrics.queue_stream_length.toLocaleString()}
            hint="Recent clicks retained in the stream"
          />
          <MetricStat
            id="live-metric-worker-health"
            label="Worker health"
            value={metrics.worker_healthy ? "Healthy" : "Stale"}
            hint={describeWorkerHeartbeat(metrics)}
            tone={metrics.worker_healthy ? "success" : "warning"}
          />
        </div>
      )}
    </div>
  );
}
