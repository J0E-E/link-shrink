import styles from "./VisibilityNotice.module.css";

/**
 * The landing-page visibility warning (TDD §5.10 hard acceptance criterion). The
 * persistent `DemoBanner` flags the public nature of the site site-wide; this notice
 * is the Home-page expansion that spells out, in full, why a user must not shorten any
 * private, sensitive, or confidential link here.
 */
export default function VisibilityNotice() {
  return (
    <section
      className={styles.notice}
      id="visibility-notice"
      aria-labelledby="visibility-notice-title"
    >
      <h2 className={styles.noticeTitle} id="visibility-notice-title">
        Before you shorten a link
      </h2>
      <p className={styles.noticeBody} id="visibility-notice-body">
        This is an account-less public demo. Anyone can browse the dashboard, so every link you
        create — its destination URL and its click analytics — is visible to everyone.
      </p>
      <p className={styles.noticeEmphasis} id="visibility-notice-emphasis">
        Do not shorten any private, sensitive, or confidential links.
      </p>
    </section>
  );
}
