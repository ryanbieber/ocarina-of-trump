#!/usr/bin/env python3
"""Generate and split the Navi voice catalog with the public HF Gradio Space.

The Space permits nine requests per client.  The 176 short lines are therefore
packed into nine requests and separated with the Space's documented pause tag.
Generated source MP3s and resumable state live under .work/voice-hf; final WAVs
are written to content/voice.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
import wave

try:
    import miniaudio
    import numpy as np
    import requests
except ImportError as exc:  # pragma: no cover - dependency guidance
    raise SystemExit(
        "Install generator dependencies with: "
        "python3 -m pip install miniaudio numpy requests"
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "dist/voice/voice-script.json"
WORK = ROOT / ".work/voice-hf"
OUTPUT = ROOT / "content/voice"
BASE_URL = (
    "https://selfit-camera-trump-ai-voice.hf.space/gradio_api/call/"
    "generate_trump_voice_with_realtime_updates"
)
LANGUAGE = "\U0001F1FA\U0001F1F8 English"
SEPARATOR = "<pause:1.4>"
REQUESTS = 9
MAX_CHARS = 1799
SAMPLE_RATE = 16_000


def load_clips() -> list[dict[str, object]]:
    if not SCRIPT.exists():
        raise SystemExit("Run `python3 -m oot_trump prepare-voice` first.")
    return json.loads(SCRIPT.read_text(encoding="utf-8"))["clips"]


def pack(clips: list[dict[str, object]]) -> list[list[dict[str, object]]]:
    """Balanced longest-first packing that stays within the Space limit."""
    positions = {str(clip["file"]): index for index, clip in enumerate(clips)}
    bins: list[list[dict[str, object]]] = [[] for _ in range(REQUESTS)]
    sizes = [0] * REQUESTS
    weighted = sorted(
        clips,
        key=lambda clip: len(str(clip["text"])) + len(SEPARATOR),
        reverse=True,
    )
    for clip in weighted:
        weight = len(str(clip["text"])) + len(SEPARATOR)
        candidates = [
            index
            for index in range(REQUESTS)
            if sizes[index] + weight <= MAX_CHARS + len(SEPARATOR)
        ]
        if not candidates:
            raise SystemExit("The catalog no longer fits in nine legal requests.")
        target = min(candidates, key=lambda index: sizes[index])
        bins[target].append(clip)
        sizes[target] += weight
    for batch in bins:
        batch.sort(key=lambda clip: positions[str(clip["file"])])
        length = sum(len(str(clip["text"])) for clip in batch)
        length += len(SEPARATOR) * (len(batch) - 1)
        if length > MAX_CHARS:
            raise AssertionError(f"packed request is {length} characters")
    return bins


def generate_source(batch: list[dict[str, object]], number: int) -> Path:
    WORK.mkdir(parents=True, exist_ok=True)
    source = WORK / f"batch-{number:02d}.mp3"
    mapping = WORK / f"batch-{number:02d}-map.json"
    mapping.write_text(json.dumps(batch, indent=2) + "\n", encoding="utf-8")
    if source.exists() and source.stat().st_size:
        print(f"batch {number}/9: reusing {source.relative_to(ROOT)}", flush=True)
        return source

    text = SEPARATOR.join(str(clip["text"]) for clip in batch)
    response = requests.post(
        BASE_URL,
        json={"data": [text, LANGUAGE]},
        timeout=30,
    )
    response.raise_for_status()
    event_id = response.json()["event_id"]
    (WORK / f"batch-{number:02d}-event.txt").write_text(
        event_id + "\n", encoding="utf-8"
    )
    print(f"batch {number}/9: accepted ({len(batch)} clips)", flush=True)

    audio_url = None
    event_name = None
    event_log: list[str] = []
    with requests.get(
        f"{BASE_URL}/{event_id}", stream=True, timeout=(30, 360)
    ) as stream:
        stream.raise_for_status()
        for raw in stream.iter_lines(decode_unicode=True):
            if not raw:
                continue
            event_log.append(raw)
            if raw.startswith("event: "):
                event_name = raw[7:]
                continue
            if not raw.startswith("data: "):
                continue
            if event_name == "error":
                raise RuntimeError(f"batch {number} queue error: {raw[6:]}")
            try:
                data = json.loads(raw[6:])
            except json.JSONDecodeError:
                continue
            if isinstance(data, list) and data:
                status = str(data[0])
                if "maximum number of requests" in status:
                    raise RuntimeError(status)
                if "failed" in status.lower():
                    raise RuntimeError(status)
                if len(data) > 1 and isinstance(data[1], dict):
                    audio_url = data[1].get("url") or audio_url
    (WORK / f"batch-{number:02d}-sse.txt").write_text(
        "\n".join(event_log) + "\n", encoding="utf-8"
    )
    if not audio_url:
        raise RuntimeError(f"batch {number} completed without an audio URL")

    audio = requests.get(audio_url, timeout=120)
    audio.raise_for_status()
    source.write_bytes(audio.content)
    print(f"batch {number}/9: downloaded {len(audio.content):,} bytes", flush=True)
    return source


def quiet_runs(samples: np.ndarray, threshold: int = 100) -> list[tuple[int, int]]:
    window = 320  # 20 ms at 16 kHz
    starts = np.arange(0, len(samples), window)
    peaks = np.maximum.reduceat(np.abs(samples.astype(np.int32)), starts)
    silent = peaks < threshold
    runs: list[tuple[int, int]] = []
    start = None
    for index, is_silent in enumerate(silent):
        if is_silent and start is None:
            start = index
        elif not is_silent and start is not None:
            runs.append((start * window, min(index * window, len(samples))))
            start = None
    if start is not None:
        runs.append((start * window, len(samples)))
    return runs


def split_source(source: Path, batch: list[dict[str, object]]) -> None:
    decoded = miniaudio.decode_file(
        str(source),
        output_format=miniaudio.SampleFormat.SIGNED16,
        nchannels=1,
        sample_rate=SAMPLE_RATE,
    )
    samples = np.frombuffer(decoded.samples, dtype=np.int16).copy()
    expected = len(batch) - 1
    candidates = [
        run
        for run in quiet_runs(samples)
        if run[0] > SAMPLE_RATE // 5
        and run[1] < len(samples) - SAMPLE_RATE // 5
        and run[1] - run[0] >= int(1.0 * SAMPLE_RATE)
    ]
    if len(candidates) < expected:
        raise RuntimeError(
            f"{source.name}: found {len(candidates)} separators, expected {expected}"
        )
    # Intended pause tags are the longest silences.  Sort back into time order.
    separators = sorted(
        sorted(candidates, key=lambda run: run[1] - run[0], reverse=True)[:expected]
    )
    cuts = [0, *[(start + end) // 2 for start, end in separators], len(samples)]

    OUTPUT.mkdir(parents=True, exist_ok=True)
    for clip, start, end in zip(batch, cuts, cuts[1:]):
        segment = samples[start:end]
        audible = np.flatnonzero(np.abs(segment.astype(np.int32)) >= 100)
        if len(audible):
            pad = int(0.05 * SAMPLE_RATE)
            low = max(0, int(audible[0]) - pad)
            high = min(len(segment), int(audible[-1]) + pad)
            segment = segment[low:high]
        duration = len(segment) / SAMPLE_RATE
        if duration > 8.0:
            # The N64 contract is strict.  Preserve the complete line by applying
            # a small delivery-speed correction instead of truncating words.
            target_size = int(7.9 * SAMPLE_RATE)
            source_points = np.arange(len(segment), dtype=np.float64)
            target_points = np.linspace(
                0, len(segment) - 1, target_size, dtype=np.float64
            )
            segment = np.rint(np.interp(target_points, source_points, segment)).astype(
                np.int16
            )
            duration = len(segment) / SAMPLE_RATE
            print(
                f"{clip['file']}: speed-corrected to {duration:.3f}s",
                flush=True,
            )
        if duration <= 0:
            raise RuntimeError(
                f"{clip['file']}: generated empty audio"
            )
        destination = OUTPUT / str(clip["file"])
        with wave.open(str(destination), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(SAMPLE_RATE)
            output.writeframes(segment.astype("<i2", copy=False).tobytes())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--start-batch", type=int, default=1, choices=range(1, REQUESTS + 1)
    )
    args = parser.parse_args()
    clips = load_clips()
    batches = pack(clips)
    for number, batch in enumerate(batches, 1):
        if number < args.start_batch:
            continue
        source = generate_source(batch, number)
        split_source(source, batch)
        print(f"batch {number}/9: wrote {len(batch)} WAVs", flush=True)
        time.sleep(0.25)
    print(f"generated {len(clips)} catalog WAVs in {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
