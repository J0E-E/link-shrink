import styles from "./ReviewSpotlight.module.css";

/** The repeating loop most of the effort goes into, shown as a cycling visual. */
const REVIEW_PHASES = [
  { id: "review-phase-review", label: "Review", icon: "🔍" },
  { id: "review-phase-tailor", label: "Tailor", icon: "✏️" },
  { id: "review-phase-execute", label: "Execute", icon: "⚙️" },
  { id: "review-phase-validate", label: "Validate", icon: "✅" },
  { id: "review-phase-repeat", label: "Rinse & repeat", icon: "🔁" },
];

/**
 * The highlighted closing section: the part of the process that gets the most attention isn't
 * writing code, it's reviewing and tailoring what the agents produce. A small looping visual
 * cycles Review → Tailor → Execute → Validate → Rinse & repeat, centered as the focal point. The
 * loop animation pauses for users who prefer reduced motion.
 */
export default function ReviewSpotlight() {
  return (
    <div className={styles.spotlight} id="review-spotlight">
      <div className={styles.intro} id="review-spotlight-intro">
        <span className={styles.eyebrow} id="review-spotlight-eyebrow">
          The part that matters most
        </span>
        <p className={styles.lead} id="review-spotlight-lead">
          Agents can crank out code in seconds. Getting the product <em>designed correctly</em> is
          the slow part, and that&apos;s the part I own. I never write the code myself, but I&apos;m
          obsessive about the plan and I review every change against it, over and over, until it&apos;s
          right. Trust the agents, then verify with my own eyes.
        </p>
      </div>

      <ol className={styles.loop} id="review-spotlight-loop" aria-label="The review loop">
        {REVIEW_PHASES.map((phase, index) => (
          <li
            className={styles.phase}
            id={phase.id}
            key={phase.id}
            style={{ animationDelay: `${index * 1.2}s` }}
          >
            <span className={styles.phaseIcon} id={`${phase.id}-icon`} aria-hidden="true">
              {phase.icon}
            </span>
            <span className={styles.phaseLabel} id={`${phase.id}-label`}>
              {phase.label}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
