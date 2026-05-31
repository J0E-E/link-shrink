import { Outlet } from "react-router-dom";

import DemoBanner from "../../DemoBanner/DemoBanner";
import SiteHeader from "../SiteHeader/SiteHeader";
import SiteFooter from "../SiteFooter/SiteFooter";
import styles from "./AppShell.module.css";

/**
 * The application frame shared by every route: a persistent public-demo banner, the
 * header with navigation, the routed page content, and the footer. The current page
 * renders into the `Outlet`, so the shell stays mounted as routes change.
 */
export default function AppShell() {
  return (
    <div className={styles.shell} id="app-shell">
      <DemoBanner />
      <SiteHeader />
      <main className={styles.main} id="app-main">
        <div className={styles.mainInner} id="app-main-inner">
          <Outlet />
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
