import { useEducationalMode } from "../../../education/EducationalModeContext";
import styles from "./EducationalModeToggle.module.css";

/**
 * The header switch that turns Educational Mode on and off site-wide. It is an on/off
 * toggle, so it uses `aria-pressed` (not `aria-expanded`). The visible label is the
 * accessible name; on small screens it is hidden visually (not removed) so the button
 * keeps its name while collapsing to just the icon to save header space.
 */
export default function EducationalModeToggle() {
  const { isEducationalModeOn, toggleEducationalMode } = useEducationalMode();

  const toggleClassName = isEducationalModeOn
    ? `${styles.toggle} ${styles.toggleOn}`
    : styles.toggle;

  return (
    <button
      type="button"
      className={toggleClassName}
      id="educational-mode-toggle"
      aria-pressed={isEducationalModeOn}
      onClick={toggleEducationalMode}
    >
      <span className={styles.icon} id="educational-mode-toggle-icon" aria-hidden="true">
        🎓
      </span>
      <span className={styles.label} id="educational-mode-toggle-label">
        Educational Mode
      </span>
      <span className={styles.switch} id="educational-mode-toggle-switch" aria-hidden="true">
        <span className={styles.switchThumb} id="educational-mode-toggle-thumb" />
      </span>
    </button>
  );
}
