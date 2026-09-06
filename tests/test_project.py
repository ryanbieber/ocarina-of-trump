from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from oot_trump.project import (
    ProjectConfig,
    ProjectError,
    clean_toolchain_environment,
    patch_armips_pthread,
    stage_baserom,
)


class ProjectTests(unittest.TestCase):
    def test_clean_toolchain_environment_removes_conda_compiler_flags(self) -> None:
        variables = {
            "CFLAGS": "-march=nocona",
            "CPPFLAGS": "-isystem /tmp/conda/include",
            "LDFLAGS": "-L/tmp/conda/lib",
        }
        with patch.dict(os.environ, variables):
            environment = clean_toolchain_environment()

        for name in variables:
            self.assertNotIn(name, environment)
        self.assertEqual(environment.get("PATH"), os.environ.get("PATH"))

    def test_armips_pthread_patch_is_idempotent(self) -> None:
        rule = (
            "armips: armips.cpp\n"
            "\t$(CXX) $(WARNFLAGS) -std=c++17 $(OPTFLAGS) -s -fno-rtti -pipe "
            "-Wno-unused-parameter -Wno-sign-compare $< -o $@\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            makefile = root / "tools" / "Makefile"
            makefile.parent.mkdir()
            makefile.write_text(rule, encoding="utf-8")

            patch_armips_pthread(root)
            first = makefile.read_text(encoding="utf-8")
            patch_armips_pthread(root)

            self.assertIn("-Wno-sign-compare -pthread $< -o $@", first)
            self.assertEqual(makefile.read_text(encoding="utf-8"), first)

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
