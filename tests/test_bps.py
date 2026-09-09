from __future__ import annotations

import struct
import unittest
import zlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch as mock_patch

from oot_trump.bps import (
    apply_bps_patch,
    create_bps_patch,
    create_optimized_bps_patch,
)
from oot_trump.project import ProjectError


class BpsTests(unittest.TestCase):
    def create_fixture(self, source: bytes, target: bytes):
        directory = TemporaryDirectory()
        root = Path(directory.name)
        source_path = root / "base.z64"
        target_path = root / "mod.z64"
        patch_path = root / "mod.bps"
        source_path.write_bytes(source)
        target_path.write_bytes(target)
        info = create_bps_patch(
            source_path,
            target_path,
            patch_path,
            metadata="<bps><name>test</name></bps>",
        )
        return directory, patch_path.read_bytes(), info

    def test_patch_round_trip_handles_source_reads_literals_and_expansion(self) -> None:
        source = bytes(range(64)) * 4
        target = source[:70] + b"TRUMP" + source[75:] + b"\x00" * 80
        directory, patch, info = self.create_fixture(source, target)
        self.addCleanup(directory.cleanup)

        self.assertEqual(apply_bps_patch(source, patch), target)
        self.assertEqual(info.source_size, len(source))
        self.assertEqual(info.target_size, len(target))
        self.assertEqual(info.patch_size, len(patch))

    def test_identical_input_creates_a_small_patch(self) -> None:
        source = b"same bytes" * 100
        directory, patch, _info = self.create_fixture(source, source)
        self.addCleanup(directory.cleanup)

        self.assertLess(len(patch), 80)
        self.assertEqual(apply_bps_patch(source, patch), source)

    def test_repeated_expansion_uses_target_copy(self) -> None:
        source = b"header"
        target = source + b"\x00" * 4096
        directory, patch, _info = self.create_fixture(source, target)
        self.addCleanup(directory.cleanup)

        self.assertLess(len(patch), 128)
        self.assertEqual(apply_bps_patch(source, patch), target)

    def test_optimized_creator_invokes_delta_mode_and_verifies_output(self) -> None:
        source = b"clean source" * 20
        target = source[:30] + b"modified" + source[38:] + b"tail"
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "base.z64"
            target_path = root / "mod.z64"
            output_path = root / "release.bps"
            source_path.write_bytes(source)
            target_path.write_bytes(target)

            def fake_flips(command, check):
                self.assertTrue(check)
                self.assertEqual(command[1:4], ["--create", "--bps-delta-moremem", "--exact"])
                create_bps_patch(Path(command[-3]), Path(command[-2]), Path(command[-1]))

            with mock_patch("oot_trump.bps.subprocess.run", side_effect=fake_flips):
                info = create_optimized_bps_patch(
                    Path("/tools/flips"), source_path, target_path, output_path
                )

            self.assertEqual(apply_bps_patch(source, output_path.read_bytes()), target)
            self.assertEqual(info.path, output_path.resolve())

    def test_wrong_source_is_rejected(self) -> None:
        directory, patch, _info = self.create_fixture(b"right source", b"new target")
        self.addCleanup(directory.cleanup)

        with self.assertRaisesRegex(ProjectError, "source checksum mismatch"):
            apply_bps_patch(b"wrong source", patch)

    def test_corrupt_patch_is_rejected(self) -> None:
        source = b"source"
        directory, patch, _info = self.create_fixture(source, b"target")
        self.addCleanup(directory.cleanup)
        corrupt = bytearray(patch)
        corrupt[5] ^= 1

        with self.assertRaisesRegex(ProjectError, "patch checksum mismatch"):
            apply_bps_patch(source, bytes(corrupt))

    def test_target_checksum_is_enforced(self) -> None:
        source = b"source"
        directory, patch, _info = self.create_fixture(source, b"target")
        self.addCleanup(directory.cleanup)
        altered = bytearray(patch)
        footer = len(altered) - 12
        target_crc = struct.unpack("<I", altered[footer + 4 : footer + 8])[0]
        altered[footer + 4 : footer + 8] = struct.pack("<I", target_crc ^ 1)
        altered[-4:] = struct.pack("<I", zlib.crc32(altered[:-4]) & 0xFFFFFFFF)

        with self.assertRaisesRegex(ProjectError, "target checksum mismatch"):
            apply_bps_patch(source, bytes(altered))


if __name__ == "__main__":
    unittest.main()
