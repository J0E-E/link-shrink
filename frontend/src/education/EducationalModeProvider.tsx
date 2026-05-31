import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import {
  EDUCATIONAL_MODE_STORAGE_KEY,
  EducationalModeContext,
} from "./EducationalModeContext";

/** Read the saved preference, defaulting to off when storage is empty or blocked. */
function readStoredPreference(): boolean {
  try {
    return window.localStorage.getItem(EDUCATIONAL_MODE_STORAGE_KEY) === "on";
  } catch {
    // localStorage can throw in private mode or when blocked; default to off.
    return false;
  }
}

interface EducationalModeProviderProps {
  children: ReactNode;
}

/**
 * Provides the global Educational Mode state and persists it to `localStorage` so the
 * preference survives reloads. Wraps the whole app so the header toggle and every page
 * read the same state.
 */
export default function EducationalModeProvider({ children }: EducationalModeProviderProps) {
  const [isEducationalModeOn, setIsEducationalModeOn] = useState<boolean>(readStoredPreference);

  useEffect(() => {
    try {
      window.localStorage.setItem(
        EDUCATIONAL_MODE_STORAGE_KEY,
        isEducationalModeOn ? "on" : "off",
      );
    } catch {
      // Persisting is best-effort; ignore storage failures.
    }
  }, [isEducationalModeOn]);

  const toggleEducationalMode = useCallback(() => {
    setIsEducationalModeOn((wasOn) => !wasOn);
  }, []);

  const value = useMemo(
    () => ({ isEducationalModeOn, toggleEducationalMode }),
    [isEducationalModeOn, toggleEducationalMode],
  );

  return (
    <EducationalModeContext.Provider value={value}>{children}</EducationalModeContext.Provider>
  );
}
