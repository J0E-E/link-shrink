/*
 * Loads everything the per-link analytics view needs: the link detail (for the short URL,
 * destination, expiry, and QR) and the aggregated analytics, fetched in parallel under one
 * `AbortController`. A 404 on either call becomes a distinct `notFound` state so the page
 * can show a "no such link" message instead of a generic error. Mirrors `useCreateLink`.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, getLink, getLinkAnalytics } from "../../../api/client";
import type { LinkAnalyticsResponse, LinkView } from "../../../api/types";

export type LinkAnalyticsStatus = "loading" | "success" | "notFound" | "error";

export interface UseLinkAnalytics {
  status: LinkAnalyticsStatus;
  link: LinkView | null;
  analytics: LinkAnalyticsResponse | null;
  errorMessage: string | null;
  reload: () => Promise<void>;
}

/** Drives the link-detail + analytics load for one short code. */
export function useLinkAnalytics(code: string): UseLinkAnalytics {
  const [status, setStatus] = useState<LinkAnalyticsStatus>("loading");
  const [link, setLink] = useState<LinkView | null>(null);
  const [analytics, setAnalytics] = useState<LinkAnalyticsResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const activeRequest = useRef<AbortController | null>(null);

  const cancelActiveRequest = useCallback(() => {
    activeRequest.current?.abort();
    activeRequest.current = null;
  }, []);

  const load = useCallback(async () => {
    cancelActiveRequest();
    const controller = new AbortController();
    activeRequest.current = controller;

    setStatus("loading");
    setErrorMessage(null);

    try {
      const [linkDetail, linkAnalytics] = await Promise.all([
        getLink(code, controller.signal),
        getLinkAnalytics(code, controller.signal),
      ]);
      if (controller.signal.aborted) {
        return;
      }
      setLink(linkDetail);
      setAnalytics(linkAnalytics);
      setStatus("success");
    } catch (caughtError) {
      // A cancelled request is intentional — leave the state for the newer request.
      if (controller.signal.aborted) {
        return;
      }
      // One of the parallel calls failed; abort the still-in-flight sibling so it can't
      // keep running (or resolve into discarded state) after we've already failed.
      controller.abort();
      if (caughtError instanceof ApiError && caughtError.reason === "not_found") {
        setStatus("notFound");
        return;
      }
      setErrorMessage(
        caughtError instanceof Error
          ? caughtError.message
          : "Something went wrong loading these analytics.",
      );
      setStatus("error");
    } finally {
      if (activeRequest.current === controller) {
        activeRequest.current = null;
      }
    }
  }, [cancelActiveRequest, code]);

  // Reload whenever the code changes and abort on unmount.
  useEffect(() => {
    void load();
    return cancelActiveRequest;
  }, [load, cancelActiveRequest]);

  return { status, link, analytics, errorMessage, reload: load };
}
