/**
 * The technology badges shown on the How-It-Works page (BRD §9). Each badge names a
 * technology and explains why it was chosen and what problem it solves. Static content —
 * separate from the component so the component file only exports a component.
 */
export interface TechBadgeContent {
  id: string;
  label: string;
  /** A small glyph shown before the label — the tech's mascot or an idea that represents it. */
  icon: string;
  /** Optional logo image (served from `public/images/`) shown instead of the glyph. */
  iconImage?: string;
  explanation: string;
}

export const TECH_BADGES: TechBadgeContent[] = [
  {
    id: "tech-badge-postgresql",
    label: "PostgreSQL",
    icon: "🐘",
    iconImage: "/images/postgresql.png",
    explanation:
      "The source of truth for links and click events. A monotonic sequence feeds short-code generation, and functional and composite indexes keep lookups and the dashboard feed fast.",
  },
  {
    id: "tech-badge-redis",
    label: "Redis",
    icon: "⚡",
    iconImage: "/images/redis.svg",
    explanation:
      "Plays two roles at once: a cache-aside store for redirects and the analytics queue (Redis Streams). One dependency covers two of the trickiest parts of the system.",
  },
  {
    id: "tech-badge-docker",
    label: "Docker",
    icon: "🐳",
    iconImage: "/images/docker.svg",
    explanation:
      "The whole stack (Postgres, Redis, the API, redirect, and worker services, the frontend build, and Nginx) comes up with a single `docker compose up`. No fuss.",
  },
  {
    id: "tech-badge-async",
    label: "Async Processing",
    icon: "🔀",
    explanation:
      "FastAPI async services and an asyncio worker loop keep every request non-blocking, so slow analytics work never holds up a redirect.",
  },
  {
    id: "tech-badge-event-queue",
    label: "Event Queue",
    icon: "📨",
    explanation:
      "Redis Streams with a consumer group, acknowledgements, retries, and a dead-letter queue make click capture durable and at-least-once.",
  },
  {
    id: "tech-badge-rate-limiting",
    label: "Rate Limiting",
    icon: "🚦",
    explanation:
      "IP-based fixed-window counters in Redis (10 per minute, 100 per day) protect link creation from abuse without a database round-trip.",
  },
  {
    id: "tech-badge-caching",
    label: "Caching",
    icon: "🗄️",
    explanation:
      "Cache-aside with negative caching for 404s; the redirect cache TTL is capped at the link's remaining lifetime, so a cached entry can never outlive its link.",
  },
  {
    id: "tech-badge-analytics-pipeline",
    label: "Analytics Pipeline",
    icon: "📊",
    explanation:
      "The worker parses user agents into device, browser, and OS categories and extracts referrer domains. No raw user agents or IP addresses are ever stored.",
  },
];
