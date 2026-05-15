"""Tests for the /stream WebSocket endpoint (P1-1/P1-2).

The STT engine is mocked here so these tests only verify WebSocket protocol
behaviour (chunk acceptance, error routing, event forwarding).
STT correctness is tested in test_stt.py using the real tiny model.
"""

import json
from unittest.mock import MagicMock, patch

from starlette.testclient import TestClient

from main import MAX_CHUNK_BYTES, app

_TRANSCRIPT_EVENT = {
    "type": "transcript",
    "is_final": True,
    "text": "你好",
    "start_time": 0.0,
    "end_time": 1.0,
    "segment_id": "test-uuid",
}


def _mock_engine(process_return=None, flush_return=None):
    """Return a MagicMock standing in for WhisperStreamingEngine."""
    instance = MagicMock()
    instance.process.return_value = process_return or []
    instance.flush.return_value = flush_return or []
    return instance


def test_stream_connect_disconnect():
    """Client can connect and disconnect cleanly without errors."""
    with (
        patch("main.WhisperStreamingEngine", return_value=_mock_engine()),
        TestClient(app) as client,
        client.websocket_connect("/stream"),
    ):
        pass


def test_stream_chunk_accepted():
    """Valid-sized chunk reaches the engine without error."""
    chunk = bytes(3200)  # 100 ms of 16 kHz mono Int16 silence
    engine = _mock_engine()
    with (
        patch("main.WhisperStreamingEngine", return_value=engine),
        TestClient(app) as client,
        client.websocket_connect("/stream") as ws,
    ):
        ws.send_bytes(chunk)
    engine.process.assert_called_once_with(chunk)


def test_stream_engine_events_forwarded():
    """Events returned by the engine are sent to the client as JSON."""
    engine = _mock_engine(process_return=[_TRANSCRIPT_EVENT])
    with (
        patch("main.WhisperStreamingEngine", return_value=engine),
        TestClient(app) as client,
        client.websocket_connect("/stream") as ws,
    ):
        ws.send_bytes(bytes(3200))
        msg = json.loads(ws.receive_text())
    assert msg["type"] == "transcript"
    assert msg["text"] == "你好"
    assert msg["is_final"] is True


def test_stream_oversized_chunk():
    """Server returns an error message for chunks exceeding MAX_CHUNK_BYTES."""
    oversized = bytes(MAX_CHUNK_BYTES + 1)
    with (
        patch("main.WhisperStreamingEngine", return_value=_mock_engine()),
        TestClient(app) as client,
        client.websocket_connect("/stream") as ws,
    ):
        ws.send_bytes(oversized)
        msg = json.loads(ws.receive_text())
    assert msg["type"] == "error"
    assert "chunk too large" in msg["message"]
