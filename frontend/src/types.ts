export type Segment = {
  id: string;        // UUID from server
  startedAt: number; // seconds from session start
  text: string;
};

export type RecordingState = "idle" | "recording";
