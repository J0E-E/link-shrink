import ProcessStep from "./ProcessStep";
import { PROCESS_STEPS } from "./processSteps";
import styles from "./ProcessTimeline.module.css";

/**
 * The end-to-end process as a vertical timeline: BRD → TDD → Epic Plan → Agents. A gradient
 * connector line runs down behind the numbered markers; each `ProcessStep` reveals itself as
 * it scrolls into view. Content lives in `processSteps.ts`.
 */
export default function ProcessTimeline() {
  return (
    <ol className={styles.timeline} id="process-timeline">
      {PROCESS_STEPS.map((step, index) => (
        <ProcessStep key={step.id} step={step} index={index} />
      ))}
    </ol>
  );
}
