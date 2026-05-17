import { useState } from "react";
import type { RecordingState } from "./types";
import ControlBar from "./components/ControlBar";
import TranscriptView from "./components/TranscriptView";
import { useWebSocket } from "./hooks/useWebSocket";
import { useAudioCapture } from "./hooks/useAudioCapture";
import { useTranscript } from "./hooks/useTranscript";
import { useAutoScroll } from "./hooks/useAutoScroll";
import styles from "./App.module.css";

export default function App() {
  const [recState, setRecState] = useState<RecordingState>("idle");

  const { committed, pending, handleMessage } = useTranscript();
  const { connect, disconnect, send } = useWebSocket(handleMessage);
  const { start, stop } = useAudioCapture(send);
  const { scrollRef, isAtBottom, scrollToBottom } = useAutoScroll([
    committed.length,
    pending,
  ]);

  const handleToggle = () => {
    if (recState === "idle") {
      connect();
      start()
        .then(() => setRecState("recording"))
        .catch(() => disconnect());
    } else {
      stop();
      disconnect();
      setRecState("idle");
    }
  };

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <h1>Meeting Transcript</h1>
      </header>
      <div className={styles.transcriptWrapper}>
        <main
          className={styles.transcriptArea}
          ref={scrollRef as React.RefObject<HTMLElement>}
        >
          <TranscriptView committed={committed} pending={pending} />
        </main>
        {!isAtBottom && (
          <button className={styles.jumpButton} onClick={scrollToBottom}>
            ↓ 跳到底部
          </button>
        )}
      </div>
      <ControlBar state={recState} onToggle={handleToggle} />
    </div>
  );
}
