#!/usr/bin/env python3
"""Generate a neutral synthetic test clip for the first Navi message."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path


RATE = 16000
OUTPUT = Path(__file__).resolve().parents[1] / "content/voice/trump_00e0_00.wav"


def envelope(index: int, length: int) -> float:
    attack = min(1.0, index / (RATE * 0.015))
    release = min(1.0, (length - index) / (RATE * 0.06))
    return max(0.0, min(attack, release))


def main() -> None:
    # A deliberately non-imitative, game-like robot cadence: four short notes.
    notes = ((392.0, 0.18), (523.25, 0.18), (659.25, 0.25), (523.25, 0.32))
    samples: list[int] = []
    for frequency, duration in notes:
        length = int(RATE * duration)
        for i in range(length):
            t = i / RATE
            fundamental = math.sin(2 * math.pi * frequency * t)
            harmonic = 0.25 * math.sin(2 * math.pi * frequency * 2 * t)
            samples.append(int(9000 * envelope(i, length) * (fundamental + harmonic)))
        samples.extend([0] * int(RATE * 0.035))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUTPUT), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(RATE)
        stream.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))
    print(f"wrote {OUTPUT} ({len(samples) / RATE:.2f}s)")


if __name__ == "__main__":
    main()
