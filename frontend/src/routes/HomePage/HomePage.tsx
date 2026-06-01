import VisibilityNotice from "../../components/VisibilityNotice/VisibilityNotice";
import ShortenForm from "./ShortenForm";
import FeatureHighlights from "./FeatureHighlights";
import PortfolioBlurb from "./PortfolioBlurb";
import styles from "./HomePage.module.css";

/**
 * The landing page. The URL input is the visual focus per the design guide; the live
 * shorten flow (submit, result card, QR download) lives in `ShortenForm`. Beneath it, a
 * feature row and a portfolio blurb frame the app as a workflow demo, and the visibility
 * notice is the §5.10 hard acceptance criterion. The system design notes live on the How
 * It Works page.
 */
export default function HomePage() {
  return (
    <div className={styles.page} id="home-page">
      <section className={styles.hero} id="home-hero" aria-labelledby="home-hero-title">
        <span className={styles.heroBadge} id="home-hero-badge">
          <span className={styles.heroBadgeDot} id="home-hero-badge-dot" aria-hidden="true" />
          Portfolio project · built with an AI-assisted workflow
        </span>
        <h1 className={styles.heroTitle} id="home-hero-title">
          Shrink that giant link
        </h1>
        <p className={styles.heroSubtitle} id="home-hero-subtitle">
          Paste a comically long URL. Get a tidy short link with a QR code.
        </p>
        <ShortenForm />
      </section>
      <VisibilityNotice />
      <FeatureHighlights />
      <PortfolioBlurb />
    </div>
  );
}
