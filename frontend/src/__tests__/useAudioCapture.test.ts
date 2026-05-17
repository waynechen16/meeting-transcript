import { renderHook, act } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAudioCapture } from "../hooks/useAudioCapture";

// ---------------------------------------------------------------------------
// Mock the worklet URL import so Vite's ?url suffix doesn't fail in jsdom
// ---------------------------------------------------------------------------
vi.mock("../worklets/pcm-processor?url", () => ({
  default: "/mock-pcm-processor.js",
}));

// ---------------------------------------------------------------------------
// Mock browser audio APIs
// ---------------------------------------------------------------------------
const mockTrackStop = vi.fn();
const mockTrack = {
  stop: mockTrackStop,
  addEventListener: vi.fn((_event: string, cb: () => void) => {
    // expose so tests can trigger 'ended'
    (mockTrack as { _endedCb?: () => void })._endedCb = cb;
  }),
};

const mockStream = {
  getTracks: () => [mockTrack],
  getAudioTracks: () => [mockTrack],
};

const mockGetDisplayMedia = vi.fn().mockResolvedValue(mockStream);

const mockWorkletNodePort = { onmessage: null as ((ev: MessageEvent) => void) | null };
const mockWorkletNodeConnect = vi.fn();
const MockAudioWorkletNode = vi.fn(() => ({
  port: mockWorkletNodePort,
  connect: mockWorkletNodeConnect,
}));

const mockSourceConnect = vi.fn();
const mockSilenceConnect = vi.fn();
const mockSilenceGain = { gain: { value: 1 }, connect: mockSilenceConnect };
const mockAddModule = vi.fn().mockResolvedValue(undefined);
const mockClose = vi.fn();

class MockAudioContext {
  destination = {};
  audioWorklet = { addModule: mockAddModule };
  createMediaStreamSource = vi.fn(() => ({ connect: mockSourceConnect }));
  createGain = vi.fn(() => mockSilenceGain);
  close = mockClose;
}

beforeEach(() => {
  vi.clearAllMocks();
  Object.defineProperty(navigator, "mediaDevices", {
    value: { getDisplayMedia: mockGetDisplayMedia },
    writable: true,
    configurable: true,
  });
  vi.stubGlobal("AudioContext", MockAudioContext);
  vi.stubGlobal("AudioWorkletNode", MockAudioWorkletNode);
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe("useAudioCapture", () => {
  it("start() calls getDisplayMedia with audio:true", async () => {
    const { result } = renderHook(() => useAudioCapture(vi.fn()));
    await act(() => result.current.start());
    expect(mockGetDisplayMedia).toHaveBeenCalledWith({ audio: true });
  });

  it("start() loads the worklet module", async () => {
    const { result } = renderHook(() => useAudioCapture(vi.fn()));
    await act(() => result.current.start());
    expect(mockAddModule).toHaveBeenCalledWith("/mock-pcm-processor.js");
  });

  it("start() creates an AudioWorkletNode named pcm-processor", async () => {
    const { result } = renderHook(() => useAudioCapture(vi.fn()));
    await act(() => result.current.start());
    expect(MockAudioWorkletNode).toHaveBeenCalledWith(
      expect.any(MockAudioContext),
      "pcm-processor",
    );
  });

  it("worklet port messages are forwarded to send()", async () => {
    const send = vi.fn();
    const { result } = renderHook(() => useAudioCapture(send));
    await act(() => result.current.start());

    const buf = new ArrayBuffer(16);
    act(() => mockWorkletNodePort.onmessage!(new MessageEvent("message", { data: buf })));
    expect(send).toHaveBeenCalledWith(buf);
  });

  it("stop() stops all media tracks and closes AudioContext", async () => {
    const { result } = renderHook(() => useAudioCapture(vi.fn()));
    await act(() => result.current.start());
    act(() => result.current.stop());
    expect(mockTrackStop).toHaveBeenCalled();
    expect(mockClose).toHaveBeenCalled();
  });

  it("start() rejects and propagates when getDisplayMedia is denied", async () => {
    mockGetDisplayMedia.mockRejectedValueOnce(new DOMException("Permission denied"));
    const { result } = renderHook(() => useAudioCapture(vi.fn()));
    await expect(act(() => result.current.start())).rejects.toThrow("Permission denied");
  });
});
