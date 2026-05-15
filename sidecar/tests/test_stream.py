"""Tests for the /stream WebSocket endpoint (P1-1)."""

import json

from starlette.testclient import TestClient

from main import MAX_CHUNK_BYTES, app


def test_stream_connect_disconnect():
    """Client can connect and disconnect cleanly without errors."""
    with TestClient(app) as client, client.websocket_connect("/stream"):
        pass  # connect then immediately close


def test_stream_echo():
    """Server echoes a mock transcript JSON for a valid 100 ms PCM chunk."""
    chunk = bytes(3200)  # 100 ms of silence: 1600 samples × 2 bytes
    with TestClient(app) as client, client.websocket_connect("/stream") as ws:
        ws.send_bytes(chunk)
        msg = json.loads(ws.receive_text())

    assert msg["type"] == "transcript"
    assert msg["is_final"] is False
    assert "text" in msg
    assert "start_time" in msg


def test_stream_oversized_chunk():
    """Server returns an error message for chunks exceeding MAX_CHUNK_BYTES."""
    oversized = bytes(MAX_CHUNK_BYTES + 1)
    with TestClient(app) as client, client.websocket_connect("/stream") as ws:
        ws.send_bytes(oversized)
        msg = json.loads(ws.receive_text())

    assert msg["type"] == "error"
    assert "chunk too large" in msg["message"]
