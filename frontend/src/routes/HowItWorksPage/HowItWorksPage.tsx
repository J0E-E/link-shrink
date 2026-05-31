import Annotation from "../../components/Annotation/Annotation";
import ArchitectureDiagram from "./ArchitectureDiagram";
import SystemFlows from "./SystemFlows";
import TechBadgeGrid from "./TechBadgeGrid";
import ScalingStory from "./ScalingStory";
import LiveMetricsPanel from "./LiveMetricsPanel";
import styles from "./HowItWorksPage.module.css";

/**
 * The portfolio/educational page. The architecture, flows, badges, and scaling story are
 * static; only the live metrics panel reads the API. The architecture annotations
 * (`Annotation`) appear only when Educational Mode is on, so the header toggle visibly
 * changes this page.
 */
export default function HowItWorksPage() {
  return (
    <div className={styles.page} id="how-it-works-page">
      <header className={styles.intro} id="how-it-works-intro">
        <h1 className={styles.title} id="how-it-works-page-title">
          How LinkShrink works
        </h1>
        <p className={styles.subtitle} id="how-it-works-subtitle">
          A look under the hood — the services, the request flows, and the choices behind them.
          Turn on Educational Mode in the header to reveal deeper annotations throughout the app.
        </p>
      </header>

      <section
        className={styles.section}
        id="how-it-works-architecture"
        aria-labelledby="how-it-works-architecture-title"
      >
        <h2 className={styles.sectionTitle} id="how-it-works-architecture-title">
          System architecture
        </h2>
        <ArchitectureDiagram />
        <div className={styles.annotations} id="how-it-works-architecture-annotations">
          <Annotation id="annotation-cache-strategy" title="Cache strategy">
            Redirects use cache-aside: the redirect service checks Redis first and only touches
            PostgreSQL on a miss. 404s are cached too (negative caching, 60 seconds) so a flood of
            bad codes can&apos;t hammer the database. Positive entries expire at the smaller of 24
            hours and the link&apos;s remaining lifetime, so a cached redirect can never outlive its
            link.
          </Annotation>
          <Annotation id="annotation-database-indexing" title="Database indexing">
            A functional unique index on{" "}
            <code id="annotation-database-indexing-code-short">lower(short_code)</code> makes code
            lookups case-insensitive and fast. A composite{" "}
            <code id="annotation-database-indexing-code-feed">(created_at DESC, id DESC)</code> index
            powers keyset pagination on the dashboard, and a{" "}
            <code id="annotation-database-indexing-code-clicks">(link_id, clicked_at)</code> index
            backs the per-link analytics queries.
          </Annotation>
        </div>
      </section>

      <section
        className={styles.section}
        id="how-it-works-flows"
        aria-labelledby="how-it-works-flows-title"
      >
        <h2 className={styles.sectionTitle} id="how-it-works-flows-title">
          Request flows
        </h2>
        <SystemFlows />
        <div className={styles.annotations} id="how-it-works-flows-annotations">
          <Annotation id="annotation-redirect-flow" title="Redirect flow">
            Every short code is a single indexed lookup. A cache hit returns a 302 immediately; a
            miss falls back to PostgreSQL, warms the cache, and still returns in milliseconds. The
            click event is queued after the redirect, never before, so analytics can never slow a
            redirect down.
          </Annotation>
          <Annotation id="annotation-analytics-pipeline" title="Analytics pipeline">
            Click events land on a Redis Stream and are processed by a worker consumer group. The
            worker parses the user agent into device, browser, and OS, keeps only the referrer&apos;s
            domain, and stores no raw user agents or IP addresses. Unacknowledged events are retried
            and, after three attempts, moved to a dead-letter queue.
          </Annotation>
          <Annotation id="annotation-rate-limiting" title="Rate limiting">
            Link creation is capped per IP with fixed-window counters in Redis — 10 per minute and
            100 per day. Each check is a single increment with an expiry, so it adds no database
            load. Reads (the dashboard and redirects) are never throttled.
          </Annotation>
        </div>
      </section>

      <section
        className={styles.section}
        id="how-it-works-technology"
        aria-labelledby="how-it-works-technology-title"
      >
        <h2 className={styles.sectionTitle} id="how-it-works-technology-title">
          Technology choices
        </h2>
        <p className={styles.sectionLead} id="how-it-works-technology-lead">
          Each piece earns its place by solving a specific problem.
        </p>
        <TechBadgeGrid />
        <Annotation id="annotation-qr-generation" title="QR generation">
          QR codes are rendered on demand from the short URL with error-correction level M, as PNG or
          SVG. They are never stored — the image is deterministic per code, so it is cached at the
          edge with a long, immutable Cache-Control header instead.
        </Annotation>
      </section>

      <section
        className={styles.section}
        id="how-it-works-scaling"
        aria-labelledby="how-it-works-scaling-title"
      >
        <h2 className={styles.sectionTitle} id="how-it-works-scaling-title">
          Scaling story
        </h2>
        <ScalingStory />
      </section>

      <section
        className={styles.section}
        id="how-it-works-metrics"
        aria-labelledby="how-it-works-metrics-title"
      >
        <h2 className={styles.sectionTitle} id="how-it-works-metrics-title">
          Live operational metrics
        </h2>
        <LiveMetricsPanel />
      </section>
    </div>
  );
}
