import styles from "./TechBadge.module.css";

interface TechBadgeProps {
  id: string;
  label: string;
}

/**
 * A small technology pill (e.g. "PostgreSQL", "Redis"). Reused as a standalone marker and
 * inside the How-It-Works badge grid; styled after the dashboard link badge.
 */
export default function TechBadge({ id, label }: TechBadgeProps) {
  return (
    <span className={styles.badge} id={id}>
      {label}
    </span>
  );
}
