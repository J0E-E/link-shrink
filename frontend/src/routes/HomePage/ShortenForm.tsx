import { useCallback, useState } from "react";

import type { CreateLinkRequest } from "../../api/types";
import AdvancedOptions from "./AdvancedOptions";
import { DEFAULT_EXPIRY_SECONDS } from "./expiry";
import ResultCard from "./ResultCard";
import { useCreateLink } from "./useCreateLink";
import styles from "./ShortenForm.module.css";

/**
 * The live shorten flow: a URL field (the primary focus), optional advanced settings
 * (custom alias + expiry), and a submit that calls `POST /api/links`. On success it swaps
 * itself for the `ResultCard`; on failure it shows the error against the relevant field.
 */
export default function ShortenForm() {
  const [url, setUrl] = useState("");
  const [alias, setAlias] = useState("");
  const [ttlSeconds, setTtlSeconds] = useState(DEFAULT_EXPIRY_SECONDS);
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);

  const { status, result, error, isSubmitting, submit, reset } = useCreateLink();

  const urlError = error?.field === "url" ? error.message : null;
  const aliasError = error?.field === "alias" ? error.message : null;
  const formError = error?.field === "form" ? error.message : null;

  const handleSubmit = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const trimmedUrl = url.trim();
      if (!trimmedUrl) {
        return;
      }
      const trimmedAlias = alias.trim();
      const payload: CreateLinkRequest = { url: trimmedUrl, ttl_seconds: ttlSeconds };
      if (trimmedAlias) {
        payload.alias = trimmedAlias;
      }
      void submit(payload);
    },
    [url, alias, ttlSeconds, submit],
  );

  const handleReset = useCallback(() => {
    reset();
    setUrl("");
    setAlias("");
    setTtlSeconds(DEFAULT_EXPIRY_SECONDS);
    setIsAdvancedOpen(false);
  }, [reset]);

  if (status === "success" && result) {
    return <ResultCard result={result} onReset={handleReset} />;
  }

  return (
    <form className={styles.form} id="shorten-form" onSubmit={handleSubmit} noValidate>
      <div className={styles.inputRow} id="shorten-url-row">
        <label className={styles.label} htmlFor="shorten-url-input" id="shorten-url-label">
          Long URL
        </label>
        <input
          className={styles.input}
          id="shorten-url-input"
          type="url"
          inputMode="url"
          autoComplete="off"
          placeholder="https://example.com/a-very-long-url-to-shorten"
          value={url}
          disabled={isSubmitting}
          required
          aria-invalid={urlError ? true : undefined}
          aria-describedby={urlError ? "shorten-url-error" : undefined}
          onChange={(event) => setUrl(event.target.value)}
        />
        {urlError && (
          <p className={styles.fieldError} id="shorten-url-error" role="alert">
            {urlError}
          </p>
        )}
      </div>

      <AdvancedOptions
        isOpen={isAdvancedOpen}
        onToggle={() => setIsAdvancedOpen((previousIsOpen) => !previousIsOpen)}
        alias={alias}
        onAliasChange={setAlias}
        ttlSeconds={ttlSeconds}
        onTtlSecondsChange={setTtlSeconds}
        aliasError={aliasError}
        isDisabled={isSubmitting}
      />

      <button
        className={styles.submitButton}
        id="shorten-submit"
        type="submit"
        disabled={isSubmitting}
      >
        {isSubmitting ? "Shrinking…" : "Shrink it"}
      </button>

      <p className={styles.formError} id="shorten-form-error" role="alert">
        {formError ?? ""}
      </p>
    </form>
  );
}
