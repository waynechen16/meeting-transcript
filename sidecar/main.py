"""
FastAPI application — Phase 1 entry point.

WebSocket /stream endpoint: P1-1
STT engine: P1-2
VAD chunker: P1-3
SQLite storage: P1-7
"""

import logging
import sys

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/stream")
async def stream(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("Client connected")
    try:
        while True:
            data = await websocket.receive_bytes()

            if len(data) > MAX_CHUNK_BYTES:
                await websocket.send_json({"type": "error", "message": "chunk too large"})
                continue

            # P1-1 mock response — replaced by real STT in P1-2.
            n_samples = len(data) // 2  # Int16 = 2 bytes per sample
            duration = n_samples / 16_000
            await websocket.send_json(
                {
                    "type": "transcript",
                    "is_final": False,
                    "text": f"[received {len(data)} bytes / {duration:.2f}s]",
                    "start_time": 0.0,
                }
            )
    except WebSocketDisconnect:
        logger.info("Client disconnected")
