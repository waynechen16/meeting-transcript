import { useCallback, useRef } from "react";
import workletUrl from "../worklets/pcm-processor?url";

export function useAudioCapture(send: (data: ArrayBuffer) => void) {
  // Keep send reference fresh without invalidating callbacks
  const sendRef = useRef(send);
  sendRef.current = send;

  const ctxRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    ctxRef.current?.close();
    ctxRef.current = null;
  }, []);

  const start = useCallback(async () => {
    const stream = await navigator.mediaDevices.getDisplayMedia({
      audio: true,
    });
    streamRef.current = stream;

    // If the user ends the share from browser UI, clean up
    stream.getAudioTracks()[0]?.addEventListener("ended", stop);

    const ctx = new AudioContext();
    ctxRef.current = ctx;

    await ctx.audioWorklet.addModule(workletUrl);

    const source = ctx.createMediaStreamSource(stream);
    const workletNode = new AudioWorkletNode(ctx, "pcm-processor");

    workletNode.port.onmessage = (ev: MessageEvent<ArrayBuffer>) => {
      sendRef.current(ev.data);
    };

    // Route through a muted gain node so the audio graph stays active
    // without playing captured audio back to the user
    const silence = ctx.createGain();
    silence.gain.value = 0;
    source.connect(workletNode);
    workletNode.connect(silence);
    silence.connect(ctx.destination);
  }, [stop]);

  return { start, stop };
}
