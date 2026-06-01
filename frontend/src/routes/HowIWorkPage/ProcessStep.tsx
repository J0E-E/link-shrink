import { useRevealOnScroll } from "../../hooks/useRevealOnScroll";
import type { ProcessStep as ProcessStepData } from "./processSteps";
import styles from "./ProcessStep.module.css";

interface ProcessStepProps {
  step: ProcessStepData;
  index: number;
}

/** Stagger each step's reveal slightly after the one above it. */
const STAGGER_MS = 110;

/**
 * One node on the process timeline: a numbered marker on the connector line and a card with
 * the artifact badge, title, and detail. The card fades and slides up the first time it
 * scrolls into view (`useRevealOnScroll`), with a delay derived from its position so the
 * steps cascade rather than appearing all at once.
 */
export default function ProcessStep({ step, index }: ProcessStepProps) {
  const { ref, isVisible } = useRevealOnScroll<HTMLLIElement>();
  const itemClassName = isVisible ? `${styles.step} ${styles.stepVisible}` : styles.step;

  return (
    <li
      className={itemClassName}
      id={step.id}
      ref={ref}
      style={{ transitionDelay: `${index * STAGGER_MS}ms` }}
    >
      <div className={styles.marker} id={`${step.id}-marker`} aria-hidden="true">
        <span className={styles.markerNumber} id={`${step.id}-marker-number`}>
          {step.stepNumber}
        </span>
      </div>

      <div className={styles.card} id={`${step.id}-card`}>
        <div className={styles.header} id={`${step.id}-header`}>
          <span className={styles.icon} id={`${step.id}-icon`} aria-hidden="true">
            {step.icon}
          </span>
          <span className={styles.badge} id={`${step.id}-badge`}>
            {step.artifact}
          </span>
        </div>
        <h3 className={styles.title} id={`${step.id}-title`}>
          {step.title}
        </h3>
        <p className={styles.detail} id={`${step.id}-detail`}>
          {step.detail}
        </p>
      </div>
    </li>
  );
}
