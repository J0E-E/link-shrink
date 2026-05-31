import { createContext, useContext } from "react";

/**
 * Shared state for the global Educational Mode toggle. When on, the app reveals
 * architecture annotations (the `Annotation` component) on the How-It-Works page and a
 * few on Home/Dashboard. The provider lives in `EducationalModeProvider.tsx`; the context
 * object and the `useEducationalMode` hook live here so the provider file only exports a
 * component (keeps the React Fast Refresh lint rule happy).
 */

/** Key under which the on/off preference is persisted in `localStorage`. */
export const EDUCATIONAL_MODE_STORAGE_KEY = "linkshrink:educational-mode";

export interface EducationalModeValue {
  isEducationalModeOn: boolean;
  toggleEducationalMode: () => void;
}

export const EducationalModeContext = createContext<EducationalModeValue | null>(null);

/** Read the Educational Mode state. Throws if used outside the provider. */
export function useEducationalMode(): EducationalModeValue {
  const value = useContext(EducationalModeContext);
  if (value === null) {
    throw new Error("useEducationalMode must be used inside an EducationalModeProvider");
  }
  return value;
}
