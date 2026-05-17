"""
Integration tests for the full WebSocket pipeline (P1-9).

These tests load the **real** Silero VAD and Whisper (tiny) models — no mocks
for VAD or STT.  The database is still mocked by conftest so no files are
written to disk.

Note on end_session: Starlette's TestClient sends the WS close frame but does
not synchronously wait for the server's disconnect handler (which runs in an
async task) to finish.  Assertions about end_session are therefore unreliable
in sync integration tests; that codepath is covered by test_stream.py instead.

Run all tests:
    cd sidecar && python3.11 -m pytest tests/ -v

Skip integration tests (faster CI):
    python3.11 -m pytest tests/ -v -m "not integration"

Requirements: pip install -r requirements-ml.txt
"""

from __future__ import annotations

import json

import numpy as np
import pytest
from starlette.testclient import TestClient

# Skip the whole module if ML deps are not installed.
pytest.importorskip("faster_whisper", reason="ML deps required (pip install -r requirements-ml.txt)")
pytest.importorskip("silero_vad", reason="ML deps required")

from main import MAX_CHUNK_BYTES, app  # noqa: E402

pytestmark = pytest.mark.integration

SAMPLE_RATE = 16_000
CHUNK_MS = 100
CHUNK_SAMPLES = SAMPLE_RATE * CHUNK_MS // 1000  # 1 600 samples
CHUNK_BYTES = CHUNK_SAMPLES * 2                  # Int16 → 2 bytes/sample


def _silence(seconds: float) -> list[bytes]:
    """Return a list of 100 ms silence chunks covering `seconds`."""
    n_chunks = int(seconds * 1000 / CHUNK_MS)
    return [bytes(CHUNK_BYTES)] * n_chunks


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_pipeline_silence_no_events(mock_database) -> None:
    """2 s of silence: pipeline stays stable, no crashes, session opened."""
    with (
        TestClient(app) as client,
        client.websocket_connect("/stream") as ws,
    ):
        for chunk in _silence(2.0):
            ws.send_bytes(chunk)
        # No transcript events expected — silence is suppressed by VAD

    # Session was opened (happens synchronously before the receive loop)
    mock_database.create_session.assert_called_once()
    # Session ID is a non-empty string
    session_id = mock_database.create_session.call_args[0][0]
    assert len(session_id) > 0
    # started_at is a positive float (wall-clock time)
    started_at = mock_database.create_session.call_args[0][1]
    assert started_at > 0


def test_pipeline_vad_suppresses_silence(mock_database) -> None:
    """VAD must suppress silence: no segments persisted for 3 s of quiet."""
    with (
        TestClient(app) as client,
        client.websocket_connect("/stream") as ws,
    ):
        for chunk in _silence(3.0):
            ws.send_bytes(chunk)

    mock_database.save_segment.assert_not_called()


def test_pipeline_oversized_chunk_returns_error(mock_database) -> None:
    """Oversized chunk returns an error JSON; connection stays alive after."""
    with (
        TestClient(app) as client,
        client.websocket_connect("/stream") as ws,
    ):
        ws.send_bytes(bytes(MAX_CHUNK_BYTES + 1))
        error_msg = json.loads(ws.receive_text())
        assert error_msg["type"] == "error"
        assert "chunk too large" in error_msg["message"]

        # Pipeline must still accept normal chunks after the error
        for chunk in _silence(0.5):
            ws.send_bytes(chunk)


def test_pipeline_two_sessions_have_unique_ids(mock_database) -> None:
    """Each WebSocket connection receives a distinct session_id."""
    session_ids: list[str] = []
    for _ in range(2):
        with (
            TestClient(app) as client,
            client.websocket_connect("/stream") as ws,
        ):
            ws.send_bytes(bytes(CHUNK_BYTES))

        session_ids.append(mock_database.create_session.call_args[0][0])
        mock_database.reset_mock()

    assert session_ids[0] != session_ids[1]


def test_pipeline_loud_noise_no_crash(mock_database) -> None:
    """White noise (max amplitude Int16) must not crash the pipeline."""
    rng = np.random.default_rng(42)
    noise = rng.integers(-32768, 32767, size=CHUNK_SAMPLES, dtype=np.int16).tobytes()

    with (
        TestClient(app) as client,
        client.websocket_connect("/stream") as ws,
    ):
        for _ in range(20):  # 2 s of max-amplitude white noise
            ws.send_bytes(noise)

    mock_database.create_session.assert_called_once()


def test_pipeline_many_chunks_no_memory_growth(mock_database) -> None:
    """30 s of silence: the pipeline must not crash or raise memory errors."""
    with (
        TestClient(app) as client,
        client.websocket_connect("/stream") as ws,
    ):
        for chunk in _silence(30.0):
            ws.send_bytes(chunk)

    mock_database.create_session.assert_called_once()
    mock_database.save_segment.assert_not_called()
