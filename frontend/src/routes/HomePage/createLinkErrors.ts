/*
 * Maps a failed `POST /api/links` call to a user-facing message and the form field it
 * belongs to, so the Home page can show the error next to the right input. We branch on
 * the API's symbolic `reason` (carried by `ApiError`) rather than message text — see the
 * error envelope notes in `api/client.ts`.
 */

import { ApiError } from "../../api/client";

/** Which part of the form an error should be shown against. */
export type CreateLinkErrorField = "url" | "alias" | "form";

export interface CreateLinkErrorInfo {
  field: CreateLinkErrorField;
  message: string;
}

/** URL validation reasons returned by the API (all map to the URL field). */
const URL_ERROR_MESSAGES: Record<string, string> = {
  url_scheme: "Enter a URL that starts with http:// or https://.",
  url_length: "Whoa, that URL is enormous. Keep it under 2,048 characters.",
  url_malformed: "That does not look like a valid URL. Check it and try again.",
  url_no_host: "That URL is missing a website address.",
  url_self_referential: "You cannot shorten a link that points back at this site.",
  url_unresolvable: "We could not find that website. Check the address and try again.",
  url_private_address: "That address is not allowed. Use a public website URL.",
};

/** Alias validation/conflict reasons returned by the API (all map to the alias field). */
const ALIAS_ERROR_MESSAGES: Record<string, string> = {
  alias_length: "Custom alias must be between 3 and 32 characters.",
  alias_grammar: "Custom alias can only use lowercase letters, numbers, and hyphens.",
  // Must match the backend reason exactly (REASON_ALIAS_HYPHEN in shared/validation.py).
  alias_leading_or_trailing_hyphen: "Custom alias cannot start or end with a hyphen.",
  alias_reserved: "That alias is reserved. Please choose another.",
  alias_taken: "That alias is already taken. Please choose another.",
};

const RATE_LIMITED_MESSAGE = "Easy there, speedy. Give it a moment and try again.";
const FALLBACK_MESSAGE = "Something went wrong creating your link. Please try again.";

/**
 * Turn any error thrown while creating a link into a field + friendly message. Unknown
 * `ApiError` reasons fall back to the API's own (human-readable) message; non-API errors
 * (network failures, etc.) use a generic message.
 */
export function describeCreateLinkError(error: unknown): CreateLinkErrorInfo {
  if (error instanceof ApiError) {
    if (error.reason in URL_ERROR_MESSAGES) {
      return { field: "url", message: URL_ERROR_MESSAGES[error.reason] };
    }
    if (error.reason in ALIAS_ERROR_MESSAGES) {
      return { field: "alias", message: ALIAS_ERROR_MESSAGES[error.reason] };
    }
    if (error.reason === "rate_limited") {
      return { field: "form", message: RATE_LIMITED_MESSAGE };
    }
    return { field: "form", message: error.message || FALLBACK_MESSAGE };
  }
  return { field: "form", message: FALLBACK_MESSAGE };
}
