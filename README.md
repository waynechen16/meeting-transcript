# Meeting Transcript Tool

Local-first real-time meeting transcription. Captures system audio, runs
Whisper inference on-device, and shows a live synchronized transcript.
**No cloud, no API keys — audio never leaves your machine.**

## Status

Phase 1 (Web POC) — complete. The full pipeline is wired:

```
Browser tab audio → getDisplayMedia → AudioWorklet (16 kHz PCM)
  → WebSocket → FastAPI sidecar → Silero VAD → faster-whisper (Whisper)
  → WebSocket events → React UI (committed / pending transcript)
  → SQLite (persistent storage)
```

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Node.js | 20+ LTS | frontend |
| Python | 3.11+ | sidecar |
| `just` | any | task runner — `brew install just` |
| pip ML deps | see below | Torch, faster-whisper, Silero VAD |

> **GPU optional.** The sidecar uses `device="cpu", compute_type="int8"` by
> default and works on any modern laptop.  A CUDA GPU speeds up transcription
> significantly for `large-v3` but is not required for `base` or `tiny`.

## Quick start (30 minutes)

### 1. Install core dependencies

```bash
git clone https://github.com/waynechen16/meeting-transcript.git
cd meeting-transcript
just bootstrap          # npm install + pip install core deps
```

### 2. Install ML dependencies

```bash
cd sidecar
pip install -r requirements-ml.txt   # torch, faster-whisper, silero-vad, …
```

The first run downloads the Whisper model weights into the HuggingFace cache
(`~/.cache/huggingface/`).  Model sizes:

| `WHISPER_MODEL` | Size | Notes |
|----------------|------|-------|
| `tiny` | ~75 MB | fast, lower accuracy |
| `base` | ~145 MB | default, good for dev |
| `large-v3` | ~3 GB | best accuracy, prod-ready |

### 3. Run the dev stack

```bash
just dev        # starts sidecar on :8000 + frontend on :5173
```

Open **http://localhost:5173** in Chrome or Edge.

### 4. Transcribe a meeting

1. Click **開始錄音**
2. In the browser dialog, select **Chrome Tab** or **Entire Screen** and enable **Share audio**
3. Play audio (a video, a podcast, a Teams/Zoom call) — text appears in real time
4. Click **停止錄音** when done
5. Transcripts are saved automatically to `sidecar/data/transcripts.db`

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_MODEL` | `base` | Whisper model size (tiny / base / large-v3) |
| `DB_PATH` | `data/transcripts.db` | SQLite database path (`:memory:` for tests) |

## Running tests

```bash
just test               # all subsystem tests

just test-sidecar       # Python tests only (includes integration tests)
just test-frontend      # Vitest + React Testing Library

# Skip the integration tests that load real ML models (faster for CI):
cd sidecar && python3.11 -m pytest tests/ -m "not integration" -v
```

## Verifying STT output

```bash
just verify-stt                                    # needs tests/fixtures/sample_meeting.wav
cd sidecar && python3.11 scripts/verify_stt.py /path/to/audio.wav
```

The script streams a WAV file through the pipeline and prints committed
segments with timestamps and latency information to stdout.

## Project layout

```
meeting-transcript/
├── frontend/           React 18 + TypeScript + Vite
│   └── src/
│       ├── components/ TranscriptView, ControlBar
│       ├── hooks/      useWebSocket, useAudioCapture, useTranscript, useAutoScroll
│       └── worklets/   pcm-processor (AudioWorklet — resamples to 16 kHz Int16)
│
├── sidecar/            Python 3.11 FastAPI STT service
│   ├── main.py         WebSocket /stream endpoint, DB lifespan
│   ├── stt.py          WhisperStreamingEngine (faster-whisper + whisper_streaming)
│   ├── vad.py          SileroVADChunker (speech gating, utterance segmentation)
│   ├── db.py           SQLite persistence (sessions + segments + FTS5)
│   ├── scripts/        verify_stt.py — end-to-end smoke test
│   └── vendor/         whisper_streaming vendored (no pip package)
│
├── src-tauri/          Rust shell — Phase 2 only (audio capture, packaging)
│
├── docs/
│   ├── SPEC.md         Full implementation plan
│   └── PHASE1_TASKS.md Task-by-task breakdown with acceptance criteria
│
└── Justfile            Task runner (bootstrap / dev / test / lint / fmt)
```

## Architecture

### WebSocket protocol

**Client → Server**: binary frames, Int16 PCM, 16 kHz mono, ~100 ms chunks (3 200 bytes).

**Server → Client**: JSON text frames:

```jsonc
// Interim — will be updated as more audio arrives
{ "type": "transcript", "is_final": false, "text": "你好世界", "start_time": 1.2 }

// Final — committed, saved to SQLite
{ "type": "transcript", "is_final": true, "text": "你好世界，", "start_time": 1.2, "end_time": 3.4, "segment_id": "<uuid>" }

// Error
{ "type": "error", "message": "chunk too large" }
```

### SQLite schema

```sql
-- One row per recording session (WebSocket connection)
CREATE TABLE sessions (id TEXT PRIMARY KEY, started_at REAL, ended_at REAL);

-- One row per committed transcript segment
CREATE TABLE segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES sessions(id),
    segment_id TEXT, started_at REAL, ended_at REAL, text TEXT
);

-- FTS5 for full-text search (Phase 2)
CREATE VIRTUAL TABLE segments_fts USING fts5(text, content=segments, content_rowid=id);
```

## Linting and formatting

```bash
just lint       # ESLint + ruff
just fmt        # prettier + ruff format
```

## Phase 2 (coming)

Tauri desktop app with WASAPI loopback audio capture, PyInstaller sidecar
packaging, system tray, and a Windows installer. See `docs/SPEC.md §Phase 2`.
