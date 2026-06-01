import styles from "./ReviewSpotlight.module.css";

/** The repeating loop most of the effort goes into, shown as a cycling visual. */
const REVIEW_PHASES = [
  { id: "review-phase-review", label: "Review", icon: "🔍" },
  { id: "review-phase-tailor", label: "Tailor", icon: "✏️" },
  { id: "review-phase-rerun", label: "Re-run", icon: "🔁" },
];

/** What every epic's code review actually checks before it's allowed to merge. */
const REVIEW_CHECKS = [
  {
    id: "review-check-deliverables",
    title: "Deliverables met",
    detail: "Every planned task is satisfied, and nothing got quietly built differently.",
  },
  {
    id: "review-check-correctness",
    title: "Correctness & security",
    detail: "Logic, edge cases, null handling, concurrency, injection, and leaked secrets.",
  },
  {
    id: "review-check-architecture",
    title: "Architecture & conventions",
    detail: "Module boundaries, coupling, naming, and the project's own rules in CLAUDE.md.",
  },
  {
    id: "review-check-tests",
    title: "Tests",
    detail: "Coverage for each verification step, with the suite actually passing.",
  },
];

/**
 * The highlighted closing section: the part of the process that gets the most attention isn't
 * writing code, it's reviewing and tailoring what the agents produce. A small looping visual
 * cycles Review → Tailor → Re-run, and the grid spells out what every review checks. The loop
 * animation pauses for users who prefer reduced motion.
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
            style={{ animationDelay: `${index * 1.5}s` }}
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

      <ul className={styles.checks} id="review-spotlight-checks">
        {REVIEW_CHECKS.map((check) => (
          <li className={styles.check} id={check.id} key={check.id}>
            <h3 className={styles.checkTitle} id={`${check.id}-title`}>
              {check.title}
            </h3>
            <p className={styles.checkDetail} id={`${check.id}-detail`}>
              {check.detail}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
