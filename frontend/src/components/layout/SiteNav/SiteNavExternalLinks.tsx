import styles from "./SiteNav.module.css";

interface SiteNavExternalLinksProps {
  onNavigate: () => void;
}

/**
 * External links shown at the end of the primary nav: the author's portfolio and the
 * project source. Rendered as `<li>` items so they flow with the nav list and stack on
 * mobile. Unlike the internal nav links, these keep the accent color and a leading icon
 * to set them apart as outbound links.
 */
export default function SiteNavExternalLinks({ onNavigate }: SiteNavExternalLinksProps) {
  return (
    <>
      <li className={styles.navListItem} id="nav-item-portfolio-item">
        <a
          className={styles.navExternalLink}
          id="nav-item-portfolio"
          href="https://joeyshub.com"
          target="_blank"
          rel="noreferrer noopener"
          onClick={onNavigate}
        >
          <svg
            className={styles.navExternalIcon}
            id="nav-item-portfolio-icon"
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
            <circle cx="12" cy="12" r="10" />
            <line x1="2" y1="12" x2="22" y2="12" />
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
          </svg>
          <span id="nav-item-portfolio-label">My Portfolio</span>
        </a>
      </li>
      <li className={styles.navListItem} id="nav-item-repo-item">
        <a
          className={styles.navExternalLink}
          id="nav-item-repo"
          href="https://github.com/J0E-E/link-shrink"
          target="_blank"
          rel="noreferrer noopener"
          onClick={onNavigate}
        >
          <svg
            className={styles.navExternalIcon}
            id="nav-item-repo-icon"
            viewBox="0 0 24 24"
            width="16"
            height="16"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M12 .5C5.37.5 0 5.87 0 12.5c0 5.3 3.44 9.8 8.21 11.39.6.11.82-.26.82-.58 0-.29-.01-1.04-.02-2.05-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.34-1.76-1.34-1.76-1.09-.75.08-.73.08-.73 1.21.09 1.84 1.24 1.84 1.24 1.07 1.84 2.81 1.31 3.5 1 .11-.78.42-1.31.76-1.61-2.67-.3-5.47-1.34-5.47-5.95 0-1.31.47-2.39 1.24-3.23-.13-.31-.54-1.53.12-3.19 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 0 1 3-.4c1.02 0 2.05.14 3 .4 2.29-1.55 3.3-1.23 3.3-1.23.66 1.66.25 2.88.12 3.19.77.84 1.24 1.92 1.24 3.23 0 4.62-2.81 5.64-5.49 5.94.43.37.81 1.1.81 2.22 0 1.6-.01 2.9-.01 3.29 0 .32.22.7.83.58A12.01 12.01 0 0 0 24 12.5C24 5.87 18.63.5 12 .5z" />
          </svg>
          <span id="nav-item-repo-label">LinkShrink Repo</span>
        </a>
      </li>
    </>
  );
}
