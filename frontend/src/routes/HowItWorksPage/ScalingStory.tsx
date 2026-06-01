import { SCALING_STAGES } from "./scalingStages";
import styles from "./ScalingStory.module.css";

/**
 * The scaling story: how the single-VM demo could grow out, one stage per piece of the
 * system. Content lives in `scalingStages.ts`.
 */
export default function ScalingStory() {
  return (
    <div className={styles.story} id="scaling-story">
      <p className={styles.intro} id="scaling-story-intro">
        LinkShrink is built as a scalable MVP: today the whole system runs on a single VM with one
        container per service. That&apos;s a deliberate starting point, not a ceiling. Each piece is
        built to scale out independently and move onto managed infrastructure when it needs to:
      </p>
      <ol className={styles.stages} id="scaling-story-stages">
        {SCALING_STAGES.map((stage) => (
          <li className={styles.stage} id={stage.id} key={stage.id}>
            <h3 className={styles.stageTitle} id={`${stage.id}-title`}>
              {stage.title}
            </h3>
            <p className={styles.stageDetail} id={`${stage.id}-detail`}>
              {stage.detail}
            </p>
          </li>
        ))}
      </ol>
    </div>
  );
}
