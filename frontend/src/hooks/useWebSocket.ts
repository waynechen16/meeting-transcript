import { useCallback, useRef, useState } from "react";

export type WsStatus = "disconnected" | "connecting" | "connected" | "error";

const WS_URL = "ws://localhost:8000/stream";

export function useWebSocket(onMessage?: (ev: MessageEvent) => void) {
  const [status, setStatus] = useState<WsStatus>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  // Keep onMessage fresh without re-creating the WS on every render
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (wsRef.current) return;
    setStatus("connecting");
    const ws = new WebSocket(WS_URL);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onopen = () => setStatus("connected");
    ws.onmessage = (ev) => onMessageRef.current?.(ev);
    ws.onerror = () => setStatus("error");
    ws.onclose = () => {
      wsRef.current = null;
      setStatus("disconnected");
    };
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  const send = useCallback((data: ArrayBuffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    }
  }, []);

  return { status, connect, disconnect, send };
}
