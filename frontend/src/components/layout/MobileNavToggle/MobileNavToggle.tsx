import styles from "./MobileNavToggle.module.css";

interface MobileNavToggleProps {
  isOpen: boolean;
  onToggle: () => void;
  controlsId: string;
}

/**
 * The hamburger button that opens and closes the navigation on small screens. It is
 * hidden on desktop via CSS. `aria-controls` points at the nav and `aria-expanded`
 * reflects the open state so assistive tech announces the menu correctly.
 */
export default function MobileNavToggle({ isOpen, onToggle, controlsId }: MobileNavToggleProps) {
  return (
    <button
      type="button"
      className={styles.toggle}
      id="mobile-nav-toggle"
      aria-controls={controlsId}
      aria-expanded={isOpen}
      aria-label={isOpen ? "Close navigation menu" : "Open navigation menu"}
      onClick={onToggle}
    >
      <span className={styles.toggleIcon} id="mobile-nav-toggle-icon" aria-hidden="true">
        {isOpen ? "✕" : "☰"}
      </span>
    </button>
  );
}
