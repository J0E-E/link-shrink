import { Link } from "react-router-dom";

import styles from "./PortfolioBlurb.module.css";

/**
 * The "why this site exists" callout: LinkShrink is a portfolio piece and a live demo of
 * the author's AI-assisted workflow. Links out to the "How I Work" page and the source so
 * visitors can dig into the process behind the product.
 */
export default function PortfolioBlurb() {
  return (
    <section
      className={styles.blurb}
      id="home-portfolio-blurb"
      aria-labelledby="home-portfolio-blurb-title"
    >
      <span className={styles.label} id="home-portfolio-blurb-label" aria-hidden="true">
        ✦ About this project
      </span>
      <h2 className={styles.title} id="home-portfolio-blurb-title">
        A portfolio piece, not just a toy
      </h2>
      <p className={styles.body} id="home-portfolio-blurb-body">
        LinkShrink is a working demo of how I design and ship software with an AI-assisted
        workflow. Every feature started as a written spec, went through a multi-agent review, and
        landed one epic per commit — the app you&apos;re using is the receipt.
      </p>
      <div className={styles.actions} id="home-portfolio-blurb-actions">
        <Link
          className={styles.primaryAction}
          id="home-portfolio-blurb-process-link"
          to="/how-i-work"
        >
          See how I work
          <svg
            className={styles.actionIcon}
            id="home-portfolio-blurb-process-icon"
            viewBox="0 0 24 24"
            width="16"
            height="16"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </Link>
        <a
          className={styles.secondaryAction}
          id="home-portfolio-blurb-repo-link"
          href="https://github.com/J0E-E/link-shrink"
          target="_blank"
          rel="noreferrer noopener"
        >
          <svg
            className={styles.actionIcon}
            id="home-portfolio-blurb-repo-icon"
            viewBox="0 0 24 24"
            width="16"
            height="16"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M12 .5C5.37.5 0 5.87 0 12.5c0 5.3 3.44 9.8 8.21 11.39.6.11.82-.26.82-.58 0-.29-.01-1.04-.02-2.05-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.34-1.76-1.34-1.76-1.09-.75.08-.73.08-.73 1.21.09 1.84 1.24 1.84 1.24 1.07 1.84 2.81 1.31 3.5 1 .11-.78.42-1.31.76-1.61-2.67-.3-5.47-1.34-5.47-5.95 0-1.31.47-2.39 1.24-3.23-.13-.31-.54-1.53.12-3.19 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 0 1 3-.4c1.02 0 2.05.14 3 .4 2.29-1.55 3.3-1.23 3.3-1.23.66 1.66.25 2.88.12 3.19.77.84 1.24 1.92 1.24 3.23 0 4.62-2.81 5.64-5.49 5.94.43.37.81 1.1.81 2.22 0 1.6-.01 2.9-.01 3.29 0 .32.22.7.83.58A12.01 12.01 0 0 0 24 12.5C24 5.87 18.63.5 12 .5z" />
          </svg>
          Browse the source
        </a>
      </div>
    </section>
  );
}
