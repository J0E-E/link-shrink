/**
 * The technology badges shown on the How-It-Works page (BRD §9). Each badge names a
 * technology and explains why it was chosen and what problem it solves. Static content —
 * separate from the component so the component file only exports a component.
 */
export interface TechBadgeContent {
  id: string;
  label: string;
  explanation: string;
}

export const TECH_BADGES: TechBadgeContent[] = [
  {
    id: "tech-badge-postgresql",
    label: "PostgreSQL",
    explanation:
      "The source of truth for links and click events. A monotonic sequence feeds short-code generation, and functional and composite indexes keep lookups and the dashboard feed fast.",
  },
  {
    id: "tech-badge-redis",
    label: "Redis",
    explanation:
      "Plays two roles at once: a cache-aside store for redirects and the analytics queue (Redis Streams). One dependency covers two of the trickiest parts of the system.",
  },
  {
    id: "tech-badge-docker",
    label: "Docker",
    explanation:
      "The whole stack — Postgres, Redis, the API, redirect, and worker services, the frontend build, and Nginx — comes up with a single `docker compose up`.",
  },
  {
    id: "tech-badge-async",
    label: "Async Processing",
    explanation:
      "FastAPI async services and an asyncio worker loop keep every request non-blocking, so slow analytics work never holds up a redirect.",
  },
  {
    id: "tech-badge-event-queue",
    label: "Event Queue",
    explanation:
      "Redis Streams with a consumer group, acknowledgements, retries, and a dead-letter queue make click capture durable and at-least-once.",
  },
  {
    id: "tech-badge-rate-limiting",
    label: "Rate Limiting",
    explanation:
      "IP-based fixed-window counters in Redis (10 per minute, 100 per day) protect link creation from abuse without a database round-trip.",
  },
  {
    id: "tech-badge-caching",
    label: "Caching",
    explanation:
      "Cache-aside with negative caching for 404s; the redirect cache TTL is capped at the link's remaining lifetime, so a cached entry can never outlive its link.",
  },
  {
    id: "tech-badge-analytics-pipeline",
    label: "Analytics Pipeline",
    explanation:
      "The worker parses user agents into device, browser, and OS categories and extracts referrer domains — no raw user agents or IP addresses are ever stored.",
  },
];
