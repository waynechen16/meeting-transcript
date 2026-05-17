import { useCallback, useEffect, useRef, useState } from "react";

const BOTTOM_THRESHOLD_PX = 50;

/**
 * Auto-scrolls a container to the bottom whenever `deps` change, unless the
 * user has manually scrolled up.  Resumes auto-scroll when the user scrolls
 * back within BOTTOM_THRESHOLD_PX of the bottom.
 *
 * @param deps  Values that trigger a scroll check (e.g. [committed.length, pending])
 * @returns     scrollRef — attach to the scrollable element
 *              isAtBottom — false when the user has scrolled up
 *              scrollToBottom — call to jump to bottom and resume auto-scroll
 */
export function useAutoScroll(deps: readonly unknown[]) {
  const scrollRef = useRef<HTMLElement | null>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  // Detect when the user scrolls away from / back to the bottom
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;

    const onScroll = () => {
      const atBottom =
        el.scrollHeight - el.scrollTop - el.clientHeight < BOTTOM_THRESHOLD_PX;
      setIsAtBottom(atBottom);
    };

    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
    // scrollRef.current is stable after mount — empty deps is correct
  }, []);

  // Instantly jump to bottom whenever content grows and auto-scroll is active
  useEffect(() => {
    if (isAtBottom && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
    // Dynamic deps — intentional spread
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAtBottom, ...deps]);

  // Smoothly scroll to bottom and re-enable auto-scroll
  const scrollToBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    setIsAtBottom(true);
  }, []);

  return { scrollRef, isAtBottom, scrollToBottom };
}
