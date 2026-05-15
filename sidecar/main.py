"""
FastAPI application — Phase 1 entry point.

WebSocket /stream endpoint: P1-1
STT engine wired:          P1-2
VAD chunker:               P1-3
SQLite storage:            P1-7
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import sys

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from stt import WhisperStreamingEngine

# All logs go to stderr so stdout remains clean for Phase 2 sidecar IPC.
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Meeting Transcript Sidecar", version="0.1.0")

# 512 KB ≈ 16 s of 16 kHz mono Int16 audio — hard cap to protect memory.
MAX_CHUNK_BYTES = 512_000

# Override via WHISPER_MODEL env var (e.g. "tiny" for dev, "large-v3" for prod).
MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/stream")
async def stream(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("Client connected")
    engine = WhisperStreamingEngine(model_size=MODEL_SIZE)
    loop = asyncio.get_event_loop()
    try:
        while True:
            data = await websocket.receive_bytes()

            if len(data) > MAX_CHUNK_BYTES:
                await websocket.send_json({"type": "error", "message": "chunk too large"})
                continue

            events = await loop.run_in_executor(None, engine.process, data)
            for ev in events:
                await websocket.send_json(ev)

    except WebSocketDisconnect:
        # Flush any remaining committed text; connection may already be closed.
        for ev in engine.flush():
            with contextlib.suppress(Exception):
                await websocket.send_json(ev)
        logger.info("Client disconnected")
