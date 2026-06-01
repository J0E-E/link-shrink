import styles from "./SiteFooter.module.css";

/**
 * The site footer: a short project descriptor and a standing reminder that this is a
 * public demo. Kept text-light per the design guide.
 */
export default function SiteFooter() {
  return (
    <footer className={styles.footer} id="site-footer">
      <div className={styles.footerInner} id="site-footer-inner">
        <p className={styles.footerText} id="site-footer-text">
          LinkShrink. A system design focused URL shortener demo, built for fun.
        </p>
        <p className={styles.footerNote} id="site-footer-note">
          Public demo. Do not shorten private or sensitive links.
        </p>
      </div>
    </footer>
  );
}
