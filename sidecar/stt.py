"""
STT engine (P1-2).

Wraps whisper_streaming's OnlineASRProcessor with a CPU-compatible
FasterWhisperASR backend.  The model weights are loaded once as a module-level
singleton; each WebSocket connection gets its own stateful OnlineASRProcessor.

See docs/whisper-streaming-notes.md and sidecar/CLAUDE.md before modifying.
Do NOT modify vendor/whisper_streaming/whisper_online.py — extend here instead.
"""

from __future__ import annotations

import logging
import sys
import uuid
from pathlib import Path

import numpy as np

# Vendor path — whisper_streaming has no pip-installable package.
sys.path.insert(0, str(Path(__file__).parent / "vendor" / "whisper_streaming"))
from whisper_online import FasterWhisperASR, OnlineASRProcessor  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CPU-compatible ASR backend (vendor hardcodes device="cuda")
# ---------------------------------------------------------------------------

class _CPUFasterWhisperASR(FasterWhisperASR):
    """FasterWhisperASR subclass that loads the model on CPU with int8 quantization.

    The upstream class hardcodes device='cuda' which fails on machines without
    a GPU.  This subclass overrides only load_model() to use CPU instead.
    """

    def load_model(self, modelsize=None, cache_dir=None, model_dir=None):
        from faster_whisper import WhisperModel

        model_path = model_dir or modelsize
        if model_path is None:
            raise ValueError("modelsize or model_dir must be provided")
        logger.info("Loading WhisperModel '%s' on CPU (int8)...", model_path)
        model = WhisperModel(model_path, device="cpu", compute_type="int8",
                             download_root=cache_dir)
        logger.info("WhisperModel loaded.")
        return model


# ---------------------------------------------------------------------------
# Model singleton — loaded once, shared across connections
# ---------------------------------------------------------------------------

_asr_model: _CPUFasterWhisperASR | None = None


def get_asr_model(model_size: str = "base", language: str = "zh") -> _CPUFasterWhisperASR:
    """Return (and lazily load) the shared ASR model."""
    global _asr_model
    if _asr_model is None:
        _asr_model = _CPUFasterWhisperASR(language, modelsize=model_size)
    return _asr_model


# ---------------------------------------------------------------------------
# Per-connection streaming engine
# ---------------------------------------------------------------------------

class WhisperStreamingEngine:
    """One instance per WebSocket connection.

    process() feeds raw Int16 PCM bytes and returns any newly committed
    transcript events.  flush() drains remaining text when the connection closes.
    """

    def __init__(self, model_size: str = "base", language: str = "zh") -> None:
        asr = get_asr_model(model_size, language)
        # buffer_trimming=("segment", 15) — trim after 15 s of audio (default)
        self.processor = OnlineASRProcessor(asr, logfile=sys.stderr)

    def process(self, pcm_int16: bytes) -> list[dict]:
        """Feed a chunk of Int16 PCM (16 kHz mono) and return committed events."""
        audio = np.frombuffer(pcm_int16, dtype=np.int16).astype(np.float32) / 32768.0
        self.processor.insert_audio_chunk(audio)
        beg, end, text = self.processor.process_iter()
        if text and text.strip():
            return [_make_event(text, beg, end, is_final=True)]
        return []

    def flush(self) -> list[dict]:
        """Drain remaining committed text — call when the connection closes."""
        beg, end, text = self.processor.finish()
        if text and text.strip():
            return [_make_event(text, beg, end, is_final=True)]
        return []

    def flush_and_reset(self) -> list[dict]:
        """Flush remaining text and reset processor for the next utterance.

        Called by the VAD layer at each utterance boundary so that timestamps
        restart from zero and the audio buffer does not carry over stale audio.
        """
        events = self.flush()
        self.processor.init()
        return events


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(
    text: str,
    beg: float | None,
    end: float | None,
    *,
    is_final: bool,
) -> dict:
    return {
        "type": "transcript",
        "is_final": is_final,
        "text": text.strip(),
        "start_time": round(beg, 3) if beg is not None else 0.0,
        "end_time": round(end, 3) if end is not None else 0.0,
        "segment_id": str(uuid.uuid4()),
    }
