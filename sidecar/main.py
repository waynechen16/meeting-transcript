"""
FastAPI application — Phase 1 entry point.

Business logic implemented in P1-1 through P1-7.
This file currently provides only the app skeleton and health endpoint.
"""

import logging
import sys

from fastapi import FastAPI

# All logs go to stderr so stdout remains clean for Phase 2 sidecar IPC.
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Meeting Transcript Sidecar", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# WebSocket /stream endpoint implemented in P1-1.
# STT engine wired in P1-2.
# VAD chunker wired in P1-3.
# SQLite storage wired in P1-7.
