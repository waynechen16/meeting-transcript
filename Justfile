# Default: list available recipes
default:
	@just --list

# Install all subsystem dependencies
bootstrap:
	@echo "==> Installing frontend dependencies..."
	cd frontend && npm install
	@echo "==> Installing sidecar core dependencies..."
	cd sidecar && pip install -r requirements.txt
	@echo ""
	@echo "Bootstrap complete."
	@echo "ML dependencies (faster-whisper, torch, silero-vad) are in"
	@echo "sidecar/requirements-ml.txt — install separately when ready:"
	@echo "  cd sidecar && pip install -r requirements-ml.txt"

# Phase 1: run sidecar (FastAPI :8000) + frontend (Vite :5173) concurrently
dev:
	#!/usr/bin/env bash
	set -euo pipefail
	trap 'kill 0' SIGINT SIGTERM EXIT
	echo "Starting sidecar on :8000 and frontend on :5173 ..."
	(cd sidecar && uvicorn main:app --reload --port 8000) &
	(cd frontend && npm run dev) &
	wait

# Run all tests
test: test-sidecar test-frontend

# Python sidecar tests
test-sidecar:
	cd sidecar && python3.11 -m pytest tests/ -v

# Frontend tests
test-frontend:
	cd frontend && npm test

# End-to-end STT smoke test (requires ML deps + model downloaded)
verify-stt:
	cd sidecar && python3.11 scripts/verify_stt.py

# Format all code
fmt:
	cd frontend && npm run fmt
	cd sidecar && ruff format .

# Lint all code
lint:
	cd frontend && npm run lint
	cd sidecar && ruff check .

# Phase 2 — Tauri dev mode (requires Rust + cargo-tauri)
tauri-dev:
	cd src-tauri && cargo tauri dev

# Phase 2 — Production installer build
build:
	cd src-tauri && cargo tauri build
