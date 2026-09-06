#!/usr/bin/env python3
"""Normalize the voice catalog for consistent, click-free N64 playback."""

from __future__ import annotations

import argparse
import math
import os
import sys
import wave
from array import array
from pathlib import Path


SAMPLE_RATE = 16000
TARGET_DBFS = -20.0
ACTIVE_GATE_DBFS = -45.0
PEAK_CEILING_DBFS = -3.0
FADE_SAMPLES = 80  # 5 ms at 16 kHz


def active_rms(samples: array) -> float:
    gate = 10 ** (ACTIVE_GATE_DBFS / 20.0)
    squares = 0
    count = 0
    window = SAMPLE_RATE // 50
    for start in range(0, len(samples), window):
        frame = samples[start : start + window]
        if not frame:
            continue
        frame_squares = sum(value * value for value in frame)
        frame_rms = math.sqrt(frame_squares / len(frame)) / 32768.0
        if frame_rms >= gate:
            squares += frame_squares
            count += len(frame)
    return math.sqrt(squares / count) / 32768.0 if count else 0.0


def dbfs(value: float) -> float:
    return 20.0 * math.log10(value) if value > 0.0 else -120.0


def read_wav(path: Path) -> array:
    with wave.open(str(path), "rb") as source:
        if (
            source.getnchannels() != 1
            or source.getsampwidth() != 2
            or source.getframerate() != SAMPLE_RATE
            or source.getcomptype() != "NONE"
        ):
            raise RuntimeError(f"{path}: expected mono 16-bit PCM at {SAMPLE_RATE} Hz")
        samples = array("h", source.readframes(source.getnframes()))
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples:
        raise RuntimeError(f"{path}: empty WAV")
    return samples


def write_wav(path: Path, samples: array) -> None:
    output_samples = array("h", samples)
    if sys.byteorder != "little":
        output_samples.byteswap()
    temporary = path.with_suffix(path.suffix + ".tmp")
    with wave.open(str(temporary), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(output_samples.tobytes())
    os.replace(temporary, path)


def normalize(samples: array) -> array:
    mean = sum(samples) / len(samples)
    centered = array("h", (round(value - mean) for value in samples))
    level = active_rms(centered)
    if level == 0.0:
        raise RuntimeError("audio contains no active speech")
    gain = 10 ** (TARGET_DBFS / 20.0) / level
    ceiling = 32767.0 * (10 ** (PEAK_CEILING_DBFS / 20.0))
    projected_peak = max(abs(value) for value in centered) * gain
    if projected_peak > ceiling:
        gain *= ceiling / projected_peak

    result = array("h", (max(-32768, min(32767, round(value * gain))) for value in centered))
    fade = min(FADE_SAMPLES, len(result) // 2)
    for index in range(fade):
        factor = index / fade
        result[index] = round(result[index] * factor)
        end = len(result) - 1 - index
        result[end] = round(result[end] * factor)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", type=Path, default=Path("content/voice"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    paths = sorted(args.directory.glob("trump_*.wav"))
    if not paths:
        raise RuntimeError(f"no voice WAVs found in {args.directory}")

    failures = []
    for path in paths:
        samples = read_wav(path)
        if not args.check:
            samples = normalize(samples)
            write_wav(path, samples)
        level = dbfs(active_rms(samples))
        peak = dbfs(max(abs(value) for value in samples) / 32768.0)
        if abs(level - TARGET_DBFS) > 0.5 or peak > PEAK_CEILING_DBFS + 0.05:
            failures.append(f"{path.name}: active {level:.2f} dBFS, peak {peak:.2f} dBFS")
    if failures:
        raise RuntimeError("voice normalization check failed:\n" + "\n".join(failures))
    print(
        f"validated {len(paths)} voice WAVs at {TARGET_DBFS:.1f} dBFS active speech "
        f"with peaks at or below {PEAK_CEILING_DBFS:.1f} dBFS"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
