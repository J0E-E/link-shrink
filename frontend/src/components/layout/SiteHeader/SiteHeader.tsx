import { useState } from "react";
import { Link } from "react-router-dom";

import SiteNav from "../SiteNav/SiteNav";
import MobileNavToggle from "../MobileNavToggle/MobileNavToggle";
import styles from "./SiteHeader.module.css";

const MOBILE_NAV_ID = "site-nav";

/**
 * The top bar: brand wordmark, primary navigation, and a toggle that collapses the
 * navigation on mobile. The header owns the open/closed state and shares it with both
 * the toggle button and the nav so their ARIA wiring stays consistent.
 */
export default function SiteHeader() {
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  const toggleMobileNav = () => setIsMobileNavOpen((wasOpen) => !wasOpen);
  const closeMobileNav = () => setIsMobileNavOpen(false);

  return (
    <header className={styles.header} id="site-header">
      <div className={styles.headerInner} id="site-header-inner">
        <Link to="/" className={styles.brand} id="site-brand" onClick={closeMobileNav}>
          <img
            className={styles.brandMark}
            id="site-brand-mark"
            src="/images/linkshrink.png"
            alt=""
            aria-hidden="true"
            width={48}
            height={32}
          />
          <span className={styles.brandText} id="site-brand-text">
            LinkShrink
          </span>
        </Link>

        <MobileNavToggle
          isOpen={isMobileNavOpen}
          onToggle={toggleMobileNav}
          controlsId={MOBILE_NAV_ID}
        />

        <SiteNav navId={MOBILE_NAV_ID} isMobileOpen={isMobileNavOpen} onNavigate={closeMobileNav} />
      </div>
    </header>
  );
}
