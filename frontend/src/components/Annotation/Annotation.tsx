import type { ReactNode } from "react";

import styles from "./Annotation.module.css";

interface AnnotationProps {
  id: string;
  title: string;
  /**
   * Heading level for the title, so the callout fits its surroundings without skipping a
   * level: `3` under a section `<h2>` (How-It-Works), `2` when it sits directly under a
   * page `<h1>` (Home, Dashboard, analytics). Defaults to `3`.
   */
  headingLevel?: 2 | 3;
  children: ReactNode;
}

/**
 * An always-visible system design callout. This is the single building block for every
 * architecture annotation in the app — dropping one anywhere adds explanatory context about
 * the choices behind that piece of the system.
 */
export default function Annotation({ id, title, headingLevel = 3, children }: AnnotationProps) {
  const TitleHeading = headingLevel === 2 ? "h2" : "h3";

  return (
    <aside className={styles.annotation} id={id} role="note" aria-labelledby={`${id}-title`}>
      <span className={styles.label} id={`${id}-label`} aria-hidden="true">
        🎓 System Design Note
      </span>
      <TitleHeading className={styles.title} id={`${id}-title`}>
        {title}
      </TitleHeading>
      <div className={styles.body} id={`${id}-body`}>
        {children}
      </div>
    </aside>
  );
}
