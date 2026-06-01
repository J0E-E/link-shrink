import Annotation from "../../components/Annotation/Annotation";
import ProcessTimeline from "./ProcessTimeline";
import ReviewSpotlight from "./ReviewSpotlight";
import ReviewAgents from "./ReviewAgents";
import styles from "./HowIWorkPage.module.css";

/**
 * The portfolio "how I work" page: the human process behind the product, as a companion to
 * "How LinkShrink works". It walks the AI-assisted pipeline (BRD, TDD, Epic Plan, agent
 * iteration) as a vertical timeline, then spotlights the review-and-tailoring loop that gets
 * the most attention. This very codebase is the proof: every commit is one reviewed epic.
 */
export default function HowIWorkPage() {
  return (
    <div className={styles.page} id="how-i-work-page">
      <header className={styles.intro} id="how-i-work-intro">
        <h1 className={styles.title} id="how-i-work-page-title">
          How I work
        </h1>
        <p className={styles.subtitle} id="how-i-work-subtitle">
          Now that cranking out code is something agents do in seconds, what&apos;s left is the
          part that always mattered: the design. I spend my time there, on the plan and the review,
          so the agents only ever fill in details I&apos;ve already decided. Nothing ships until
          I&apos;ve checked it against the plan.
        </p>
      </header>

      <section
        className={styles.section}
        id="how-i-work-process"
        aria-labelledby="how-i-work-process-title"
      >
        <h2 className={styles.sectionTitle} id="how-i-work-process-title">
          From idea to shipped
        </h2>
        <p className={styles.sectionLead} id="how-i-work-process-lead">
          A repeatable pipeline turns a fuzzy idea into working software, one written artifact at a
          time. Each stage feeds the next, so nothing important is left to chance or to the model&apos;s
          imagination.
        </p>
        <ProcessTimeline />
      </section>

      <section
        className={styles.section}
        id="how-i-work-review"
        aria-labelledby="how-i-work-review-title"
      >
        <h2 className={styles.sectionTitle} id="how-i-work-review-title">
          Where the real work happens
        </h2>
        <ReviewSpotlight />
      </section>

      <section
        className={styles.section}
        id="how-i-work-agents"
        aria-labelledby="how-i-work-agents-title"
      >
        <h2 className={styles.sectionTitle} id="how-i-work-agents-title">
          How the review is split across agents
        </h2>
        <p className={styles.sectionLead} id="how-i-work-agents-lead">
          One review, many sets of eyes. The work is divided so each agent owns a single lens and
          looks for nothing else, which is exactly what makes the pass thorough.
        </p>
        <ReviewAgents />
      </section>

      <Annotation id="how-i-work-annotation" title="This site is the receipts" headingLevel={2}>
        LinkShrink was built with exactly this process. Go peek at the git history: it reads as one
        commit per epic (every message starts with{" "}
        <code id="how-i-work-annotation-code">Epic N</code>), each one planned, reviewed, and only
        then committed. Not a single line typed by hand. Everything you see on the{" "}
        <a id="how-i-work-annotation-link" href="/how-it-works">
          How It Works
        </a>{" "}
        page is whatever popped out the other end.
      </Annotation>
    </div>
  );
}
