import { useCallback, useEffect, useRef, useState } from "react";

import { getMetrics } from "../../api/client";
import type { MetricsResponse } from "../../api/types";

export type LiveMetricsStatus = "loading" | "success" | "error";

/** How often the panel re-fetches while it is open. */
const REFRESH_INTERVAL_MS = 10_000;

export interface UseLiveMetrics {
  status: LiveMetricsStatus;
  metrics: MetricsResponse | null;
  isRefreshing: boolean;
  errorMessage: string | null;
  reload: () => void;
}

/**
 * Loads `/api/metrics` on mount and then polls every 10 seconds while mounted, following the
 * Epic 15/16 state-machine + `AbortController` pattern. A refresh keeps the last good numbers
 * on screen instead of flashing back to the loading state, and the error state only takes
 * over on the very first load (when there is nothing to show yet).
 */
export function useLiveMetrics(): UseLiveMetrics {
  const [status, setStatus] = useState<LiveMetricsStatus>("loading");
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const activeRequest = useRef<AbortController | null>(null);

  const fetchMetrics = useCallback(async () => {
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    setIsRefreshing(true);

    try {
      const next = await getMetrics(controller.signal);
      if (controller.signal.aborted) {
        return;
      }
      setMetrics(next);
      setStatus("success");
      setErrorMessage(null);
    } catch (caughtError) {
      if (controller.signal.aborted) {
        return;
      }
      setErrorMessage(
        caughtError instanceof Error ? caughtError.message : "Could not load metrics.",
      );
      // Keep showing the last good numbers on a failed refresh; only the first load fails hard.
      setStatus((current) => (current === "success" ? current : "error"));
    } finally {
      if (activeRequest.current === controller) {
        activeRequest.current = null;
        setIsRefreshing(false);
      }
    }
  }, []);

  useEffect(() => {
    void fetchMetrics();
    const intervalId = window.setInterval(() => void fetchMetrics(), REFRESH_INTERVAL_MS);
    return () => {
      window.clearInterval(intervalId);
      activeRequest.current?.abort();
    };
  }, [fetchMetrics]);

  const reload = useCallback(() => {
    setStatus("loading");
    void fetchMetrics();
  }, [fetchMetrics]);

  return { status, metrics, isRefreshing, errorMessage, reload };
}
