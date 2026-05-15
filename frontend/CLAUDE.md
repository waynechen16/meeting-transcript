# frontend/ — React UI

## What this is

React 18 + TypeScript + Vite frontend for the meeting transcript tool.
In **Phase 1** it communicates with the sidecar over WebSocket (ws://localhost:8000/stream).
In **Phase 2** it will be embedded inside Tauri and communicate via Tauri IPC events instead.

## Key responsibilities

- Capture browser/tab audio via `navigator.mediaDevices.getDisplayMedia({ audio: true })`
- Resample audio to 16 kHz mono Int16 PCM using `AudioWorklet` and push to sidecar over WebSocket
- Maintain two transcript state buckets:
  - `committed: Segment[]` — append-only array of `{ id, startedAt, text }` from `is_final=true` events
  - `pending: string` — current in-flight text from `is_final=false` events, replaced on each update
- Auto-scroll to bottom, pausing when the user scrolls up (resume when back at bottom)
- Long meetings: `committed` must be rendered with `react-virtuoso` once it exceeds ~200 segments

## State management

Start with `useState` / `useReducer` — do NOT reach for Zustand/Redux until local state becomes unmanageable.

## Styling

CSS Modules. No Tailwind, no styled-components. Keep it simple.

## WebSocket message protocol

**Client → Server**: binary `ArrayBuffer` of Int16 PCM samples (16 kHz mono).

**Server → Client**: JSON
```jsonc
// Interim result (will change)
{ "type": "transcript", "is_final": false, "text": "你好世界", "start_time": 1.2 }

// Final result (committed, append to store)
{ "type": "transcript", "is_final": true,  "text": "你好世界，", "start_time": 1.2, "end_time": 3.4, "segment_id": "uuid" }

// Error
{ "type": "error", "message": "..." }
```

## Key files (to be created per task)

| File | Task | Purpose |
|------|------|---------|
| `src/App.tsx` | P1-4 | Root component, layout |
| `src/hooks/useWebSocket.ts` | P1-5/6 | WS connection lifecycle |
| `src/hooks/useAudioCapture.ts` | P1-5 | getDisplayMedia + AudioWorklet |
| `src/hooks/useTranscript.ts` | P1-6 | committed/pending state reducer |
| `src/components/TranscriptView.tsx` | P1-4/6 | Renders committed + pending |
| `src/components/ControlBar.tsx` | P1-4 | Start/Stop button |
| `src/worklets/pcm-processor.ts` | P1-5 | AudioWorklet processor |

## Test setup

Vitest + React Testing Library. Run with `npm test`.
Do NOT write snapshot tests — prefer behaviour tests.

## AudioWorklet note

The worklet file (`src/worklets/pcm-processor.ts`) must be loaded via Vite's `?worker&url` import or a dedicated Vite plugin. Check `vite.config.ts` for the setup.
The worklet resamples from the browser's native sample rate (usually 48 kHz) to 16 kHz and converts Float32 → Int16.
