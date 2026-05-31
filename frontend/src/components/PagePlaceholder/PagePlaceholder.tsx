import type { ReactNode } from "react";

import styles from "./PagePlaceholder.module.css";

interface PagePlaceholderProps {
  pageId: string;
  titleId: string;
  bodyId: string;
  title: string;
  children: ReactNode;
}

/**
 * A minimal "coming soon" card used by routes whose real content arrives in a later
 * epic. Callers pass the page-level ids so every element still carries a unique id
 * per the project's HTML-id rule.
 */
export default function PagePlaceholder({
  pageId,
  titleId,
  bodyId,
  title,
  children,
}: PagePlaceholderProps) {
  return (
    <section className={styles.placeholder} id={pageId} aria-labelledby={titleId}>
      <h1 className={styles.title} id={titleId}>
        {title}
      </h1>
      <p className={styles.body} id={bodyId}>
        {children}
      </p>
    </section>
  );
}
