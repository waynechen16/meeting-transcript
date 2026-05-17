import { renderHook, act } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useTranscript } from "../hooks/useTranscript";

function makeMsg(data: object): MessageEvent {
  return new MessageEvent("message", { data: JSON.stringify(data) });
}

describe("useTranscript", () => {
  it("starts with empty committed and pending", () => {
    const { result } = renderHook(() => useTranscript());
    expect(result.current.committed).toEqual([]);
    expect(result.current.pending).toBe("");
  });

  it("interim message updates pending", () => {
    const { result } = renderHook(() => useTranscript());
    act(() =>
      result.current.handleMessage(
        makeMsg({ type: "transcript", is_final: false, text: "你好", start_time: 1.0 }),
      ),
    );
    expect(result.current.pending).toBe("你好");
    expect(result.current.committed).toHaveLength(0);
  });

  it("later interim replaces pending", () => {
    const { result } = renderHook(() => useTranscript());
    act(() =>
      result.current.handleMessage(
        makeMsg({ type: "transcript", is_final: false, text: "你好", start_time: 1.0 }),
      ),
    );
    act(() =>
      result.current.handleMessage(
        makeMsg({ type: "transcript", is_final: false, text: "你好世界", start_time: 1.0 }),
      ),
    );
    expect(result.current.pending).toBe("你好世界");
  });

  it("final message appends to committed and clears pending", () => {
    const { result } = renderHook(() => useTranscript());
    // Build up some pending first
    act(() =>
      result.current.handleMessage(
        makeMsg({ type: "transcript", is_final: false, text: "你好世界", start_time: 0 }),
      ),
    );
    act(() =>
      result.current.handleMessage(
        makeMsg({
          type: "transcript",
          is_final: true,
          text: "你好世界，",
          start_time: 0.5,
          end_time: 2.1,
          segment_id: "seg-001",
        }),
      ),
    );
    expect(result.current.committed).toHaveLength(1);
    expect(result.current.committed[0]).toEqual({
      id: "seg-001",
      startedAt: 0.5,
      text: "你好世界，",
    });
    expect(result.current.pending).toBe("");
  });

  it("multiple finals accumulate in order", () => {
    const { result } = renderHook(() => useTranscript());
    act(() =>
      result.current.handleMessage(
        makeMsg({ type: "transcript", is_final: true, text: "A", start_time: 0, segment_id: "1" }),
      ),
    );
    act(() =>
      result.current.handleMessage(
        makeMsg({ type: "transcript", is_final: true, text: "B", start_time: 1, segment_id: "2" }),
      ),
    );
    expect(result.current.committed.map((s) => s.text)).toEqual(["A", "B"]);
  });

  it("final without segment_id still creates a segment with a generated id", () => {
    const { result } = renderHook(() => useTranscript());
    act(() =>
      result.current.handleMessage(
        makeMsg({ type: "transcript", is_final: true, text: "X", start_time: 0 }),
      ),
    );
    expect(result.current.committed[0].id).toBeTruthy();
  });

  it("ignores non-transcript messages", () => {
    const { result } = renderHook(() => useTranscript());
    act(() =>
      result.current.handleMessage(
        makeMsg({ type: "error", message: "something went wrong" }),
      ),
    );
    expect(result.current.committed).toHaveLength(0);
    expect(result.current.pending).toBe("");
  });

  it("ignores binary (non-string) messages", () => {
    const { result } = renderHook(() => useTranscript());
    act(() =>
      result.current.handleMessage(
        new MessageEvent("message", { data: new ArrayBuffer(8) }),
      ),
    );
    expect(result.current.committed).toHaveLength(0);
  });

  it("ignores malformed JSON", () => {
    const { result } = renderHook(() => useTranscript());
    act(() =>
      result.current.handleMessage(
        new MessageEvent("message", { data: "{invalid json" }),
      ),
    );
    expect(result.current.committed).toHaveLength(0);
  });

  it("reset() clears committed and pending", () => {
    const { result } = renderHook(() => useTranscript());
    act(() =>
      result.current.handleMessage(
        makeMsg({ type: "transcript", is_final: true, text: "A", start_time: 0, segment_id: "1" }),
      ),
    );
    act(() => result.current.reset());
    expect(result.current.committed).toHaveLength(0);
    expect(result.current.pending).toBe("");
  });
});
