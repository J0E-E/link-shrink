import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";

import AppShell from "./components/layout/AppShell/AppShell";
import HomePage from "./routes/HomePage/HomePage";
import DashboardPage from "./routes/DashboardPage/DashboardPage";
import HowItWorksPage from "./routes/HowItWorksPage/HowItWorksPage";
import HowIWorkPage from "./routes/HowIWorkPage/HowIWorkPage";

// The analytics view pulls in the charting library; lazy-load it so the home and dashboard
// routes don't carry that weight in the initial bundle.
const LinkAnalyticsPage = lazy(() => import("./routes/DashboardPage/analytics/LinkAnalyticsPage"));

/**
 * Top-level routing. A single layout route renders the persistent shell (demo
 * banner, header, footer) and the matched page renders into its main outlet, so
 * navigating between routes never re-mounts the shell.
 */
export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route
          path="/dashboard/:code"
          element={
            <Suspense
              fallback={
                <p id="analytics-route-loading" role="status">
                  Loading analytics…
                </p>
              }
            >
              <LinkAnalyticsPage />
            </Suspense>
          }
        />
        <Route path="/how-it-works" element={<HowItWorksPage />} />
        <Route path="/how-i-work" element={<HowIWorkPage />} />
      </Route>
    </Routes>
  );
}
