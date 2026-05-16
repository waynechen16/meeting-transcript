import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import TranscriptView from "../components/TranscriptView";
import type { Segment } from "../types";

const SEGMENTS: Segment[] = [
  { id: "1", startedAt: 0, text: "你好世界" },
  { id: "2", startedAt: 3, text: "今天天氣很好" },
];

describe("TranscriptView", () => {
  it("renders all committed segments", () => {
    render(<TranscriptView committed={SEGMENTS} pending="" />);
    expect(screen.getByText("你好世界")).toBeInTheDocument();
    expect(screen.getByText("今天天氣很好")).toBeInTheDocument();
  });

  it("formats timestamp as [MM:SS]", () => {
    render(<TranscriptView committed={SEGMENTS} pending="" />);
    expect(screen.getByText("[00:03]")).toBeInTheDocument();
  });

  it("renders pending text when non-empty", () => {
    render(<TranscriptView committed={[]} pending="正在說話..." />);
    expect(screen.getByText("正在說話...")).toBeInTheDocument();
  });

  it("shows […] timestamp for pending row", () => {
    render(<TranscriptView committed={[]} pending="正在說話..." />);
    expect(screen.getByText("[…]")).toBeInTheDocument();
  });

  it("renders no pending row when pending is empty", () => {
    render(<TranscriptView committed={SEGMENTS} pending="" />);
    expect(screen.queryByText("[…]")).not.toBeInTheDocument();
  });
});
