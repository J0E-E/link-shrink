import styles from "./ReviewAgents.module.css";

/**
 * Each review fans out into a panel of focused agents. Every one is handed the same diff and the
 * epic's plan, then sent hunting for a single class of problem in parallel — and only that one.
 * Their findings merge back into one PR-style report.
 */
const REVIEW_AGENTS = [
  {
    id: "review-agent-deliverables",
    title: "Deliverables met",
    detail: "Every planned task is satisfied, and nothing got quietly built differently than planned.",
  },
  {
    id: "review-agent-breaking",
    title: "No breaking changes",
    detail: "The existing public surface (routes, signatures, config keys, schema) stays intact.",
  },
  {
    id: "review-agent-correctness",
    title: "Correctness & security",
    detail: "Logic, edge cases, null handling, concurrency, injection, and leaked secrets.",
  },
  {
    id: "review-agent-architecture",
    title: "Architecture",
    detail: "Single responsibility, clear module boundaries, minimal coupling, and reuse.",
  },
  {
    id: "review-agent-clean",
    title: "Clean code",
    detail: "Readability, naming, dead code, swallowed errors, and over-engineering.",
  },
  {
    id: "review-agent-conventions",
    title: "Conventions & lint",
    detail: "The project's own rules in CLAUDE.md: naming, HTML IDs, the design guide.",
  },
  {
    id: "review-agent-tests",
    title: "Tests",
    detail: "Coverage for each verification step, with the suite actually run and passing.",
  },
];

/**
 * Explains how a single review is split across a fleet of parallel agents, each owning one lens.
 * The grid spells out the lenses; the findings from every agent merge into one report I read
 * top to bottom.
 */
export default function ReviewAgents() {
  return (
    <div className={styles.agents} id="review-agents">
      <p className={styles.lead} id="review-agents-lead">
        A review isn&apos;t one pass. It fans out into a panel of agents working at once. Each gets the
        same diff and the epic&apos;s plan, then hunts for a single class of problem and reports back{" "}
        <code id="review-agents-format">path:line - issue - fix</code>. No praise, no filler. Their
        findings merge into one report I read top to bottom.
      </p>

      <ul className={styles.grid} id="review-agents-grid">
        {REVIEW_AGENTS.map((agent) => (
          <li className={styles.agent} id={agent.id} key={agent.id}>
            <h3 className={styles.agentTitle} id={`${agent.id}-title`}>
              {agent.title}
            </h3>
            <p className={styles.agentDetail} id={`${agent.id}-detail`}>
              {agent.detail}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
