import styles from "./TechBadge.module.css";

interface TechBadgeProps {
  id: string;
  label: string;
  /** Optional decorative glyph shown before the label (e.g. the tech's mascot emoji). */
  icon?: string;
  /** Optional logo image shown before the label; takes precedence over the glyph. */
  iconImage?: string;
}

/**
 * A small technology pill (e.g. "PostgreSQL", "Redis"), optionally led by a decorative
 * icon — a logo image when one is given, otherwise an emoji glyph. Reused as a standalone
 * marker and inside the How-It-Works badge grid; styled after the dashboard link badge.
 */
export default function TechBadge({ id, label, icon, iconImage }: TechBadgeProps) {
  return (
    <span className={styles.badge} id={id}>
      {iconImage ? (
        <img
          className={styles.iconImage}
          id={`${id}-icon`}
          src={iconImage}
          alt=""
          aria-hidden="true"
        />
      ) : (
        icon && (
          <span className={styles.icon} id={`${id}-icon`} aria-hidden="true">
            {icon}
          </span>
        )
      )}
      {label}
    </span>
  );
}
