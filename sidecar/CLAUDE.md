# sidecar/ — Python STT Service

## What this is

Python 3.11+ FastAPI service that receives PCM audio over WebSocket, runs
VAD + Whisper streaming inference locally, and emits transcript events.

In **Phase 1** it runs as a standalone FastAPI/uvicorn server on `:8000`.
In **Phase 2** it will be compiled to a standalone binary by PyInstaller and
managed as a Tauri sidecar communicating over stdin/stdout JSONL.

## Hard rules

- **No network calls** beyond localhost. All inference is local.
- **stdout is sacred**: in Phase 2 stdout is the IPC channel. All logging MUST go to `stderr`.
  Use `logging` with a handler that writes to `sys.stderr`. Never `print()` to stdout.
- **Do not modify `vendor/whisper_streaming/`**. Wrap and extend in our own modules.
- **Never use large-v3 in tests or CI**. Use `tiny` or `base` only.
- **No model weights or audio in git**. Covered by `.gitignore`.

## Key modules

| File | Task | Purpose |
|------|------|---------|
| `main.py` | P1-1 | FastAPI app, `/stream` WebSocket endpoint, `/health` HTTP |
| `stt.py` | P1-2 | `WhisperStreamingEngine` — wraps `OnlineASRProcessor` |
| `vad.py` | P1-3 | `SileroVAD` — VAD chunker, outputs speech segments |
| `storage.py` | P1-7 | `SegmentStore` — async SQLite writes via `aiosqlite` |
| `scripts/verify_stt.py` | P1-2 | CLI smoke test: feed a WAV, print streaming output |

## WebSocket message protocol

**Client → Server**: binary frames containing raw Int16 PCM samples (16 kHz mono, little-endian).

**Server → Client**: JSON text frames
```jsonc
// Interim (is_final=false) — will be replaced
{ "type": "transcript", "is_final": false, "text": "你好世界", "start_time": 1.2 }

// Final (is_final=true) — append to committed
{ "type": "transcript", "is_final": true, "text": "你好世界，", "start_time": 1.2, "end_time": 3.4, "segment_id": "<uuid>" }

// Error
{ "type": "error", "message": "..." }
```

## Audio format

- Sample rate: 16 000 Hz
- Channels: 1 (mono)
- Encoding: Int16 PCM, little-endian
- Chunk size: ~100 ms worth of samples = 1 600 samples = 3 200 bytes

## whisper_streaming notes

`whisper_streaming` is vendored under `vendor/whisper_streaming/`. Its
`OnlineASRProcessor.process_iter()` returns `(begin_time, end_time, text)` tuples.
`text` is `None` when there is no output yet. See `docs/whisper-streaming-notes.md`
for the non-obvious offset semantics before touching `stt.py`.

## Silero VAD notes

- VAD and Whisper both expect 16 kHz mono.
- Silero processes 30 ms chunks (512 samples at 16 kHz).
- whisper_streaming has its own internal voice activity heuristic; our VAD layer
  sits **before** it and is responsible for suppressing silent periods so we
  don't feed silence to Whisper. See `docs/whisper-streaming-notes.md`.

## SQLite schema

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    started_at REAL NOT NULL,
    ended_at REAL
);

CREATE TABLE segments (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    started_at REAL NOT NULL,
    ended_at REAL,
    text TEXT NOT NULL
);

CREATE VIRTUAL TABLE segments_fts USING fts5(text, content=segments, content_rowid=rowid);
```

## Testing

Run with `just test-sidecar` or `cd sidecar && python -m pytest tests/ -v`.
Tests use `tiny` model. Do NOT download large-v3 in CI.
Use `httpx[ws]` for async WebSocket test client.
