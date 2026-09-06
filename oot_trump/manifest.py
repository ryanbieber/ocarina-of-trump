from __future__ import annotations

import json
import math
import re
import sys
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .project import ProjectConfig, ROOT


MESSAGE_ID = re.compile(r"^0x[0-9A-Fa-f]{1,4}$")
VOICE_NAME = re.compile(r"^trump_[0-9a-f]{4}_[0-9]{2}\.wav$")
VOICE_ACTIVE_TARGET_DBFS = -20.0
VOICE_ACTIVE_TOLERANCE_DB = 0.5
VOICE_PEAK_CEILING_DBFS = -3.0


def _voice_levels(frames: bytes, sample_rate: int) -> tuple[float, float]:
    samples = array("h")
    samples.frombytes(frames)
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples:
        return -120.0, -120.0
    gate = 10 ** (-45.0 / 20.0)
    squares = 0
    count = 0
    window = max(1, sample_rate // 50)
    for start in range(0, len(samples), window):
        frame = samples[start : start + window]
        frame_squares = sum(value * value for value in frame)
        frame_rms = math.sqrt(frame_squares / len(frame)) / 32768.0
        if frame_rms >= gate:
            squares += frame_squares
            count += len(frame)
    active = math.sqrt(squares / count) / 32768.0 if count else 0.0
    peak = max(abs(value) for value in samples) / 32768.0
    active_db = 20.0 * math.log10(active) if active else -120.0
    peak_db = 20.0 * math.log10(peak) if peak else -120.0
    return active_db, peak_db


@dataclass(frozen=True)
class Page:
    lines: tuple[str, ...]
    voice: str


@dataclass(frozen=True)
class Dialogue:
    message_id: int
    context: str
    required_hint: str
    pages: tuple[Page, ...]


def load_manifest(path: Path | None = None) -> list[Dialogue]:
    source = path or ROOT / "content" / "dialogue.en.json"
    raw = json.loads(source.read_text(encoding="utf-8"))
    entries: list[Dialogue] = []
    for item in raw["dialogue"]:
        value = item["message_id"]
        if not isinstance(value, str) or not MESSAGE_ID.fullmatch(value):
            raise ValueError(f"Invalid message_id: {value!r}")
        entries.append(
            Dialogue(
                message_id=int(value, 16),
                context=item["context"].strip(),
                required_hint=item["required_hint"].strip(),
                pages=tuple(
                    Page(tuple(page["lines"]), page["voice"]) for page in item["pages"]
                ),
            )
        )
    for item in raw.get("enemies", []):
        enemy_id = item["enemy_id"]
        if isinstance(enemy_id, str):
            enemy_id = int(enemy_id, 0)
        message_id = 0x0600 + int(enemy_id)
        entries.append(
            Dialogue(
                message_id=message_id,
                context=f"Enemy targeting: {item['name']}",
                required_hint=item["required_hint"].strip(),
                pages=(
                    Page(
                        tuple(item["lines"]),
                        f"trump_{message_id:04x}_00.wav",
                    ),
                ),
            )
        )
    return entries


def validate_manifest(
    entries: Iterable[Dialogue],
    config: ProjectConfig,
    voice_dir: Path,
    allow_missing_audio: bool = False,
) -> list[str]:
    errors: list[str] = []
    estimated_vadpcm_bytes = 0
    missing_voice_files: list[Path] = []
    seen: set[int] = set()
    entries = list(entries)
    for entry in entries:
        label = f"0x{entry.message_id:04X}"
        if entry.message_id in seen:
            errors.append(f"{label}: duplicate message ID")
        seen.add(entry.message_id)
        if not entry.context:
            errors.append(f"{label}: context is required")
        if not entry.required_hint:
            errors.append(f"{label}: required_hint is required")
        if not entry.pages:
            errors.append(f"{label}: at least one page is required")
        for page_index, page in enumerate(entry.pages):
            expected_voice = f"trump_{entry.message_id:04x}_{page_index:02d}.wav"
            if page.voice != expected_voice:
                errors.append(f"{label} page {page_index}: voice must be {expected_voice}")
            if not VOICE_NAME.fullmatch(page.voice):
                errors.append(f"{label} page {page_index}: invalid voice filename")
            if not 1 <= len(page.lines) <= 4:
                errors.append(f"{label} page {page_index}: use one to four lines")
            for line in page.lines:
                if not line.strip():
                    errors.append(f"{label} page {page_index}: blank line")
                if len(line) > 36:
                    errors.append(
                        f"{label} page {page_index}: line exceeds 36 characters: {line!r}"
                    )
                if any(ord(char) < 32 for char in line):
                    errors.append(f"{label} page {page_index}: control character in text")
            voice = voice_dir / page.voice
            if not voice.exists():
                if not allow_missing_audio:
                    missing_voice_files.append(voice)
                continue
            try:
                with wave.open(str(voice), "rb") as stream:
                    if stream.getnchannels() != config.voice_channels:
                        errors.append(f"{voice}: must be mono")
                    if stream.getsampwidth() != config.voice_sample_width:
                        errors.append(f"{voice}: must be 16-bit PCM")
                    if stream.getframerate() != config.voice_sample_rate:
                        errors.append(
                            f"{voice}: expected {config.voice_sample_rate} Hz, "
                            f"found {stream.getframerate()} Hz"
                        )
                    duration = stream.getnframes() / max(1, stream.getframerate())
                    frames = stream.readframes(stream.getnframes())
                    active_db, peak_db = _voice_levels(frames, stream.getframerate())
                    if abs(active_db - VOICE_ACTIVE_TARGET_DBFS) > VOICE_ACTIVE_TOLERANCE_DB:
                        errors.append(
                            f"{voice}: active speech is {active_db:.2f} dBFS; "
                            f"normalize to {VOICE_ACTIVE_TARGET_DBFS:.1f} dBFS"
                        )
                    if peak_db > VOICE_PEAK_CEILING_DBFS + 0.05:
                        errors.append(
                            f"{voice}: peak is {peak_db:.2f} dBFS; "
                            f"ceiling is {VOICE_PEAK_CEILING_DBFS:.1f} dBFS"
                        )
                    # Nintendo 64 VADPCM frames encode 16 samples in 9 bytes.
                    estimated_vadpcm_bytes += ((stream.getnframes() + 15) // 16) * 9
                    estimated_vadpcm_bytes += 256  # conservative loop/book/table overhead
                    if duration > config.max_voice_seconds:
                        errors.append(
                            f"{voice}: {duration:.2f}s exceeds {config.max_voice_seconds:.2f}s"
                        )
            except (wave.Error, EOFError) as exc:
                errors.append(f"{voice}: invalid WAV: {exc}")

    if estimated_vadpcm_bytes > config.max_voice_vadpcm_bytes:
        errors.append(
            "estimated VADPCM voice bank is "
            f"{estimated_vadpcm_bytes / (1024 * 1024):.2f} MiB; "
            f"budget is {config.max_voice_vadpcm_bytes / (1024 * 1024):.2f} MiB"
        )
    if missing_voice_files:
        examples = ", ".join(path.name for path in missing_voice_files[:3])
        errors.append(
            f"missing {len(missing_voice_files)} voice WAVs in {voice_dir} "
            f"(first: {examples})"
        )

    required_quest_ids = {
        0x0140, 0x0141, 0x0142, 0x0143, 0x0144, 0x0145, 0x0146, 0x0147,
        0x0148, 0x0149, 0x014A, 0x014B, 0x014C, 0x014D, 0x014E, 0x0150,
        0x0151, 0x0152, 0x0153, 0x0154, 0x0155, 0x0156, 0x0157, 0x0158,
        0x015A, 0x015B, 0x015C, 0x015F,
    }
    required_infospot_ids = {
        0x0100, 0x0101, 0x0102, 0x0103, 0x0104, 0x0105, 0x0106, 0x0107,
        0x0108, 0x010C, 0x0114, 0x0115, 0x0116, 0x0119, 0x011F, 0x0124,
        0x0126, 0x0128, 0x0129, 0x012A, 0x012B, 0x012F, 0x0131, 0x0132,
        0x0133, 0x0137, 0x0139, 0x013A, 0x013D, 0x0180, 0x0181, 0x0183,
        0x0184, 0x0186, 0x0189, 0x018C, 0x018D, 0x018F, 0x0190, 0x0191,
        0x0192, 0x0194, 0x0195, 0x0197, 0x0198, 0x01A3, 0x01A5, 0x01A7,
        0x01A9, 0x01AB,
    }
    required_enemy_ids = set(range(0x0600, 0x065D)) - {0x060B, 0x062C, 0x0638, 0x063C}
    required_flow_ids = {
        0x00E0, 0x00E1, 0x00E3,
        0x0201, 0x0202, 0x0203, 0x0204, 0x020B, 0x0225,
    }
    missing = sorted(
        (required_quest_ids | required_infospot_ids | required_enemy_ids | required_flow_ids)
        - seen
    )
    if missing:
        errors.append(
            "manifest is missing required Navi IDs: "
            + ", ".join(f"0x{value:04X}" for value in missing)
        )
    return errors
