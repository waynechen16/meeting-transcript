import type { RecordingState } from "../types";
import styles from "./ControlBar.module.css";

type Props = {
  state: RecordingState;
  onToggle: () => void;
};

export default function ControlBar({ state, onToggle }: Props) {
  const isRecording = state === "recording";
  return (
    <div className={styles.bar}>
      <button
        className={isRecording ? styles.btnStop : styles.btnStart}
        onClick={onToggle}
      >
        {isRecording ? "停止錄音" : "開始錄音"}
      </button>
    </div>
  );
}
