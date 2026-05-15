# Meeting Transcript Tool

Local-first real-time meeting transcription tool.

## Status

Bootstrapped from planning docs. The project skeleton has NOT been built yet.

## Get started

1. Install Claude Code if you haven't: `npm install -g @anthropic-ai/claude-code`
2. Run `claude` in this directory.
3. Paste this as the first prompt:

> 請讀 CLAUDE.md 和 docs/PHASE1_TASKS.md，然後依照 CLAUDE.md 描述的 monorepo
> 結構，建立 frontend/、sidecar/、src-tauri/ 三個子系統的初始骨架（每個放
> 占位的 CLAUDE.md 與基本配置檔），以及根目錄的 Justfile。先不寫業務邏輯，
> 只搭鷹架。完成後跑 `just bootstrap` 驗證 deps 安裝。

## Documents

- `CLAUDE.md` — Claude Code project context (auto-loaded each session)
- `docs/SPEC.md` — Full implementation plan and specification
- `docs/PHASE1_TASKS.md` — Phase 1 task breakdown (one task = one Claude Code session)
