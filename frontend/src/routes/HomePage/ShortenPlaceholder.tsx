import styles from "./ShortenPlaceholder.module.css";

/**
 * A non-functional preview of the shorten control so the landing layout is reviewable
 * in this scaffold epic. Epic 15 replaces it with the real input, submit handler,
 * result card, and QR download. The field is disabled to make its placeholder status
 * obvious and to avoid implying a working flow.
 */
export default function ShortenPlaceholder() {
  return (
    <form
      className={styles.form}
      id="shorten-placeholder-form"
      aria-describedby="shorten-placeholder-hint"
      onSubmit={(event) => event.preventDefault()}
    >
      <div className={styles.inputRow} id="shorten-placeholder-input-row">
        <label className={styles.label} htmlFor="shorten-placeholder-input" id="shorten-placeholder-label">
          Long URL
        </label>
        <input
          className={styles.input}
          id="shorten-placeholder-input"
          type="url"
          inputMode="url"
          placeholder="https://example.com/a-very-long-url-to-shorten"
          disabled
          aria-disabled="true"
        />
      </div>
      <button
        className={styles.submitButton}
        id="shorten-placeholder-submit"
        type="submit"
        disabled
        aria-disabled="true"
      >
        Shorten
      </button>
      <p className={styles.hint} id="shorten-placeholder-hint">
        The shortening flow arrives in the next release.
      </p>
    </form>
  );
}
