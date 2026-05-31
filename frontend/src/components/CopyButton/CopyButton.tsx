import { useCallback, useEffect, useRef, useState } from "react";

import styles from "./CopyButton.module.css";

interface CopyButtonProps {
  /** The text to copy (the short URL). */
  value: string;
  /** Element id stem, so the button stays unique on whichever page renders it. */
  elementId?: string;
}

/**
 * Copies the short URL to the clipboard and flips to a green "Copied!" state for a couple
 * of seconds. Falls back to a hidden textarea + `document.execCommand` when the async
 * Clipboard API is unavailable (older browsers or non-secure contexts). Shared by the Home
 * result card and the per-link analytics header.
 */
export default function CopyButton({ value, elementId = "result-copy-button" }: CopyButtonProps) {
  const [didCopy, setDidCopy] = useState(false);
  const revertTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearRevertTimer = useCallback(() => {
    if (revertTimer.current !== null) {
      clearTimeout(revertTimer.current);
      revertTimer.current = null;
    }
  }, []);

  const copyValue = useCallback(async () => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
      } else {
        copyWithFallback(value);
      }
      setDidCopy(true);
      clearRevertTimer();
      revertTimer.current = setTimeout(() => setDidCopy(false), 2000);
    } catch {
      // If copying fails the user can still select the text manually; leave the idle state.
      setDidCopy(false);
    }
  }, [value, clearRevertTimer]);

  useEffect(() => clearRevertTimer, [clearRevertTimer]);

  return (
    <button
      type="button"
      className={didCopy ? `${styles.button} ${styles.copied}` : styles.button}
      id={elementId}
      aria-live="polite"
      onClick={copyValue}
    >
      <span className={styles.icon} id={`${elementId}-icon`} aria-hidden="true">
        {didCopy ? "✓" : "⧉"}
      </span>
      <span className={styles.label} id={`${elementId}-label`}>
        {didCopy ? "Copied!" : "Copy"}
      </span>
    </button>
  );
}

/** Legacy clipboard path for browsers without the async Clipboard API. */
function copyWithFallback(value: string) {
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "absolute";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
}
