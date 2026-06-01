import type { ReactNode } from "react";

import styles from "./FeatureHighlights.module.css";

interface Feature {
  id: string;
  title: string;
  description: string;
  icon: ReactNode;
}

/**
 * The three things LinkShrink does, shown as a compact card row beneath the hero. Keeps
 * the landing page from feeling empty while staying minimal per the design guide — icon,
 * a short title, and one line of copy each.
 */
const FEATURES: Feature[] = [
  {
    id: "home-feature-short-links",
    title: "Instant short links",
    description: "Paste any giant URL and get a tidy, shareable short link in seconds.",
    icon: (
      <svg
        id="home-feature-short-links-glyph"
        viewBox="0 0 24 24"
        width="22"
        height="22"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </svg>
    ),
  },
  {
    id: "home-feature-qr-codes",
    title: "QR codes built in",
    description: "Every short link comes with a downloadable QR code, ready to print.",
    icon: (
      <svg
        id="home-feature-qr-codes-glyph"
        viewBox="0 0 24 24"
        width="22"
        height="22"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <path d="M14 14h3v3" />
        <path d="M21 14v7" />
        <path d="M14 21h3" />
      </svg>
    ),
  },
  {
    id: "home-feature-analytics",
    title: "Click analytics",
    description: "See clicks and referrers for every link on the public dashboard.",
    icon: (
      <svg
        id="home-feature-analytics-glyph"
        viewBox="0 0 24 24"
        width="22"
        height="22"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <line x1="4" y1="20" x2="4" y2="12" />
        <line x1="10" y1="20" x2="10" y2="4" />
        <line x1="16" y1="20" x2="16" y2="14" />
        <line x1="20" y1="20" x2="20" y2="9" />
      </svg>
    ),
  },
];

export default function FeatureHighlights() {
  return (
    <section className={styles.features} id="home-features" aria-label="What LinkShrink does">
      <ul className={styles.featureList} id="home-features-list">
        {FEATURES.map((feature) => (
          <li className={styles.featureCard} id={feature.id} key={feature.id}>
            <span className={styles.featureIcon} id={`${feature.id}-icon`} aria-hidden="true">
              {feature.icon}
            </span>
            <h2 className={styles.featureTitle} id={`${feature.id}-title`}>
              {feature.title}
            </h2>
            <p className={styles.featureDescription} id={`${feature.id}-description`}>
              {feature.description}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
