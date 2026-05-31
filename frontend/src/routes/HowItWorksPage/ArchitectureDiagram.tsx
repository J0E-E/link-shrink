import styles from "./ArchitectureDiagram.module.css";

/**
 * A styled box diagram of the system: the proxy fans out to the API and redirect services,
 * both backed by PostgreSQL and Redis, with the worker draining the Redis analytics queue
 * into PostgreSQL. The connectors are decorative; the caption carries the real description.
 */
export default function ArchitectureDiagram() {
  return (
    <div className={styles.diagram} id="architecture-diagram">
      <div className={styles.tier} id="architecture-tier-proxy">
        <div className={`${styles.node} ${styles.nodeAccent}`} id="architecture-node-nginx">
          <span className={styles.nodeTitle} id="architecture-node-nginx-title">
            Nginx
          </span>
          <span className={styles.nodeSubtitle} id="architecture-node-nginx-subtitle">
            Reverse proxy &amp; TLS
          </span>
        </div>
      </div>

      <div className={styles.connector} id="architecture-connector-proxy" aria-hidden="true" />

      <div className={styles.tier} id="architecture-tier-services">
        <div className={styles.node} id="architecture-node-api">
          <span className={styles.nodeTitle} id="architecture-node-api-title">
            API Service
          </span>
          <span className={styles.nodeSubtitle} id="architecture-node-api-subtitle">
            Create links, dashboard, analytics, QR
          </span>
        </div>
        <div className={styles.node} id="architecture-node-redirect">
          <span className={styles.nodeTitle} id="architecture-node-redirect-title">
            Redirect Service
          </span>
          <span className={styles.nodeSubtitle} id="architecture-node-redirect-subtitle">
            Resolve short codes → 302
          </span>
        </div>
      </div>

      <div className={styles.connector} id="architecture-connector-services" aria-hidden="true" />

      <div className={styles.tier} id="architecture-tier-stores">
        <div className={styles.node} id="architecture-node-postgres">
          <span className={styles.nodeTitle} id="architecture-node-postgres-title">
            PostgreSQL
          </span>
          <span className={styles.nodeSubtitle} id="architecture-node-postgres-subtitle">
            Links &amp; click events
          </span>
        </div>
        <div className={styles.node} id="architecture-node-redis">
          <span className={styles.nodeTitle} id="architecture-node-redis-title">
            Redis
          </span>
          <span className={styles.nodeSubtitle} id="architecture-node-redis-subtitle">
            Cache &amp; analytics queue
          </span>
        </div>
      </div>

      <div className={styles.connector} id="architecture-connector-worker" aria-hidden="true" />

      <div className={styles.tier} id="architecture-tier-worker">
        <div className={styles.node} id="architecture-node-worker">
          <span className={styles.nodeTitle} id="architecture-node-worker-title">
            Worker Service
          </span>
          <span className={styles.nodeSubtitle} id="architecture-node-worker-subtitle">
            Drains the click queue → PostgreSQL
          </span>
        </div>
      </div>

      <p className={styles.caption} id="architecture-diagram-caption">
        The API and redirect services are independent entry points behind the proxy. The API
        reads and writes PostgreSQL and reads Redis (cache invalidation, live metrics). The
        redirect service reads Redis (cache) and PostgreSQL (on a miss) and writes click events
        onto the Redis queue. The worker consumes that queue and writes the derived analytics
        back to PostgreSQL.
      </p>
    </div>
  );
}
