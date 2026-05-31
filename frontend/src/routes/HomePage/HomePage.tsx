import Annotation from "../../components/Annotation/Annotation";
import VisibilityNotice from "../../components/VisibilityNotice/VisibilityNotice";
import ShortenForm from "./ShortenForm";
import styles from "./HomePage.module.css";

/**
 * The landing page. The URL input is the visual focus per the design guide; the live
 * shorten flow (submit, result card, QR download) lives in `ShortenForm`. The visibility
 * notice is the §5.10 hard acceptance criterion for this page.
 */
export default function HomePage() {
  return (
    <div className={styles.page} id="home-page">
      <section className={styles.hero} id="home-hero" aria-labelledby="home-hero-title">
        <h1 className={styles.heroTitle} id="home-hero-title">
          Shorten a link in seconds
        </h1>
        <p className={styles.heroSubtitle} id="home-hero-subtitle">
          Paste a long URL, get a short link with a QR code, and watch the clicks roll in.
        </p>
        <ShortenForm />
      </section>
      <VisibilityNotice />
      <Annotation id="annotation-home-rate-limiting" title="Rate limiting" headingLevel={2}>
        Creating links is rate-limited per IP — 10 per minute and 100 per day — using fixed-window
        counters in Redis. Browsing the dashboard and following short links are never throttled.
      </Annotation>
      <Annotation id="annotation-home-validation" title="URL validation &amp; SSRF guard" headingLevel={2}>
        Before a link is created the destination is checked: only http and https, at most 2048
        characters, and the host is resolved and rejected if it points at a private, loopback, or
        link-local address — so the shortener can&apos;t be used to probe internal services.
      </Annotation>
    </div>
  );
}
