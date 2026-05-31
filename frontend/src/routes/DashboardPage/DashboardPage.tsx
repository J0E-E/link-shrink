import { Link } from "react-router-dom";

import Annotation from "../../components/Annotation/Annotation";
import LinkList from "./LinkList";
import { useLinkList } from "./useLinkList";
import styles from "./DashboardPage.module.css";

/**
 * The public dashboard: a newest-first feed of shortened links with cursor-based
 * "Load more" paging. Each card links through to that link's analytics view.
 */
export default function DashboardPage() {
  const { status, items, hasMore, isLoadingMore, errorMessage, loadMoreError, loadMore, reload } =
    useLinkList();

  return (
    <section className={styles.page} id="dashboard-page" aria-labelledby="dashboard-page-title">
      <header className={styles.header} id="dashboard-header">
        <h1 className={styles.title} id="dashboard-page-title">
          Dashboard
        </h1>
        <p className={styles.subtitle} id="dashboard-subtitle">
          Every shortened link, newest first. Open one to see its analytics.
        </p>
      </header>

      <Annotation id="annotation-dashboard-pagination" title="Keyset pagination" headingLevel={2}>
        This feed pages with a keyset cursor, not an offset — each “Load more” carries the
        created-at and id of the last row and asks for everything after it. That stays fast no
        matter how deep you page, and never skips or repeats a row when new links appear mid-scroll.
      </Annotation>

      {status === "loading" && (
        <p className={styles.notice} id="dashboard-loading" role="status">
          Loading links…
        </p>
      )}

      {status === "error" && (
        <div className={styles.notice} id="dashboard-error" role="alert">
          <p className={styles.noticeText} id="dashboard-error-text">
            {errorMessage ?? "Something went wrong loading your links."}
          </p>
          <button
            type="button"
            className={styles.retryButton}
            id="dashboard-retry-button"
            onClick={() => void reload()}
          >
            Try again
          </button>
        </div>
      )}

      {status === "success" && items.length === 0 && (
        <div className={styles.notice} id="dashboard-empty">
          <p className={styles.noticeText} id="dashboard-empty-text">
            No links yet.
          </p>
          <Link className={styles.emptyLink} id="dashboard-empty-link" to="/">
            Shorten your first link
          </Link>
        </div>
      )}

      {status === "success" && items.length > 0 && (
        <div className={styles.feed} id="dashboard-feed">
          <LinkList links={items} />
          {loadMoreError && (
            <p className={styles.loadMoreError} id="dashboard-load-more-error" role="alert">
              {loadMoreError}
            </p>
          )}
          {hasMore && (
            <button
              type="button"
              className={styles.loadMoreButton}
              id="dashboard-load-more-button"
              disabled={isLoadingMore}
              onClick={() => void loadMore()}
            >
              {isLoadingMore ? "Loading…" : loadMoreError ? "Try again" : "Load more"}
            </button>
          )}
        </div>
      )}
    </section>
  );
}
