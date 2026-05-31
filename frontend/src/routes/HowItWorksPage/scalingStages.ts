/**
 * The scaling story shown on the How-It-Works page (BRD §9.4): how the single-VM demo
 * could evolve. Static content, kept separate so the component file only exports a
 * component.
 */
export interface ScalingStage {
  id: string;
  title: string;
  detail: string;
}

export const SCALING_STAGES: ScalingStage[] = [
  {
    id: "scaling-stage-redirect",
    title: "Multiple redirect instances",
    detail:
      "The redirect service is stateless and reads from the shared cache, so it scales horizontally behind the proxy to absorb traffic spikes.",
  },
  {
    id: "scaling-stage-workers",
    title: "Dedicated worker pools",
    detail:
      "The analytics consumer group lets you add workers that share the click stream, processing events in parallel without double-counting.",
  },
  {
    id: "scaling-stage-cache",
    title: "Distributed caching",
    detail:
      "Redis can move to a managed cluster, and immutable QR images to a CDN edge, once a single node is no longer enough.",
  },
  {
    id: "scaling-stage-orchestration",
    title: "Container orchestration",
    detail:
      "The Docker services map cleanly onto an orchestrator like Kubernetes for rolling deploys, health checks, and autoscaling.",
  },
];
