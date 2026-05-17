import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { useAutoScroll } from "../hooks/useAutoScroll";

// ---------------------------------------------------------------------------
// Test wrapper component
// ---------------------------------------------------------------------------
function Scroller({ deps = [] as unknown[] }: { deps?: unknown[] }) {
  const { scrollRef, isAtBottom, scrollToBottom } = useAutoScroll(deps);
  return (
    <div style={{ position: "relative" }}>
      <div
        ref={scrollRef as React.RefObject<HTMLDivElement>}
        data-testid="scroller"
        style={{ overflow: "auto", height: "100px" }}
      />
      {!isAtBottom && (
        <button data-testid="jump" onClick={scrollToBottom}>
          跳到底部
        </button>
      )}
      <span data-testid="status">{isAtBottom ? "at-bottom" : "scrolled-up"}</span>
    </div>
  );
}

// Helper: set layout-related properties on the scroll element
function setScrollLayout(
  el: HTMLElement,
  { scrollHeight = 1000, clientHeight = 400, scrollTop = 0 } = {},
) {
  Object.defineProperty(el, "scrollHeight", { value: scrollHeight, configurable: true });
  Object.defineProperty(el, "clientHeight", { value: clientHeight, configurable: true });
  el.scrollTop = scrollTop;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe("useAutoScroll", () => {
  it("starts in auto-scroll mode (isAtBottom = true)", () => {
    render(<Scroller />);
    expect(screen.getByTestId("status").textContent).toBe("at-bottom");
    expect(screen.queryByTestId("jump")).not.toBeInTheDocument();
  });

  it("shows jump button when user scrolls away from bottom", () => {
    render(<Scroller />);
    const el = screen.getByTestId("scroller");
    setScrollLayout(el, { scrollHeight: 1000, clientHeight: 400, scrollTop: 0 });
    // 1000 - 0 - 400 = 600 > 50 → not at bottom

    act(() => el.dispatchEvent(new Event("scroll")));

    expect(screen.getByTestId("status").textContent).toBe("scrolled-up");
    expect(screen.getByTestId("jump")).toBeInTheDocument();
  });

  it("hides jump button when user scrolls back to bottom", () => {
    render(<Scroller />);
    const el = screen.getByTestId("scroller");

    // Scroll away
    setScrollLayout(el, { scrollHeight: 1000, clientHeight: 400, scrollTop: 0 });
    act(() => el.dispatchEvent(new Event("scroll")));
    expect(screen.getByTestId("jump")).toBeInTheDocument();

    // Scroll back (1000 - 560 - 400 = 40 < 50 → at bottom)
    setScrollLayout(el, { scrollTop: 560 });
    act(() => el.dispatchEvent(new Event("scroll")));

    expect(screen.queryByTestId("jump")).not.toBeInTheDocument();
    expect(screen.getByTestId("status").textContent).toBe("at-bottom");
  });

  it("clicking jump button restores auto-scroll", async () => {
    render(<Scroller />);
    const el = screen.getByTestId("scroller");
    el.scrollTo = vi.fn();

    setScrollLayout(el, { scrollHeight: 1000, clientHeight: 400, scrollTop: 0 });
    act(() => el.dispatchEvent(new Event("scroll")));
    expect(screen.getByTestId("jump")).toBeInTheDocument();

    await userEvent.click(screen.getByTestId("jump"));

    expect(el.scrollTo).toHaveBeenCalledWith({ top: 1000, behavior: "smooth" });
    expect(screen.queryByTestId("jump")).not.toBeInTheDocument();
  });

  it("auto-scrolls when deps change and isAtBottom is true", () => {
    const { rerender } = render(<Scroller deps={[0]} />);
    const el = screen.getByTestId("scroller");
    // At bottom (default) — simulate content growing
    Object.defineProperty(el, "scrollHeight", { value: 500, configurable: true });

    rerender(<Scroller deps={[1]} />);

    // scrollTop should be set to scrollHeight
    expect(el.scrollTop).toBe(500);
  });

  it("does not auto-scroll when user has scrolled up", () => {
    const { rerender } = render(<Scroller deps={[0]} />);
    const el = screen.getByTestId("scroller");

    // User scrolls away
    setScrollLayout(el, { scrollHeight: 1000, clientHeight: 400, scrollTop: 0 });
    act(() => el.dispatchEvent(new Event("scroll")));

    const scrollTopBefore = el.scrollTop;
    rerender(<Scroller deps={[1]} />); // content grows, but auto-scroll paused

    expect(el.scrollTop).toBe(scrollTopBefore);
  });
});
