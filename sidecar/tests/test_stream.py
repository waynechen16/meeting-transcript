"""Tests for the /stream WebSocket endpoint (P1-1 through P1-3).

Both WhisperStreamingEngine and SileroVADChunker are mocked so these tests
verify only WebSocket protocol behaviour (chunk routing, error handling, event
forwarding).  STT and VAD correctness are tested in test_stt.py / test_vad.py.
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
    """MagicMock for WhisperStreamingEngine."""
    instance = MagicMock()
    instance.process.return_value = process_return or []
    instance.flush.return_value = flush_return or []
    instance.flush_and_reset.return_value = []
    return instance


def _mock_vad(pass_through: bool = True, flush: bool = False):
    """MagicMock for SileroVADChunker.

    pass_through=True  → feed() returns (data, flush)   — simulates speech
    pass_through=False → feed() returns (None, flush)   — simulates silence
    """
    instance = MagicMock()
    if pass_through:
        instance.feed.side_effect = lambda data: (data, flush)
    else:
        instance.feed.return_value = (None, flush)
    return instance


def test_stream_connect_disconnect():
    """Client can connect and disconnect cleanly without errors."""
    with (
        patch("main.WhisperStreamingEngine", return_value=_mock_engine()),
        patch("main.SileroVADChunker", return_value=_mock_vad()),
        TestClient(app) as client,
        client.websocket_connect("/stream"),
    ):
        pass


def test_stream_chunk_accepted():
    """Valid chunk passes through VAD and reaches the STT engine."""
    chunk = bytes(3200)  # 100 ms of 16 kHz mono Int16 silence
    engine = _mock_engine()
    with (
        patch("main.WhisperStreamingEngine", return_value=engine),
        patch("main.SileroVADChunker", return_value=_mock_vad(pass_through=True)),
        TestClient(app) as client,
        client.websocket_connect("/stream") as ws,
    ):
        ws.send_bytes(chunk)
    engine.process.assert_called_once_with(chunk)


def test_stream_silence_suppressed():
    """Chunks suppressed by VAD are not forwarded to the STT engine."""
    engine = _mock_engine()
    with (
        patch("main.WhisperStreamingEngine", return_value=engine),
        patch("main.SileroVADChunker", return_value=_mock_vad(pass_through=False)),
        TestClient(app) as client,
        client.websocket_connect("/stream") as ws,
    ):
        ws.send_bytes(bytes(3200))
    engine.process.assert_not_called()


def test_stream_flush_calls_flush_and_reset():
    """When VAD signals flush, engine.flush_and_reset() is called."""
    engine = _mock_engine()
    with (
        patch("main.WhisperStreamingEngine", return_value=engine),
        patch("main.SileroVADChunker", return_value=_mock_vad(pass_through=True, flush=True)),
        TestClient(app) as client,
        client.websocket_connect("/stream") as ws,
    ):
        ws.send_bytes(bytes(3200))
    engine.flush_and_reset.assert_called_once()


def test_stream_engine_events_forwarded():
    """Events returned by the engine are sent to the client as JSON."""
    engine = _mock_engine(process_return=[_TRANSCRIPT_EVENT])
    with (
        patch("main.WhisperStreamingEngine", return_value=engine),
        patch("main.SileroVADChunker", return_value=_mock_vad(pass_through=True)),
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
        patch("main.SileroVADChunker", return_value=_mock_vad()),
        TestClient(app) as client,
        client.websocket_connect("/stream") as ws,
    ):
        ws.send_bytes(oversized)
        msg = json.loads(ws.receive_text())
    assert msg["type"] == "error"
    assert "chunk too large" in msg["message"]
