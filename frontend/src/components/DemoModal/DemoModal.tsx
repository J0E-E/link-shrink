import { useEffect, useState } from "react";

import styles from "./DemoModal.module.css";

/**
 * Centered welcome modal shown on first load (TDD §5.10 public-demo disclosure). It
 * explains that LinkShrink is a portfolio piece built to showcase system design and
 * implementation, and warns plainly that links should not contain anything private.
 * Once the visitor dismisses it, it stays closed for the rest of the session.
 */
export default function DemoModal() {
  const [isOpen, setIsOpen] = useState(true);

  const close = () => setIsOpen(false);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        close();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }

  return (
    <div className={styles.overlay} id="demo-modal-overlay" onClick={close}>
      <div
        className={styles.modal}
        id="demo-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="demo-modal-title"
        aria-describedby="demo-modal-body"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          type="button"
          className={styles.close}
          id="demo-modal-close"
          aria-label="Dismiss system design demo notice"
          onClick={close}
        >
          <span className={styles.closeIcon} id="demo-modal-close-icon" aria-hidden="true">
            ✕
          </span>
        </button>

        <span className={styles.icon} id="demo-modal-icon" aria-hidden="true">
          ⚠
        </span>

        <h2 className={styles.title} id="demo-modal-title">
          System Design Demo
        </h2>

        <div className={styles.body} id="demo-modal-body">
          <p className={styles.paragraph} id="demo-modal-intro">
            LinkShrink is a portfolio project built to show off end-to-end system design and
            implementation. Think URL shortening, analytics, caching, and all the infrastructure
            humming along behind them.
          </p>
          <p className={styles.paragraph} id="demo-modal-visibility">
            Every shortened link, its destination, and its analytics are visible to anyone who
            wanders by. The data may also be wiped at any moment.
          </p>
          <p className={styles.warning} id="demo-modal-warning">
            Do not shorten private, sensitive, or confidential links.
          </p>
        </div>

        <button
          type="button"
          className={styles.acknowledge}
          id="demo-modal-acknowledge"
          onClick={close}
        >
          Got it
        </button>
      </div>
    </div>
  );
}
