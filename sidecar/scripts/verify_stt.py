"""
End-to-end STT smoke test (P1-2).

Usage:
    cd sidecar
    python3.11 scripts/verify_stt.py [path/to/audio.wav]

Feeds a WAV file through the streaming pipeline and prints each committed
segment to stdout.  All Whisper logs go to stderr.

Requirements: pip install -r requirements-ml.txt
WAV format:   16 kHz, mono, 16-bit PCM (other formats will cause an error).
"""

from __future__ import annotations

import sys
import time
import wave
from pathlib import Path

# Allow running from repo root or from sidecar/
_sidecar_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_sidecar_dir))

from stt import WhisperStreamingEngine  # noqa: E402

CHUNK_MS = 100  # feed 100 ms chunks, matching the frontend cadence
SAMPLE_RATE = 16_000
BYTES_PER_SAMPLE = 2  # Int16
CHUNK_SAMPLES = SAMPLE_RATE * CHUNK_MS // 1000
CHUNK_BYTES = CHUNK_SAMPLES * BYTES_PER_SAMPLE


def fmt_ts(seconds: float | None) -> str:
    if seconds is None:
        return "??:??.???"
    m, s = divmod(seconds, 60)
    return f"{int(m):02d}:{s:06.3f}"


def main() -> int:
    wav_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/fixtures/sample_meeting.wav")

    if not wav_path.exists():
        print(f"ERROR: WAV file not found: {wav_path}", file=sys.stderr)
        print("Provide a path: python3.11 scripts/verify_stt.py /path/to/audio.wav", file=sys.stderr)
        return 1

    model_size = "base"
    print(f"Loading model '{model_size}'...", file=sys.stderr)
    engine = WhisperStreamingEngine(model_size=model_size)

    with wave.open(str(wav_path)) as wf:
        if wf.getframerate() != SAMPLE_RATE:
            print(f"ERROR: expected 16000 Hz, got {wf.getframerate()} Hz", file=sys.stderr)
            return 1
        if wf.getnchannels() != 1:
            print(f"ERROR: expected mono, got {wf.getnchannels()} channels", file=sys.stderr)
            return 1
        if wf.getsampwidth() != BYTES_PER_SAMPLE:
            print(f"ERROR: expected Int16 (2 bytes), got {wf.getsampwidth()} bytes", file=sys.stderr)
            return 1

        total_frames = wf.getnframes()
        duration = total_frames / SAMPLE_RATE
        print(f"Audio: {wav_path.name}  ({duration:.1f}s)", file=sys.stderr)
        print(f"Streaming in {CHUNK_MS}ms chunks...\n", file=sys.stderr)

        t_start = time.monotonic()
        while True:
            chunk = wf.readframes(CHUNK_SAMPLES)
            if not chunk:
                break
            events = engine.process(chunk)
            for ev in events:
                latency = time.monotonic() - t_start - (ev.get("end_time") or 0)
                print(f"[{fmt_ts(ev['start_time'])} → {fmt_ts(ev['end_time'])}]  {ev['text']}"
                      f"  (latency {latency:+.2f}s)")
                sys.stdout.flush()

    # Flush remainder
    for ev in engine.flush():
        print(f"[{fmt_ts(ev['start_time'])} → {fmt_ts(ev['end_time'])}]  {ev['text']}  (flush)")
        sys.stdout.flush()

    print("\nDone.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
