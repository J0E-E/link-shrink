import Annotation from "../../components/Annotation/Annotation";
import ProcessTimeline from "./ProcessTimeline";
import ReviewSpotlight from "./ReviewSpotlight";
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
          Plot twist: I don&apos;t write any of the code. Not one line. My job is the thinking. I pin
          the design down on paper, slice it into bite-sized epics, and review every step so that by
          the time the agents start typing, I already know they&apos;ll deliver. Then I trust, but
          verify, with my own two eyes.
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
