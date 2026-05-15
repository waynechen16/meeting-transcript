"""
Unit tests for WhisperStreamingEngine (P1-2).

These tests require ML dependencies:
    pip install -r requirements-ml.txt

The 'tiny' Whisper model (~75 MB) is downloaded on first run into the
HuggingFace cache and reused on subsequent runs.
"""

import pytest

SILENCE_5S = bytes(5 * 16_000 * 2)  # 5 s of 16 kHz mono Int16 zeros


@pytest.fixture(scope="module")
def engine():
    """Shared engine across tests in this module — avoids reloading model."""
    from stt import WhisperStreamingEngine
    return WhisperStreamingEngine(model_size="tiny", language="zh")


def test_engine_init(engine):
    """WhisperStreamingEngine instantiates without error."""
    assert engine is not None
    assert engine.processor is not None


def test_process_returns_list(engine):
    """process() always returns a list."""
    result = engine.process(bytes(3200))  # 100 ms silence
    assert isinstance(result, list)


def test_flush_returns_list(engine):
    """flush() always returns a list."""
    result = engine.flush()
    assert isinstance(result, list)


def test_process_silence_no_output(engine):
    """Feeding 5 s of silence produces no transcript events."""
    # Reset processor state for a clean test
    engine.processor.init()
    events = engine.process(SILENCE_5S)
    assert events == [], f"Expected no events for silence, got: {events}"


def test_event_schema():
    """Committed events contain required fields with correct types."""
    from stt import _make_event
    ev = _make_event("你好", 1.0, 2.5, is_final=True)
    assert ev["type"] == "transcript"
    assert ev["is_final"] is True
    assert isinstance(ev["text"], str)
    assert isinstance(ev["start_time"], float)
    assert isinstance(ev["end_time"], float)
    assert isinstance(ev["segment_id"], str)
    assert len(ev["segment_id"]) == 36  # UUID format
