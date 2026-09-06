from __future__ import annotations

import hashlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from oot_trump.project import ProjectConfig, ProjectError, stage_baserom


class ProjectTests(unittest.TestCase):
    def test_stage_baserom_validates_and_copies_to_expected_location(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "owned.z64"
            source.write_bytes(b"test baserom fixture")
            checksum = hashlib.md5(source.read_bytes()).hexdigest()
            config = replace(ProjectConfig.load(), baserom_md5=(checksum,))

            destination = stage_baserom(source, root / "oot", config)

            self.assertEqual(
                destination,
                root / "oot" / "baseroms" / config.version / "baserom.z64",
            )
            self.assertEqual(destination.read_bytes(), source.read_bytes())
            self.assertEqual(stage_baserom(source, root / "oot", config), destination)

    def test_stage_baserom_rejects_wrong_revision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "wrong.z64"
            source.write_bytes(b"wrong revision")
            with self.assertRaisesRegex(ProjectError, "Unsupported ntsc-1.0"):
                stage_baserom(source, Path(directory) / "oot", ProjectConfig.load())


if __name__ == "__main__":
    unittest.main()
