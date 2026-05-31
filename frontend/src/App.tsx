import { Routes, Route } from "react-router-dom";

import AppShell from "./components/layout/AppShell/AppShell";
import HomePage from "./routes/HomePage/HomePage";
import DashboardPage from "./routes/DashboardPage/DashboardPage";
import HowItWorksPage from "./routes/HowItWorksPage/HowItWorksPage";

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
        <Route path="/how-it-works" element={<HowItWorksPage />} />
      </Route>
    </Routes>
  );
}
