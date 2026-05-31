import CopyButton from "../../../components/CopyButton/CopyButton";
import type { LinkView } from "../../../api/types";
import { formatDateTime } from "../../../utils/datetime";
import styles from "./AnalyticsHeader.module.css";

interface AnalyticsHeaderProps {
  link: LinkView;
}

/** The identity block for the analytics view: short URL, destination, and lifetime dates. */
export default function AnalyticsHeader({ link }: AnalyticsHeaderProps) {
  return (
    <header
      className={styles.header}
      id="analytics-header"
      aria-labelledby="analytics-header-short-url"
    >
      <div className={styles.shortUrlRow} id="analytics-short-url-row">
        <a
          className={styles.shortUrl}
          id="analytics-header-short-url"
          href={link.short_url}
          target="_blank"
          rel="noreferrer noopener"
        >
          {link.short_url}
        </a>
        <CopyButton value={link.short_url} elementId="analytics-copy-button" />
      </div>

      <dl className={styles.details} id="analytics-header-details">
        <dt className={styles.detailTerm} id="analytics-destination-term">
          Destination
        </dt>
        <dd className={styles.detailValue} id="analytics-destination-value" title={link.original_url}>
          {link.original_url}
        </dd>
        <dt className={styles.detailTerm} id="analytics-created-term">
          Created
        </dt>
        <dd className={styles.detailValue} id="analytics-created-value">
          {formatDateTime(link.created_at)}
        </dd>
        <dt className={styles.detailTerm} id="analytics-expires-term">
          Expires
        </dt>
        <dd className={styles.detailValue} id="analytics-expires-value">
          {formatDateTime(link.expires_at)}
        </dd>
      </dl>
    </header>
  );
}
