import VisibilityNotice from "../../components/VisibilityNotice/VisibilityNotice";
import ShortenPlaceholder from "./ShortenPlaceholder";
import styles from "./HomePage.module.css";

/**
 * The landing page. The URL input is the visual focus per the design guide; the live
 * shorten flow (submit, result card, QR) is wired up in Epic 15. The visibility notice
 * is the §5.10 hard acceptance criterion for this page.
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
        <ShortenPlaceholder />
      </section>
      <VisibilityNotice />
    </div>
  );
}
