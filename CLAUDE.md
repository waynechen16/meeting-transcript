# Meeting Transcript Tool

## Why

Local-first real-time meeting transcription. Captures system audio, runs Whisper inference locally, displays synchronized transcript with **no cloud dependencies**. Privacy is a hard requirement — meeting audio and transcripts must never leave the user's machine.

Detailed spec: @docs/SPEC.md
Current phase tasks: @docs/PHASE1_TASKS.md

## What

Monorepo with three subsystems:

- `frontend/` — React 18 + TypeScript + Vite. UI, state management, WebSocket client (Phase 1) / Tauri IPC (Phase 2).
- `sidecar/` — Python 3.11+ STT service. faster-whisper, whisper_streaming, Silero VAD. Runs as FastAPI server in Phase 1, as a Tauri sidecar (stdin/stdout JSONL) in Phase 2.
- `src-tauri/` — Rust shell (Phase 2 only). cpal audio capture, SQLite persistence, sidecar process management.

Each subsystem has its own `CLAUDE.md` with deeper context. Read it before working in that directory.

Shared docs:
- `docs/ARCHITECTURE.md` — system design and IPC protocol
- `docs/whisper-streaming-notes.md` — non-obvious behavior of the streaming wrapper
- `docs/tauri-sidecar-notes.md` — Phase 2 packaging quirks

## How

### Setup

```bash
just bootstrap          # Install deps for all subsystems
```

### Phase 1 (current)

```bash
just dev                # Runs sidecar (FastAPI on :8000) + frontend (Vite on :5173)
just test               # All tests across subsystems
just test-sidecar       # Python tests only
just verify-stt         # End-to-end STT smoke test with a sample WAV
```

### Phase 2 (Tauri packaging — not yet active)

```bash
just tauri-dev          # Full Tauri dev mode
just build              # Production installer
```

### Workflow

1. For any task larger than ~30 lines of code: use plan mode first. Write the plan to `PLAN.md`, get it reviewed, then implement.
2. One task per branch, one PR per task. Reference task ID from `docs/PHASE1_TASKS.md` in commit message.
3. Run `just test` before every commit. Run `just verify-stt` before any PR touching `sidecar/`.
4. Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`.

### Code style

Linters and formatters are configured per-subsystem. Run `just fmt` and `just lint` — don't manually style code.

## Hard rules — do not violate

- **No network calls in `sidecar/` or `src-tauri/`** beyond localhost IPC. Cloud STT is not an option, ever. There are no API keys to add.
- **No model weights or audio in git.** `.gitignore` covers `*.wav`, `*.pt`, `*.bin`, `models/`. Confirm before adding any binary.
- **Python sidecar must write protocol JSON to stdout only.** All logging goes to stderr. Stdout pollution will break IPC.
- **Don't use `large-v3` model in tests or CI.** Use `tiny` or `base`. Inference time matters.
- **Don't modify `whisper_streaming` upstream code** vendored under `sidecar/vendor/`. Wrap and extend in our own modules.

## Gotchas

- `whisper_streaming` returns finalized text in segments via `process_iter()`, but the offset semantics are tricky. See @docs/whisper-streaming-notes.md before changing anything in `sidecar/streaming.py`.
- WASAPI loopback (Phase 2) requires Windows 10 1809+ and may behave differently on corporate-managed machines with audio policy restrictions. Fallback to `getDisplayMedia` is mandatory.
- Tauri sidecar binaries on Windows need `.exe` suffix in `tauri.conf.json` even when developing on macOS/Linux. Cross-platform path handling is in @docs/tauri-sidecar-notes.md.
- Long meetings (2h+) need `committed[]` virtualization on the frontend (react-virtuoso). Don't render unbounded lists.

## When stuck

- Don't guess Whisper streaming behavior. Run `just verify-stt`, or read the verification script at `scripts/verify_stt.py` to see what correct streaming output looks like.
- For audio capture issues: `scripts/list_audio_devices.py` (Python) and `scripts/list_audio_devices.rs` (Rust) print available devices on the current OS.
- For IPC issues between sidecar and Tauri: `scripts/replay_jsonl.py` can replay a recorded sidecar transcript for testing the frontend in isolation.
