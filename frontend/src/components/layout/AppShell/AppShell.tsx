import { Outlet } from "react-router-dom";

import DemoModal from "../../DemoModal/DemoModal";
import SiteHeader from "../SiteHeader/SiteHeader";
import styles from "./AppShell.module.css";

/**
 * The application frame shared by every route: a centered public-demo modal shown on
 * first load, the header with navigation, and the routed page content. The current page
 * renders into the `Outlet`, so the shell stays mounted as routes change.
 */
export default function AppShell() {
  return (
    <div className={styles.shell} id="app-shell">
      <DemoModal />
      <SiteHeader />
      <main className={styles.main} id="app-main">
        <div className={styles.mainInner} id="app-main-inner">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
