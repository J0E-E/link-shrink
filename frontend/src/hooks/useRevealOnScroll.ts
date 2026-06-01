import { useEffect, useRef, useState } from "react";
import type { RefObject } from "react";

/**
 * Reveals an element once it scrolls into view, for a one-shot fade/slide-in.
 *
 * Returns a `ref` to attach to the element and an `isVisible` flag that flips to `true`
 * the first time the element intersects the viewport, then stops observing (reveal-once,
 * so it never flickers back out). Users who prefer reduced motion start visible and the
 * observer is skipped entirely, so they see the content immediately with no animation.
 *
 * Generic and reusable site-wide, not specific to any one page.
 */
export function useRevealOnScroll<ElementType extends HTMLElement = HTMLElement>(
  threshold = 0.2,
): { ref: RefObject<ElementType>; isVisible: boolean } {
  const ref = useRef<ElementType>(null);
  const prefersReducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const [isVisible, setIsVisible] = useState(prefersReducedMotion);

  useEffect(() => {
    if (prefersReducedMotion) {
      return;
    }

    const element = ref.current;
    if (!element) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry?.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { threshold },
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, [prefersReducedMotion, threshold]);

  return { ref, isVisible };
}
