/**
 * The two request flows shown on the How-It-Works page (BRD §9.2–9.3). Static content,
 * kept separate from the component so the component file only exports a component.
 */
export interface FlowContent {
  id: string;
  title: string;
  steps: string[];
}

export const SYSTEM_FLOWS: FlowContent[] = [
  {
    id: "redirect-flow",
    title: "Redirect flow",
    steps: ["User", "Reverse Proxy", "Redirect Service", "Cache", "Database"],
  },
  {
    id: "analytics-flow",
    title: "Analytics flow",
    steps: ["Redirect", "Queue", "Worker", "Database"],
  },
];
