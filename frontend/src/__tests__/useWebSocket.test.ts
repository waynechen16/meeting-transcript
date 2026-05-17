import { renderHook, act } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useWebSocket } from "../hooks/useWebSocket";

// ---------------------------------------------------------------------------
// Mock WebSocket
// ---------------------------------------------------------------------------
class MockWebSocket {
  static readonly OPEN = 1;
  readyState = MockWebSocket.OPEN;
  binaryType = "";
  onopen: (() => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
  send = vi.fn();
  close = vi.fn(() => {
    this.onclose?.();
  });
}

let mockWs: MockWebSocket;

beforeEach(() => {
  mockWs = new MockWebSocket();
  const ctor = vi.fn(() => mockWs) as unknown as typeof WebSocket;
  // The hook reads WebSocket.OPEN (static constant = 1)
  (ctor as unknown as { OPEN: number }).OPEN = 1;
  vi.stubGlobal("WebSocket", ctor);
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe("useWebSocket", () => {
  it("starts disconnected", () => {
    const { result } = renderHook(() => useWebSocket());
    expect(result.current.status).toBe("disconnected");
  });

  it("connect() creates a WebSocket at the sidecar URL", () => {
    const { result } = renderHook(() => useWebSocket());
    act(() => result.current.connect());
    expect(WebSocket).toHaveBeenCalledWith("ws://localhost:8000/stream");
  });

  it("status becomes connected when socket opens", () => {
    const { result } = renderHook(() => useWebSocket());
    act(() => {
      result.current.connect();
      mockWs.onopen!();
    });
    expect(result.current.status).toBe("connected");
  });

  it("status becomes error on socket error", () => {
    const { result } = renderHook(() => useWebSocket());
    act(() => {
      result.current.connect();
      mockWs.onerror!();
    });
    expect(result.current.status).toBe("error");
  });

  it("send() forwards an ArrayBuffer when socket is open", () => {
    const { result } = renderHook(() => useWebSocket());
    act(() => {
      result.current.connect();
      mockWs.onopen!();
    });
    const buf = new ArrayBuffer(8);
    act(() => result.current.send(buf));
    expect(mockWs.send).toHaveBeenCalledWith(buf);
  });

  it("send() is a no-op when socket is not open", () => {
    mockWs.readyState = 0; // CONNECTING
    const { result } = renderHook(() => useWebSocket());
    act(() => result.current.connect());
    act(() => result.current.send(new ArrayBuffer(4)));
    expect(mockWs.send).not.toHaveBeenCalled();
  });

  it("disconnect() closes the socket", () => {
    const { result } = renderHook(() => useWebSocket());
    act(() => {
      result.current.connect();
      mockWs.onopen!();
    });
    act(() => result.current.disconnect());
    expect(mockWs.close).toHaveBeenCalled();
  });

  it("calls onMessage callback when a message arrives", () => {
    const onMessage = vi.fn();
    const { result } = renderHook(() => useWebSocket(onMessage));
    act(() => result.current.connect());
    const ev = new MessageEvent("message", { data: '{"type":"transcript"}' });
    act(() => mockWs.onmessage!(ev));
    expect(onMessage).toHaveBeenCalledWith(ev);
  });

  it("does not create a second WebSocket if already connected", () => {
    const { result } = renderHook(() => useWebSocket());
    act(() => {
      result.current.connect();
      result.current.connect(); // second call should be no-op
    });
    expect(WebSocket).toHaveBeenCalledTimes(1);
  });
});
