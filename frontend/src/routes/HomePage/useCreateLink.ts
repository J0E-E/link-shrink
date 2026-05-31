/*
 * Owns the state machine for the Home page shorten flow: it calls `createLink`, tracks
 * whether a request is in flight, and holds either the created link or a field-aware
 * error. An `AbortController` cancels an in-flight (or superseded) request so a slow
 * response can never overwrite newer state or fire after the page unmounts.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { createLink } from "../../api/client";
import type { CreateLinkRequest, CreateLinkResponse } from "../../api/types";
import { describeCreateLinkError, type CreateLinkErrorInfo } from "./createLinkErrors";

export type CreateLinkStatus = "idle" | "submitting" | "success" | "error";

export interface UseCreateLink {
  status: CreateLinkStatus;
  result: CreateLinkResponse | null;
  error: CreateLinkErrorInfo | null;
  isSubmitting: boolean;
  submit: (payload: CreateLinkRequest) => Promise<void>;
  reset: () => void;
}

/** Drives the create-link request and exposes its status, result, and error to the form. */
export function useCreateLink(): UseCreateLink {
  const [status, setStatus] = useState<CreateLinkStatus>("idle");
  const [result, setResult] = useState<CreateLinkResponse | null>(null);
  const [error, setError] = useState<CreateLinkErrorInfo | null>(null);
  const activeRequest = useRef<AbortController | null>(null);

  const cancelActiveRequest = useCallback(() => {
    activeRequest.current?.abort();
    activeRequest.current = null;
  }, []);

  const submit = useCallback(
    async (payload: CreateLinkRequest) => {
      cancelActiveRequest();
      const controller = new AbortController();
      activeRequest.current = controller;

      setStatus("submitting");
      setError(null);

      try {
        const created = await createLink(payload, controller.signal);
        if (controller.signal.aborted) {
          return;
        }
        setResult(created);
        setStatus("success");
      } catch (caughtError) {
        // A cancelled request is intentional — leave the state for the newer request.
        if (controller.signal.aborted) {
          return;
        }
        setError(describeCreateLinkError(caughtError));
        setStatus("error");
      } finally {
        if (activeRequest.current === controller) {
          activeRequest.current = null;
        }
      }
    },
    [cancelActiveRequest],
  );

  const reset = useCallback(() => {
    cancelActiveRequest();
    setStatus("idle");
    setResult(null);
    setError(null);
  }, [cancelActiveRequest]);

  // Abort any in-flight request if the page unmounts mid-submit.
  useEffect(() => cancelActiveRequest, [cancelActiveRequest]);

  return {
    status,
    result,
    error,
    isSubmitting: status === "submitting",
    submit,
    reset,
  };
}
