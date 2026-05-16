import type { Segment } from "../types";
import styles from "./TranscriptView.module.css";

function fmtTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

type Props = {
  committed: Segment[];
  pending: string;
};

export default function TranscriptView({ committed, pending }: Props) {
  return (
    <div className={styles.container}>
      {committed.map((seg) => (
        <div key={seg.id} className={styles.segment}>
          <span className={styles.timestamp}>[{fmtTime(seg.startedAt)}]</span>
          <span className={styles.text}>{seg.text}</span>
        </div>
      ))}

      {pending !== "" && (
        <div className={`${styles.segment} ${styles.pending}`}>
          <span className={styles.timestamp}>[…]</span>
          <span className={styles.text}>{pending}</span>
        </div>
      )}
    </div>
  );
}
