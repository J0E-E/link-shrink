import { Link } from "react-router-dom";

import type { LinkView } from "../../api/types";
import { formatDateTime, formatRelative } from "../../utils/datetime";
import styles from "./LinkCard.module.css";

interface LinkCardProps {
  link: LinkView;
}

/**
 * One link in the dashboard feed: its short code, whether it is a custom alias or a
 * generated code, the destination it points at, and when it was created/expires. The whole
 * card links to that link's analytics view.
 */
export default function LinkCard({ link }: LinkCardProps) {
  const cardId = `link-card-${link.short_code}`;

  return (
    <li className={styles.item} id={`${cardId}-item`}>
      <Link
        className={styles.card}
        id={cardId}
        to={`/dashboard/${link.short_code}`}
        aria-label={`View analytics for ${link.short_code}`}
      >
        <div className={styles.header} id={`${cardId}-header`}>
          <span className={styles.shortCode} id={`${cardId}-short-code`}>
            /{link.short_code}
          </span>
          <span
            className={link.is_custom ? `${styles.badge} ${styles.badgeCustom}` : styles.badge}
            id={`${cardId}-badge`}
          >
            {link.is_custom ? "Custom" : "Generated"}
          </span>
          <span className={styles.arrow} id={`${cardId}-arrow`} aria-hidden="true">
            ↗
          </span>
        </div>

        <span className={styles.destination} id={`${cardId}-destination`} title={link.original_url}>
          {link.original_url}
        </span>

        <dl className={styles.meta} id={`${cardId}-meta`}>
          <div className={styles.metaPair} id={`${cardId}-created-pair`}>
            <dt className={styles.metaTerm} id={`${cardId}-created-term`}>
              Created
            </dt>
            <dd className={styles.metaValue} id={`${cardId}-created-value`}>
              {formatRelative(link.created_at)}
            </dd>
          </div>
          <div className={styles.metaPair} id={`${cardId}-expires-pair`}>
            <dt className={styles.metaTerm} id={`${cardId}-expires-term`}>
              Expires
            </dt>
            <dd className={styles.metaValue} id={`${cardId}-expires-value`}>
              {formatDateTime(link.expires_at)}
            </dd>
          </div>
        </dl>
      </Link>
    </li>
  );
}
