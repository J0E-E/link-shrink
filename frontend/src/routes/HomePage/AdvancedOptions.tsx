import { EXPIRY_OPTIONS } from "./expiry";
import styles from "./AdvancedOptions.module.css";

interface AdvancedOptionsProps {
  isOpen: boolean;
  onToggle: () => void;
  alias: string;
  onAliasChange: (alias: string) => void;
  ttlSeconds: number;
  onTtlSecondsChange: (ttlSeconds: number) => void;
  aliasError: string | null;
  isDisabled: boolean;
}

/**
 * The collapsible "Advanced options" section: an optional custom alias and a link-expiry
 * selector. Kept behind a toggle so the URL field stays the primary focus of the page.
 * The toggle wires `aria-controls`/`aria-expanded` to the options region.
 */
export default function AdvancedOptions({
  isOpen,
  onToggle,
  alias,
  onAliasChange,
  ttlSeconds,
  onTtlSecondsChange,
  aliasError,
  isDisabled,
}: AdvancedOptionsProps) {
  return (
    <div className={styles.advanced} id="advanced-options">
      <button
        type="button"
        className={styles.toggle}
        id="advanced-options-toggle"
        aria-controls="advanced-options-panel"
        aria-expanded={isOpen}
        onClick={onToggle}
      >
        <span className={styles.toggleIcon} id="advanced-options-toggle-icon" aria-hidden="true">
          {isOpen ? "▾" : "▸"}
        </span>
        <span className={styles.toggleLabel} id="advanced-options-toggle-label">
          Advanced options
        </span>
      </button>

      {isOpen && (
        <div className={styles.panel} id="advanced-options-panel">
          <div className={styles.field} id="alias-field">
            <label className={styles.label} htmlFor="alias-input" id="alias-label">
              Custom alias <span className={styles.optional} id="alias-optional">(optional)</span>
            </label>
            <input
              className={styles.input}
              id="alias-input"
              type="text"
              inputMode="text"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              placeholder="my-link"
              value={alias}
              disabled={isDisabled}
              aria-invalid={aliasError ? true : undefined}
              aria-describedby={aliasError ? "alias-error" : "alias-hint"}
              onChange={(event) => onAliasChange(event.target.value)}
            />
            {aliasError ? (
              <p className={styles.error} id="alias-error" role="alert">
                {aliasError}
              </p>
            ) : (
              <p className={styles.hint} id="alias-hint">
                3 to 32 characters: lowercase letters, numbers, and hyphens.
              </p>
            )}
          </div>

          <div className={styles.field} id="expiry-field">
            <label className={styles.label} htmlFor="expiry-select" id="expiry-label">
              Link expires after
            </label>
            <select
              className={styles.select}
              id="expiry-select"
              value={ttlSeconds}
              disabled={isDisabled}
              onChange={(event) => onTtlSecondsChange(Number(event.target.value))}
            >
              {EXPIRY_OPTIONS.map((option) => (
                <option
                  key={option.seconds}
                  id={`expiry-option-${option.seconds}`}
                  value={option.seconds}
                >
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
  );
}
