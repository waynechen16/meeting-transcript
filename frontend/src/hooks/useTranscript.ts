import { useCallback, useReducer } from "react";
import type { Segment } from "../types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
type TranscriptMsg = {
  type: "transcript";
  is_final: boolean;
  text: string;
  start_time: number;
  segment_id?: string;
};

type TranscriptState = {
  committed: Segment[];
  pending: string;
};

type Action =
  | { type: "INTERIM"; text: string }
  | { type: "FINAL"; segment: Segment }
  | { type: "RESET" };

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------
function reducer(state: TranscriptState, action: Action): TranscriptState {
  switch (action.type) {
    case "INTERIM":
      return { ...state, pending: action.text };
    case "FINAL":
      return { committed: [...state.committed, action.segment], pending: "" };
    case "RESET":
      return { committed: [], pending: "" };
  }
}

const INITIAL: TranscriptState = { committed: [], pending: "" };

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------
export function useTranscript() {
  const [state, dispatch] = useReducer(reducer, INITIAL);

  const handleMessage = useCallback((ev: MessageEvent) => {
    if (typeof ev.data !== "string") return;
    let msg: TranscriptMsg | { type: string };
    try {
      msg = JSON.parse(ev.data) as TranscriptMsg | { type: string };
    } catch {
      return;
    }
    if (msg.type !== "transcript") return;

    const t = msg as TranscriptMsg;
    if (t.is_final) {
      dispatch({
        type: "FINAL",
        segment: {
          id: t.segment_id ?? crypto.randomUUID(),
          startedAt: t.start_time,
          text: t.text,
        },
      });
    } else {
      dispatch({ type: "INTERIM", text: t.text });
    }
  }, []);

  const reset = useCallback(() => dispatch({ type: "RESET" }), []);

  return { committed: state.committed, pending: state.pending, handleMessage, reset };
}
