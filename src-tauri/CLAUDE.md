# src-tauri/ — Rust Shell (Phase 2)

## Status

**Phase 2 — not yet active.** This directory is a placeholder.
Do not implement anything here until Phase 1 (Web POC) is complete and M1 is signed off.

## What this will do (Phase 2)

| Responsibility | Detail |
|----------------|--------|
| Audio capture | `cpal` + WASAPI loopback (Windows primary), `CoreAudio` loopback (macOS) |
| Sidecar management | Spawn/kill the PyInstaller-bundled Python sidecar; read stdout JSONL, write stdin commands |
| SQLite persistence | `rusqlite` — segments table; same schema as Phase 1 sidecar SQLite |
| Tauri IPC | Emit `transcript` events to the React frontend via `app_handle.emit_all()` |
| System tray | Start/Stop hotkeys, tray icon with recording indicator |

## Key Phase 2 tasks

See `docs/PHASE1_TASKS.md` — Phase 2 task IDs are P2-1 through P2-10.

## Important gotchas for Phase 2

- Sidecar binary on Windows needs `.exe` suffix in `tauri.conf.json` **even when developing on macOS**.
  See `docs/tauri-sidecar-notes.md`.
- WASAPI loopback requires Windows 10 1809+. Fallback to `getDisplayMedia` is mandatory for unsupported hosts.
- Do not bundle model weights in the installer. First-launch download with progress bar (P2-5).
- Cross-platform audio device enumeration: `scripts/list_audio_devices.rs`.

## Crate dependencies (planned)

```toml
tauri = { version = "2", features = ["shell-sidecar"] }
cpal = "0.15"
rusqlite = { version = "0.31", features = ["bundled"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tokio = { version = "1", features = ["full"] }
```
