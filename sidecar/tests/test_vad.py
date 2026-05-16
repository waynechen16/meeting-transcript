"""Unit tests for SileroVADChunker (P1-3).

Synthetic audio only — no real speech/WAV required.
The Silero model (~2 MB) is downloaded on first run.
"""

import numpy as np
import pytest

SAMPLE_RATE = 16_000
CHUNK_MS = 100
CHUNK_SAMPLES = SAMPLE_RATE * CHUNK_MS // 1000   # 1600
CHUNK_BYTES = CHUNK_SAMPLES * 2                   # Int16


def _silence(n_chunks: int = 1) -> list[bytes]:
    return [bytes(CHUNK_BYTES)] * n_chunks


def _tone(n_chunks: int = 1, freq: int = 1000) -> list[bytes]:
    """Generate a pure sine-wave tone (speech-like energy) as Int16 PCM."""
    t = np.arange(CHUNK_SAMPLES * n_chunks) / SAMPLE_RATE
    wave = (np.sin(2 * np.pi * freq * t) * 32000).astype(np.int16)
    chunks = []
    for i in range(n_chunks):
        chunks.append(wave[i * CHUNK_SAMPLES: (i + 1) * CHUNK_SAMPLES].tobytes())
    return chunks


@pytest.fixture(scope="module")
def chunker():
    from vad import SileroVADChunker
    return SileroVADChunker()


def test_vad_init(chunker):
    """SileroVADChunker instantiates and loads model without error."""
    assert chunker is not None
    assert chunker._model is not None


def test_feed_returns_tuple(chunker):
    """feed() always returns a (bytes|None, bool) tuple."""
    result = chunker.feed(bytes(CHUNK_BYTES))
    assert isinstance(result, tuple)
    assert len(result) == 2
    audio, flush = result
    assert audio is None or isinstance(audio, bytes)
    assert isinstance(flush, bool)


def test_silence_suppressed(chunker):
    """30 s of pure silence → no audio output and no flush signal."""
    chunker.reset()
    n_chunks = 300  # 30 s at 100 ms/chunk
    for chunk in _silence(n_chunks):
        audio, flush = chunker.feed(chunk)
        assert audio is None, "silence should be suppressed"
        assert flush is False, "no flush expected during silence"


def test_speech_passthrough(chunker):
    """When the model signals speech, audio is forwarded to the caller."""
    chunker.reset()
    # Mock the VAD model to always return high speech probability (0.9).
    from unittest.mock import patch

    import torch

    got_audio = False
    with patch.object(chunker, "_model", return_value=torch.tensor([[0.9]])):
        for chunk in _silence(n_chunks=5):  # content irrelevant — model is mocked
            audio, _ = chunker.feed(chunk)
            if audio is not None:
                got_audio = True
                assert isinstance(audio, bytes)
                break
    assert got_audio, "expected audio to pass through when model detects speech"


def test_flush_after_speech_then_silence(chunker):
    """Speech state followed by > 500 ms of silence emits exactly one flush."""
    from unittest.mock import patch

    import torch

    chunker.reset()

    # Phase 1: drive chunker into SPEECH state with mocked high probability.
    with patch.object(chunker, "_model", return_value=torch.tensor([[0.9]])):
        for chunk in _silence(n_chunks=10):  # 1 s — model returns speech
            chunker.feed(chunk)

    # Phase 2: feed silence frames with mocked low probability until flush fires.
    flush_count = 0
    with patch.object(chunker, "_model", return_value=torch.tensor([[0.0]])):
        for chunk in _silence(n_chunks=30):  # up to 3 s
            _, flush = chunker.feed(chunk)
            if flush:
                flush_count += 1

    assert flush_count == 1, f"expected exactly 1 flush, got {flush_count}"


def test_reset_clears_state(chunker):
    """After reset(), sustained silence is suppressed (no stale SPEECH state)."""
    from unittest.mock import patch

    import torch

    # Drive chunker into SPEECH state.
    with patch.object(chunker, "_model", return_value=torch.tensor([[0.9]])):
        for chunk in _silence(n_chunks=5):
            chunker.feed(chunk)

    chunker.reset()

    # Now real silence should be suppressed again (model back to real inference).
    for chunk in _silence(n_chunks=10):
        audio, flush = chunker.feed(chunk)
        assert audio is None
        assert flush is False
