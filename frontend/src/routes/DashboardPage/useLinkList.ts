/*
 * Owns the dashboard's link-list state: it loads the first page on mount, accumulates
 * pages as the user clicks "Load more", and tracks the keyset cursor. An `AbortController`
 * cancels an in-flight (or superseded) request so a slow response can never overwrite
 * newer state or fire after the page unmounts. Mirrors the `useCreateLink` pattern.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { listLinks } from "../../api/client";
import type { LinkView } from "../../api/types";

export type LinkListStatus = "loading" | "success" | "error";

export interface UseLinkList {
  status: LinkListStatus;
  items: LinkView[];
  nextCursor: string | null;
  hasMore: boolean;
  isLoadingMore: boolean;
  errorMessage: string | null;
  loadMoreError: string | null;
  loadMore: () => Promise<void>;
  reload: () => Promise<void>;
}

const GENERIC_ERROR_MESSAGE = "Something went wrong loading your links.";

/** Drives the paginated link feed and exposes its items, paging state, and errors. */
export function useLinkList(): UseLinkList {
  const [status, setStatus] = useState<LinkListStatus>("loading");
  const [items, setItems] = useState<LinkView[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [loadMoreError, setLoadMoreError] = useState<string | null>(null);
  const activeRequest = useRef<AbortController | null>(null);

  const cancelActiveRequest = useCallback(() => {
    activeRequest.current?.abort();
    activeRequest.current = null;
  }, []);

  /**
   * Fetch one page. `cursor` null starts a fresh feed (first load / reload) and replaces
   * the items; a non-null cursor appends the next page.
   */
  const fetchPage = useCallback(
    async (cursor: string | null) => {
      cancelActiveRequest();
      const controller = new AbortController();
      activeRequest.current = controller;

      const isInitialLoad = cursor === null;
      if (isInitialLoad) {
        setStatus("loading");
        setErrorMessage(null);
      } else {
        setIsLoadingMore(true);
        setLoadMoreError(null);
      }

      try {
        const page = await listLinks(cursor, undefined, controller.signal);
        if (controller.signal.aborted) {
          return;
        }
        setItems((previousItems) =>
          isInitialLoad ? page.items : [...previousItems, ...page.items],
        );
        setNextCursor(page.next_cursor);
        setHasMore(page.next_cursor !== null);
        setStatus("success");
      } catch (caughtError) {
        // A cancelled request is intentional — leave the state for the newer request.
        if (controller.signal.aborted) {
          return;
        }
        const message =
          caughtError instanceof Error ? caughtError.message : GENERIC_ERROR_MESSAGE;
        if (isInitialLoad) {
          setErrorMessage(message);
          setStatus("error");
        } else {
          // Keep the already-loaded feed on screen; surface the paging failure inline so
          // the user can retry "Load more" instead of failing silently.
          setLoadMoreError(message);
        }
      } finally {
        if (activeRequest.current === controller) {
          activeRequest.current = null;
        }
        // Clear the spinner unconditionally: a reload that supersedes an in-flight
        // "Load more" doesn't manage isLoadingMore itself, so the finishing request must.
        setIsLoadingMore(false);
      }
    },
    [cancelActiveRequest],
  );

  const loadMore = useCallback(async () => {
    if (!hasMore || isLoadingMore) {
      return;
    }
    await fetchPage(nextCursor);
  }, [fetchPage, hasMore, isLoadingMore, nextCursor]);

  const reload = useCallback(async () => {
    await fetchPage(null);
  }, [fetchPage]);

  // Load the first page on mount and abort it if the page unmounts mid-request.
  useEffect(() => {
    void fetchPage(null);
    return cancelActiveRequest;
  }, [fetchPage, cancelActiveRequest]);

  return {
    status,
    items,
    nextCursor,
    hasMore,
    isLoadingMore,
    errorMessage,
    loadMoreError,
    loadMore,
    reload,
  };
}
