import { SYSTEM_FLOWS } from "./flows";
import styles from "./SystemFlows.module.css";

/**
 * The redirect and analytics request flows, each rendered as a sequence of labeled steps
 * joined by arrows. Data lives in `flows.ts`.
 */
export default function SystemFlows() {
  return (
    <div className={styles.flows} id="system-flows">
      {SYSTEM_FLOWS.map((flow) => (
        <div className={styles.flow} id={flow.id} key={flow.id}>
          <h3 className={styles.flowTitle} id={`${flow.id}-title`}>
            {flow.title}
          </h3>
          <ol className={styles.steps} id={`${flow.id}-steps`}>
            {flow.steps.map((step, index) => (
              <li className={styles.step} id={`${flow.id}-step-${index}`} key={step}>
                <span className={styles.stepLabel} id={`${flow.id}-step-${index}-label`}>
                  {step}
                </span>
                {index < flow.steps.length - 1 && (
                  <span
                    className={styles.stepArrow}
                    id={`${flow.id}-step-${index}-arrow`}
                    aria-hidden="true"
                  >
                    →
                  </span>
                )}
              </li>
            ))}
          </ol>
        </div>
      ))}
    </div>
  );
}
