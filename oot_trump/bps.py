from __future__ import annotations

import hashlib
import os
import struct
import subprocess
import tempfile
import zlib
from dataclasses import dataclass
from pathlib import Path

from .project import ProjectError


MAGIC = b"BPS1"
SOURCE_READ = 0
TARGET_READ = 1
SOURCE_COPY = 2
TARGET_COPY = 3
MIN_COPY_LENGTH = 4
MIN_REPEAT_LENGTH = 8


@dataclass(frozen=True)
class BpsPatchInfo:
    path: Path
    source_size: int
    target_size: int
    patch_size: int
    source_crc32: int
    target_crc32: int
    patch_crc32: int
    source_md5: str
    target_sha256: str


def _encode_number(value: int) -> bytes:
    if value < 0:
        raise ValueError("BPS numbers cannot be negative")
    encoded = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value == 0:
            encoded.append(byte | 0x80)
            return bytes(encoded)
        encoded.append(byte)
        value -= 1


def _decode_number(data: bytes, offset: int, limit: int) -> tuple[int, int]:
    value = 0
    shift = 1
    while True:
        if offset >= limit:
            raise ProjectError("truncated BPS variable-length number")
        byte = data[offset]
        offset += 1
        value += (byte & 0x7F) * shift
        if byte & 0x80:
            return value, offset
        shift <<= 7
        value += shift
        if shift > 1 << 63:
            raise ProjectError("invalid BPS variable-length number")


def _encode_signed(value: int) -> bytes:
    return _encode_number((abs(value) << 1) | (1 if value < 0 else 0))


def _decode_signed(data: bytes, offset: int, limit: int) -> tuple[int, int]:
    value, offset = _decode_number(data, offset, limit)
    magnitude = value >> 1
    return (-magnitude if value & 1 else magnitude), offset


def _action(mode: int, length: int) -> bytes:
    if length <= 0:
        raise ValueError("BPS action length must be positive")
    return _encode_number(((length - 1) << 2) | mode)


def _same_source_run(source: bytes, target: bytes, offset: int) -> int:
    end = min(len(source), len(target))
    cursor = offset
    while cursor < end and source[cursor] == target[cursor]:
        cursor += 1
    return cursor - offset


def _repeat_run(target: bytes, offset: int) -> int:
    if offset == 0 or target[offset] != target[offset - 1]:
        return 0
    value = target[offset]
    cursor = offset + 1
    while cursor < len(target) and target[cursor] == value:
        cursor += 1
    return cursor - offset


def _build_patch_body(source: bytes, target: bytes, metadata: bytes) -> bytes:
    patch = bytearray(MAGIC)
    patch.extend(_encode_number(len(source)))
    patch.extend(_encode_number(len(target)))
    patch.extend(_encode_number(len(metadata)))
    patch.extend(metadata)

    target_offset = 0
    target_relative_offset = 0
    while target_offset < len(target):
        source_run = _same_source_run(source, target, target_offset)
        if source_run >= MIN_COPY_LENGTH:
            patch.extend(_action(SOURCE_READ, source_run))
            target_offset += source_run
            continue

        repeat_run = _repeat_run(target, target_offset)
        if repeat_run >= MIN_REPEAT_LENGTH:
            copy_offset = target_offset - 1
            patch.extend(_action(TARGET_COPY, repeat_run))
            patch.extend(_encode_signed(copy_offset - target_relative_offset))
            target_relative_offset = copy_offset + repeat_run
            target_offset += repeat_run
            continue

        literal_start = target_offset
        target_offset += 1
        while target_offset < len(target):
            if _same_source_run(source, target, target_offset) >= MIN_COPY_LENGTH:
                break
            if _repeat_run(target, target_offset) >= MIN_REPEAT_LENGTH:
                break
            target_offset += 1
        literal = target[literal_start:target_offset]
        patch.extend(_action(TARGET_READ, len(literal)))
        patch.extend(literal)
    return bytes(patch)


def _crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def apply_bps_patch(source: bytes, patch: bytes) -> bytes:
    """Apply and validate a BPS patch entirely in memory."""
    if len(patch) < 16 or patch[:4] != MAGIC:
        raise ProjectError("invalid BPS patch header")
    footer_offset = len(patch) - 12
    expected_source_crc, expected_target_crc, expected_patch_crc = struct.unpack(
        "<III", patch[footer_offset:]
    )
    if _crc32(patch[:-4]) != expected_patch_crc:
        raise ProjectError("BPS patch checksum mismatch")
    if _crc32(source) != expected_source_crc:
        raise ProjectError("BPS source checksum mismatch; use the exact supported baserom")

    offset = 4
    source_size, offset = _decode_number(patch, offset, footer_offset)
    target_size, offset = _decode_number(patch, offset, footer_offset)
    metadata_size, offset = _decode_number(patch, offset, footer_offset)
    if len(source) != source_size:
        raise ProjectError(
            f"BPS source size mismatch: expected {source_size}, found {len(source)}"
        )
    if offset + metadata_size > footer_offset:
        raise ProjectError("truncated BPS metadata")
    offset += metadata_size

    target = bytearray()
    source_relative_offset = 0
    target_relative_offset = 0
    while len(target) < target_size:
        action, offset = _decode_number(patch, offset, footer_offset)
        mode = action & 3
        length = (action >> 2) + 1
        if len(target) + length > target_size:
            raise ProjectError("BPS action exceeds declared target size")

        if mode == SOURCE_READ:
            start = len(target)
            end = start + length
            if end > len(source):
                raise ProjectError("BPS SourceRead exceeds source size")
            target.extend(source[start:end])
        elif mode == TARGET_READ:
            end = offset + length
            if end > footer_offset:
                raise ProjectError("truncated BPS TargetRead data")
            target.extend(patch[offset:end])
            offset = end
        elif mode == SOURCE_COPY:
            relative, offset = _decode_signed(patch, offset, footer_offset)
            source_relative_offset += relative
            end = source_relative_offset + length
            if source_relative_offset < 0 or end > len(source):
                raise ProjectError("BPS SourceCopy exceeds source size")
            target.extend(source[source_relative_offset:end])
            source_relative_offset = end
        elif mode == TARGET_COPY:
            relative, offset = _decode_signed(patch, offset, footer_offset)
            target_relative_offset += relative
            if target_relative_offset < 0 or target_relative_offset >= len(target):
                raise ProjectError("BPS TargetCopy references unavailable target data")
            for _ in range(length):
                if target_relative_offset >= len(target):
                    raise ProjectError("BPS TargetCopy exceeds available target data")
                target.append(target[target_relative_offset])
                target_relative_offset += 1

    if offset != footer_offset:
        raise ProjectError("unexpected data before BPS checksum footer")
    if _crc32(target) != expected_target_crc:
        raise ProjectError("BPS target checksum mismatch")
    return bytes(target)


def create_bps_patch(
    source_path: Path,
    target_path: Path,
    output_path: Path,
    *,
    metadata: str = "",
) -> BpsPatchInfo:
    """Create an atomic BPS file and verify that it reproduces the target."""
    source = source_path.read_bytes()
    target = target_path.read_bytes()
    metadata_bytes = metadata.encode("utf-8")
    body = _build_patch_body(source, target, metadata_bytes)
    source_crc = _crc32(source)
    target_crc = _crc32(target)
    patch_without_final_crc = body + struct.pack("<II", source_crc, target_crc)
    patch_crc = _crc32(patch_without_final_crc)
    patch = patch_without_final_crc + struct.pack("<I", patch_crc)

    if apply_bps_patch(source, patch) != target:
        raise ProjectError("generated BPS patch did not reproduce the built ROM")

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            dir=output_path.parent,
            prefix=output_path.name + ".",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(patch)
            temporary_name = stream.name
        os.replace(temporary_name, output_path)
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)

    return BpsPatchInfo(
        path=output_path,
        source_size=len(source),
        target_size=len(target),
        patch_size=len(patch),
        source_crc32=source_crc,
        target_crc32=target_crc,
        patch_crc32=patch_crc,
        source_md5=hashlib.md5(source).hexdigest(),
        target_sha256=hashlib.sha256(target).hexdigest(),
    )


def create_optimized_bps_patch(
    flips: Path,
    source_path: Path,
    target_path: Path,
    output_path: Path,
) -> BpsPatchInfo:
    """Create a delta BPS with Floating IPS and verify it independently."""
    source = source_path.read_bytes()
    target = target_path.read_bytes()
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output_path.parent,
            prefix=output_path.name + ".",
            suffix=".tmp.bps",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
        temporary_path.unlink()
        try:
            subprocess.run(
                [
                    str(flips),
                    "--create",
                    "--bps-delta-moremem",
                    "--exact",
                    str(source_path),
                    str(target_path),
                    str(temporary_path),
                ],
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ProjectError("Floating IPS could not create the BPS patch") from exc
        patch = temporary_path.read_bytes()
        if apply_bps_patch(source, patch) != target:
            raise ProjectError("generated BPS patch did not reproduce the built ROM")
        os.replace(temporary_path, output_path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    patch = output_path.read_bytes()
    footer_offset = len(patch) - 12
    source_crc, target_crc, patch_crc = struct.unpack("<III", patch[footer_offset:])
    return BpsPatchInfo(
        path=output_path,
        source_size=len(source),
        target_size=len(target),
        patch_size=len(patch),
        source_crc32=source_crc,
        target_crc32=target_crc,
        patch_crc32=patch_crc,
        source_md5=hashlib.md5(source).hexdigest(),
        target_sha256=hashlib.sha256(target).hexdigest(),
    )
