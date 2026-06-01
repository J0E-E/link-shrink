import styles from "./VisibilityNotice.module.css";

/**
 * The landing-page visibility warning (TDD §5.10 hard acceptance criterion). The
 * `DemoModal` flags the public nature of the site on first load site-wide; this notice
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
        Before you shrink a link
      </h2>
      <p className={styles.noticeBody} id="visibility-notice-body">
        This is an account-less public demo. Anyone can browse the analytics. That means every link
        you create is out in the open, destination URL and click analytics included.
      </p>
      <p className={styles.noticeEmphasis} id="visibility-notice-emphasis">
        Do not shorten any private, sensitive, or confidential links.
      </p>
    </section>
  );
}
