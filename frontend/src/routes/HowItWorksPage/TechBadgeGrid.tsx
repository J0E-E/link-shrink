import TechBadge from "../../components/TechBadge/TechBadge";
import { TECH_BADGES } from "./techBadges";
import styles from "./TechBadgeGrid.module.css";

/**
 * The technology badge grid: each badge pill paired with a one-line "why we chose it"
 * explanation. Content lives in `techBadges.ts`.
 */
export default function TechBadgeGrid() {
  return (
    <ul className={styles.grid} id="tech-badge-grid">
      {TECH_BADGES.map((badge) => (
        <li className={styles.card} id={`${badge.id}-card`} key={badge.id}>
          <TechBadge
            id={badge.id}
            label={badge.label}
            icon={badge.icon}
            iconImage={badge.iconImage}
          />
          <p className={styles.explanation} id={`${badge.id}-explanation`}>
            {badge.explanation}
          </p>
        </li>
      ))}
    </ul>
  );
}
