import { useState } from "react";
import type { RecordingState, Segment } from "./types";
import ControlBar from "./components/ControlBar";
import TranscriptView from "./components/TranscriptView";
import styles from "./App.module.css";

const MOCK_COMMITTED: Segment[] = [
  { id: "1", startedAt: 0.0, text: "好，我們來開始今天的會議。" },
  { id: "2", startedAt: 3.5, text: "首先討論 Q3 產品路線圖的規劃。" },
  { id: "3", startedAt: 8.2, text: "目標是完成 MVP 並在內部進行測試。" },
];
const MOCK_PENDING = "我們預計在下個月底...";

export default function App() {
  const [committed] = useState<Segment[]>(MOCK_COMMITTED);
  const [pending] = useState<string>(MOCK_PENDING);
  const [recState, setRecState] = useState<RecordingState>("idle");

  const handleToggle = () =>
    setRecState((s) => (s === "idle" ? "recording" : "idle"));

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <h1>Meeting Transcript</h1>
      </header>
      <main className={styles.transcriptArea}>
        <TranscriptView committed={committed} pending={pending} />
      </main>
      <ControlBar state={recState} onToggle={handleToggle} />
    </div>
  );
}
