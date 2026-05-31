import type { CreateLinkResponse } from "../../api/types";
import CopyButton from "./CopyButton";
import QrPanel from "./QrPanel";
import styles from "./ResultCard.module.css";

interface ResultCardProps {
  result: CreateLinkResponse;
  onReset: () => void;
}

/** Format an ISO timestamp as a readable local date and time, e.g. "30 Jun 2026, 14:30". */
function formatExpiry(isoTimestamp: string): string {
  const expiryDate = new Date(isoTimestamp);
  if (Number.isNaN(expiryDate.getTime())) {
    return isoTimestamp;
  }
  return expiryDate.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * The success result for a shortened link: the short URL with a copy button, the original
 * destination, when it expires, the QR code, and a way to shorten another link.
 */
export default function ResultCard({ result, onReset }: ResultCardProps) {
  return (
    <section className={styles.card} id="result-card" aria-labelledby="result-card-title">
      <h2 className={styles.title} id="result-card-title">
        Your short link is ready
      </h2>

      <div className={styles.shortUrlRow} id="result-short-url-row">
        <a
          className={styles.shortUrl}
          id="result-short-url"
          href={result.short_url}
          target="_blank"
          rel="noreferrer noopener"
        >
          {result.short_url}
        </a>
        <CopyButton value={result.short_url} />
      </div>

      <dl className={styles.details} id="result-details">
        <dt className={styles.detailTerm} id="result-original-term">
          Destination
        </dt>
        <dd className={styles.detailValue} id="result-original-value">
          {result.original_url}
        </dd>
        <dt className={styles.detailTerm} id="result-expiry-term">
          Expires
        </dt>
        <dd className={styles.detailValue} id="result-expiry-value">
          {formatExpiry(result.expires_at)}
        </dd>
      </dl>

      <QrPanel shortCode={result.short_code} />

      <button
        type="button"
        className={styles.resetButton}
        id="result-reset-button"
        onClick={onReset}
      >
        Shorten another
      </button>
    </section>
  );
}
