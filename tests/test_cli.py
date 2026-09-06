from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from oot_trump.cli import build, find_blender, path_for_blender, validate_model_tools
from oot_trump.project import ProjectError


class CliTests(unittest.TestCase):
    def test_find_blender_reports_wsl_install_boundary(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("oot_trump.cli.shutil.which", return_value=None),
        ):
            with self.assertRaisesRegex(ProjectError, "Windows Blender installation"):
                find_blender()

    def test_find_blender_accepts_configured_windows_executable(self) -> None:
        with patch("oot_trump.cli.shutil.which", return_value="/mnt/c/Blender/blender.exe"):
            self.assertEqual(find_blender(), "/mnt/c/Blender/blender.exe")

    def test_windows_blender_paths_are_converted_with_wslpath(self) -> None:
        completed = SimpleNamespace(stdout="\\\\wsl.localhost\\Debian\\home\\user\\oot\n")
        with patch("oot_trump.cli.subprocess.run", return_value=completed) as run:
            result = path_for_blender(Path("/home/user/oot"), "/mnt/c/Blender/blender.exe")

        self.assertEqual(result, r"\\wsl.localhost\Debian\home\user\oot")
        self.assertEqual(run.call_args.args[0], ["wslpath", "-w", "/home/user/oot"])

    def test_model_tool_validation_checks_fast64_operators(self) -> None:
        completed = SimpleNamespace(
            returncode=0,
            stdout="Blender 4.5.3\nOOT_TRUMP_MODEL_TOOLS_OK=4.5.3 LTS\n",
        )
        with (
            patch("oot_trump.cli.find_blender", return_value="/opt/blender/blender"),
            patch("oot_trump.cli.subprocess.run", return_value=completed) as run,
        ):
            blender = validate_model_tools()

        self.assertEqual(blender, "/opt/blender/blender")
        command = run.call_args.args[0]
        self.assertEqual(command[:2], ["/opt/blender/blender", "--background"])
        self.assertIn("oot_import_skeleton", command[-1])
        self.assertIn("oot_export_skeleton", command[-1])

    def test_model_tool_validation_surfaces_blender_failure(self) -> None:
        completed = SimpleNamespace(returncode=1, stdout="AssertionError: Fast64 is not enabled\n")
        with (
            patch("oot_trump.cli.find_blender", return_value="/opt/blender/blender"),
            patch("oot_trump.cli.subprocess.run", return_value=completed),
        ):
            with self.assertRaisesRegex(ProjectError, "Fast64 validation failed"):
                validate_model_tools()

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
