import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ControlBar from "../components/ControlBar";

describe("ControlBar", () => {
  it('shows "開始錄音" when idle', () => {
    render(<ControlBar state="idle" onToggle={() => {}} />);
    expect(screen.getByRole("button", { name: "開始錄音" })).toBeInTheDocument();
  });

  it('shows "停止錄音" when recording', () => {
    render(<ControlBar state="recording" onToggle={() => {}} />);
    expect(screen.getByRole("button", { name: "停止錄音" })).toBeInTheDocument();
  });

  it("calls onToggle when button is clicked", async () => {
    const onToggle = vi.fn();
    render(<ControlBar state="idle" onToggle={onToggle} />);
    await userEvent.click(screen.getByRole("button"));
    expect(onToggle).toHaveBeenCalledOnce();
  });
});
