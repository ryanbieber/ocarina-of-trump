from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from oot_trump.cli import build
from oot_trump.project import ProjectError


class CliTests(unittest.TestCase):
    def test_mod_build_disables_retail_rom_comparison(self) -> None:
        config = SimpleNamespace(version="ntsc-1.0")
        with (
            patch("oot_trump.cli.validate", return_value=[]),
            patch("oot_trump.cli.ProjectConfig.load", return_value=config),
            patch("oot_trump.cli.apply"),
            patch("oot_trump.cli.load_manifest", return_value=[]),
            patch("oot_trump.cli.install_audio_backend", return_value=176),
            patch("oot_trump.cli.run") as run,
        ):
            build(Path("/oot"))

        run.assert_called_once_with(
            ["make", "VERSION=ntsc-1.0", "COMPARE=0"],
            cwd=Path("/oot"),
            clean_toolchain=True,
        )

    def test_full_build_requires_complete_voice_inputs(self) -> None:
        missing = "missing 175 voice WAVs in /unused/content/voice"
        with patch("oot_trump.cli.validate", return_value=[missing]):
            with self.assertRaisesRegex(ProjectError, "missing 175 voice WAVs"):
                build(Path("/unused"))


if __name__ == "__main__":
    unittest.main()
