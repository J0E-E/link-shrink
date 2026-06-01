/**
 * The four stages of the AI-assisted design/build process shown on the How-I-Work page.
 * Static content, kept separate so the component files only export components. Each step
 * names the artifact it produces (BRD, TDD, Epic Plan) or the loop it runs (Agents).
 */
export interface ProcessStep {
  id: string;
  stepNumber: string;
  artifact: string;
  icon: string;
  title: string;
  detail: string;
}

export const PROCESS_STEPS: ProcessStep[] = [
  {
    id: "process-step-brd",
    stepNumber: "01",
    artifact: "BRD",
    icon: "📝",
    title: "Pin down what we're actually building",
    detail:
      "It all kicks off with a Business Requirements Document, written with real specifics: concrete goals, explicit non-goals, hard constraints, and exactly how each feature should behave. No lazy one-line prompts. Garbage in, garbage out, so this is where the intent gets nailed down before a single line of code exists.",
  },
  {
    id: "process-step-tdd",
    stepNumber: "02",
    artifact: "TDD",
    icon: "📐",
    title: "Design it on paper first",
    detail:
      "The BRD grows up into a Technical Design Document: components, data model, interfaces, and the order things happen in. Every architectural choice goes into a decisions table (what I picked, what I passed on, and why), hashed out through a proper back and forth instead of letting the model wing it.",
  },
  {
    id: "process-step-epic-plan",
    stepNumber: "03",
    artifact: "Epic Plan",
    icon: "🧩",
    title: "Slice it into bite-sized epics",
    detail:
      "The design gets chopped into small, shippable epics. Each one delivers a coherent slice, can be tested on its own, fits in a single reviewable commit, and leaves the branch working when it lands. Dependencies are called out up front, so nothing gets built on sand.",
  },
  {
    id: "process-step-agents",
    stepNumber: "04",
    artifact: "Agents",
    icon: "🤖",
    title: "Let the agents cook",
    detail:
      "Here's where I play tech lead. Each epic runs through a tight loop: plan, implement, agent review, fix, complete, my own personal review and fixing any nits or findings, then commit. Think of the agents as a team of eager junior developers: they do their best work with small, tightly scoped tasks and a senior engineer watching closely. I never touch the keyboard, but nothing lands without my eyes on it.",
  },
];
