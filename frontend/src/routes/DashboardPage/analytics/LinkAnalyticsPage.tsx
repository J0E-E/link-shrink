import { Link, useParams } from "react-router-dom";

import type { LinkAnalyticsResponse } from "../../../api/types";
import QrPanel from "../../../components/QrPanel/QrPanel";
import AnalyticsHeader from "./AnalyticsHeader";
import BreakdownChart from "./BreakdownChart";
import DailyClicksChart from "./DailyClicksChart";
import TotalClicks from "./TotalClicks";
import { useLinkAnalytics } from "./useLinkAnalytics";
import styles from "./LinkAnalyticsPage.module.css";

/** The five analytics breakdown dimensions, in display order. */
const BREAKDOWNS: ReadonlyArray<{
  breakdownId: string;
  title: string;
  key: keyof Pick<
    LinkAnalyticsResponse,
    "by_device_type" | "by_browser_family" | "by_os_family" | "by_referrer_domain" | "by_source"
  >;
}> = [
  { breakdownId: "device-type", title: "Device type", key: "by_device_type" },
  { breakdownId: "browser-family", title: "Browser", key: "by_browser_family" },
  { breakdownId: "os-family", title: "Operating system", key: "by_os_family" },
  { breakdownId: "referrer-domain", title: "Referrer", key: "by_referrer_domain" },
  { breakdownId: "source", title: "Source", key: "by_source" },
];

/**
 * The per-link analytics view at `/dashboard/:code`: the link's identity, total clicks, a
 * daily clicks chart, the five dimension breakdowns, and a QR download. Loads the link
 * detail and analytics together; a 404 shows a "not found" message.
 */
export default function LinkAnalyticsPage() {
  const { code = "" } = useParams<{ code: string }>();
  const { status, link, analytics, errorMessage, reload } = useLinkAnalytics(code);

  return (
    <section className={styles.page} id="analytics-page" aria-labelledby="analytics-page-title">
      <div className={styles.topRow} id="analytics-top-row">
        <Link className={styles.backLink} id="analytics-back-link" to="/dashboard">
          ← Back to dashboard
        </Link>
        <h1 className={styles.title} id="analytics-page-title">
          Analytics for /{code}
        </h1>
      </div>

      {status === "loading" && (
        <p className={styles.notice} id="analytics-loading" role="status">
          Loading analytics…
        </p>
      )}

      {status === "notFound" && (
        <div className={styles.notice} id="analytics-not-found">
          <p className={styles.noticeText} id="analytics-not-found-text">
            No link found for <strong id="analytics-not-found-code">/{code}</strong>.
          </p>
          <Link className={styles.noticeLink} id="analytics-not-found-link" to="/dashboard">
            Back to dashboard
          </Link>
        </div>
      )}

      {status === "error" && (
        <div className={styles.notice} id="analytics-error" role="alert">
          <p className={styles.noticeText} id="analytics-error-text">
            {errorMessage ?? "Something went wrong loading these analytics."}
          </p>
          <button
            type="button"
            className={styles.retryButton}
            id="analytics-retry-button"
            onClick={() => void reload()}
          >
            Try again
          </button>
        </div>
      )}

      {status === "success" && link && analytics && (
        <div className={styles.content} id="analytics-content">
          <AnalyticsHeader link={link} />

          <div className={styles.summaryRow} id="analytics-summary-row">
            <TotalClicks totalClicks={analytics.total_clicks} />
            <div className={styles.qrCard} id="analytics-qr-card">
              <QrPanel shortCode={link.short_code} />
            </div>
          </div>

          <DailyClicksChart daily={analytics.daily} />

          <div className={styles.breakdowns} id="analytics-breakdowns">
            {BREAKDOWNS.map((breakdown) => (
              <BreakdownChart
                key={breakdown.breakdownId}
                breakdownId={breakdown.breakdownId}
                title={breakdown.title}
                items={analytics[breakdown.key]}
              />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
