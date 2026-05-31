import { NavLink } from "react-router-dom";

import { NAVIGATION_ITEMS } from "../../../navigation";
import styles from "./SiteNav.module.css";

interface SiteNavProps {
  navId: string;
  isMobileOpen: boolean;
  onNavigate: () => void;
}

/**
 * Primary navigation links, mapped from the single `NAVIGATION_ITEMS` source. On
 * mobile the list is hidden until the toggle opens it; `isMobileOpen` drives that.
 * Selecting a link calls `onNavigate` so the header can close the mobile menu.
 */
export default function SiteNav({ navId, isMobileOpen, onNavigate }: SiteNavProps) {
  const navClassName = isMobileOpen ? `${styles.nav} ${styles.navOpen}` : styles.nav;

  return (
    <nav className={navClassName} id={navId} aria-label="Primary">
      <ul className={styles.navList} id="site-nav-list">
        {NAVIGATION_ITEMS.map((item) => (
          <li className={styles.navListItem} id={`${item.id}-item`} key={item.path}>
            <NavLink
              to={item.path}
              id={item.id}
              end={item.path === "/"}
              onClick={onNavigate}
              className={({ isActive }) =>
                isActive ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink
              }
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
