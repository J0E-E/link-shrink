import styles from "./DemoBanner.module.css";

/**
 * Persistent public-demo warning, rendered at the top of the shell on every route
 * (TDD §5.10 hard acceptance criterion). It states plainly that this is a public demo
 * and that every shortened link and its analytics are visible to anyone.
 */
export default function DemoBanner() {
  return (
    <aside className={styles.banner} id="demo-banner" role="note" aria-label="Public demo notice">
      <div className={styles.bannerInner} id="demo-banner-inner">
        <span className={styles.bannerIcon} id="demo-banner-icon" aria-hidden="true">
          ⚠
        </span>
        <p className={styles.bannerText} id="demo-banner-text">
          <strong className={styles.bannerLabel} id="demo-banner-label">
            Public demo:
          </strong>{" "}
          every shortened link — its destination and analytics — is visible to anyone. Do not
          shorten private, sensitive, or confidential links.
        </p>
      </div>
    </aside>
  );
}
