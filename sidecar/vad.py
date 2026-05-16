"""
Silero VAD chunker (P1-3).

Gates the STT engine: speech frames pass through, silence is suppressed.
At utterance boundaries (silence > threshold) it signals the caller to
flush-and-reset the STT processor so each utterance starts fresh.

See sidecar/CLAUDE.md §Silero VAD notes for design rationale.
"""

from __future__ import annotations

import logging

import numpy as np
import torch

logger = logging.getLogger(__name__)


class SileroVADChunker:
    """Per-connection VAD gate.

    Call feed() for every incoming audio chunk.  It returns the audio to pass
    to the STT engine (None during silence) and a flush flag that fires once
    per utterance boundary.

    State machine:
        SILENCE ──(speech detected)──────────────────► SPEECH
        SPEECH  ──(≥ SILENCE_THRESHOLD_MS of silence)► flush → SILENCE
        SPEECH  ──(≥ FORCE_FLUSH_S of speech)────────► flush, continue SPEECH
    """

    # Silero VAD processes exactly 512 samples (≈ 32 ms) per call at 16 kHz.
    VAD_FRAME_SAMPLES: int = 512
    SILENCE_THRESHOLD_MS: int = 500   # ms of silence that ends an utterance
    FORCE_FLUSH_S: int = 15           # hard cap — flush after 15 s of speech

    def __init__(self, sample_rate: int = 16_000, threshold: float = 0.5) -> None:
        self.sample_rate = sample_rate
        self.threshold = threshold
        self._silence_threshold_frames = int(
            self.SILENCE_THRESHOLD_MS / 1000 * sample_rate / self.VAD_FRAME_SAMPLES
        )
        self._force_flush_samples = self.FORCE_FLUSH_S * sample_rate

        logger.info("Loading Silero VAD model...")
        from silero_vad import load_silero_vad
        self._model = load_silero_vad()
        logger.info("Silero VAD model loaded.")

        self._reset_state()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def feed(self, pcm_int16: bytes) -> tuple[bytes | None, bool]:
        """Process one incoming Int16 PCM chunk (16 kHz mono).

        Returns:
            audio  — the original pcm_int16 bytes to forward to the STT engine,
                     or None if the chunk falls entirely within sustained silence.
            flush  — True exactly once per utterance end; caller should call
                     engine.flush_and_reset() to commit remaining text.
        """
        audio = np.frombuffer(pcm_int16, dtype=np.int16).astype(np.float32) / 32768.0

        # Prepend any leftover sub-frame samples from the previous call.
        if len(self._remainder) > 0:
            audio = np.concatenate([self._remainder, audio])

        is_any_speech = False
        flush = False

        # Process complete 512-sample VAD frames.
        n_frames = len(audio) // self.VAD_FRAME_SAMPLES
        self._remainder = audio[n_frames * self.VAD_FRAME_SAMPLES:]

        for i in range(n_frames):
            frame = audio[i * self.VAD_FRAME_SAMPLES: (i + 1) * self.VAD_FRAME_SAMPLES]
            frame_tensor = torch.from_numpy(frame)
            prob: float = self._model(frame_tensor, self.sample_rate).item()

            if prob > self.threshold:
                self._is_speaking = True
                self._silence_frames = 0
                is_any_speech = True
                self._speech_samples += self.VAD_FRAME_SAMPLES
            else:
                if self._is_speaking:
                    self._silence_frames += 1
                    if self._silence_frames >= self._silence_threshold_frames:
                        # End of utterance detected.
                        flush = True
                        self._is_speaking = False
                        self._silence_frames = 0
                        self._speech_samples = 0

        # Hard cap: 15 s of uninterrupted speech → force flush.
        if self._speech_samples >= self._force_flush_samples:
            flush = True
            self._speech_samples = 0

        audio_out: bytes | None = pcm_int16 if (self._is_speaking or is_any_speech) else None
        return audio_out, flush

    def reset(self) -> None:
        """Reset all state. Call when a WebSocket connection closes."""
        self._model.reset_states()
        self._reset_state()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reset_state(self) -> None:
        self._remainder = np.array([], dtype=np.float32)
        self._is_speaking: bool = False
        self._silence_frames: int = 0
        self._speech_samples: int = 0
