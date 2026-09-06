from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from oot_trump.cli import (
    build,
    export_navi_model,
    find_blender,
    merge_fairy_shared_assets,
    path_for_blender,
    validate_exported_navi_model,
    validate_model_tools,
)
from oot_trump.project import ProjectError


class CliTests(unittest.TestCase):
    def test_trump_fairy_uses_one_rigid_model_bone(self) -> None:
        script = (Path(__file__).parent.parent / "navi_trump_fast64_example.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "model_bone_name = get_limb_bone(armature, FAIRY_MODEL_BONE).name",
            script,
        )
        self.assertIn(
            'model_group.add([vertex.index for vertex in mesh_obj.data.vertices], 1.0, "REPLACE")',
            script,
        )
        self.assertIn("FAIRY_MODEL_BONE = 7", script)
        self.assertNotIn("upper.add(", script)

    def test_trump_fairy_centers_geometry_and_exports_material_colors(self) -> None:
        script = (Path(__file__).parent.parent / "navi_trump_fast64_example.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("vertical_center = (min(vertical_bounds) + max(vertical_bounds)) * 0.5", script)
        self.assertIn("obj.location.z -= vertical_center", script)
        self.assertIn("f3d_mat.default_light_color = color", script)
        self.assertIn("f3d_mat.set_lights = True", script)
        self.assertIn('f3d_mat.combiner1.D_alpha = "PRIMITIVE"', script)

    def test_model_export_injects_settings_into_blender_python(self) -> None:
        with (
            patch(
                "oot_trump.cli.path_for_blender",
                side_effect=lambda path, _blender: "converted:" + Path(path).name,
            ),
            patch("oot_trump.cli.subprocess.run") as run,
            patch("oot_trump.cli.restore_vanilla_fairy_skeleton") as restore_skeleton,
            patch("oot_trump.cli.preserve_fairy_shared_assets") as preserve_assets,
            patch("oot_trump.cli.validate_exported_navi_model") as validate_export,
        ):
            export_navi_model(Path("/oot"), "/mnt/c/Blender/blender.exe")

        command = run.call_args.args[0]
        self.assertEqual(
            command[:5],
            [
                "/mnt/c/Blender/blender.exe",
                "--background",
                "--python-exit-code",
                "1",
                "--python-expr",
            ],
        )
        self.assertIn("OOT_DECOMP_PATH", command[-1])
        self.assertIn("converted:oot", command[-1])
        self.assertIn("NAVI_TRUMP_EXPORT", command[-1])
        self.assertIn("runpy.run_path", command[-1])
        restore_skeleton.assert_called_once_with(Path("/oot"))
        preserve_assets.assert_called_once_with(Path("/oot"))
        validate_export.assert_called_once_with(Path("/oot"))

    def test_fast64_export_retains_colocated_glow_assets(self) -> None:
        generated_header = "#ifndef FAIRY_SKEL_H\n#define FAIRY_SKEL_H\nextern SkeletonHeader gFairySkel;\n#endif\n"
        generated_source = '#include "fairy_skel.h"\nGfx TrumpFairy_Skin[] = {};\n'
        vanilla_header = (
            "extern Vtx gGlowCircleVtx[];\n"
            "extern Gfx gGlowCircleTextureLoadDL[8];\n"
            "extern Gfx gGlowCircleDL[4];\n"
            "extern StandardLimb gFairySkelLimb_0;\n"
        )
        vanilla_source = (
            "Vtx gGlowCircleVtx[] = { 0 };\n"
            "Gfx gGlowCircleTextureLoadDL[8] = { 0 };\n"
            "Gfx gGlowCircleDL[4] = { 0 };\n"
            "StandardLimb gFairySkelLimb_0 = { 0 };\n"
        )

        header, source = merge_fairy_shared_assets(
            generated_header, generated_source, vanilla_header, vanilla_source
        )

        self.assertIn("extern Gfx gGlowCircleTextureLoadDL[8];", header)
        self.assertLess(header.index("gGlowCircleTextureLoadDL"), header.index("#endif"))
        self.assertIn('#include "tex_len.h"', header)
        self.assertIn('#include "circle_glow_textures.h"', source)
        self.assertIn('#include "gfx.h"', source)
        self.assertIn("Gfx gGlowCircleDL[4]", source)
        self.assertIn("TrumpFairy_Skin", source)

    def test_exported_model_must_replace_gfairyskel_with_trump_geometry(self) -> None:
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            source = repo / "assets/objects/gameplay_keep/fairy_skel.c"
            source.parent.mkdir(parents=True)
            source.write_text("SkeletonHeader gFairySkel;\n", encoding="utf-8")
            with self.assertRaisesRegex(ProjectError, "missing: TrumpFairy"):
                validate_exported_navi_model(repo)

            source.write_text(
                "FlexSkeletonHeader gFairySkel; Gfx TrumpFairy_Skin[] = {};\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ProjectError, "requires rigid vertex binding"):
                validate_exported_navi_model(repo)

            source.write_text(
                "SkeletonHeader gFairySkel; Gfx TrumpFairy_Skin[] = {};\n",
                encoding="utf-8",
            )
            validate_exported_navi_model(repo)

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
        self.assertEqual(command[2:5], ["--python-exit-code", "1", "--python"])
        self.assertTrue(command[-1].endswith("scripts/blender_fast64_preflight.py"))

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
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            marker = repo / "build/ntsc-1.0/.oot-trump-region"
            marker.parent.mkdir(parents=True)
            marker.write_text("US\n", encoding="utf-8")
            with (
                patch("oot_trump.cli.validate", return_value=[]),
                patch("oot_trump.cli.ProjectConfig.load", return_value=config),
                patch("oot_trump.cli.apply"),
                patch("oot_trump.cli.load_manifest", return_value=[]),
                patch("oot_trump.cli.install_audio_backend", return_value=176),
                patch("oot_trump.cli.run") as run,
            ):
                build(repo)

        run.assert_called_once_with(
            ["make", "VERSION=ntsc-1.0", "REGION=US", "COMPARE=0"],
            cwd=repo,
            clean_toolchain=True,
        )

    def test_mod_build_clears_objects_from_an_unmarked_region_build(self) -> None:
        config = SimpleNamespace(version="ntsc-1.0")
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            with (
                patch("oot_trump.cli.validate", return_value=[]),
                patch("oot_trump.cli.ProjectConfig.load", return_value=config),
                patch("oot_trump.cli.apply"),
                patch("oot_trump.cli.load_manifest", return_value=[]),
                patch("oot_trump.cli.install_audio_backend", return_value=176),
                patch("oot_trump.cli.run") as run,
            ):
                build(repo)

            self.assertEqual(run.call_count, 2)
            self.assertEqual(
                run.call_args_list[0].args[0],
                ["make", "clean", "VERSION=ntsc-1.0", "REGION=US"],
            )
            self.assertEqual(
                run.call_args_list[1].args[0],
                ["make", "VERSION=ntsc-1.0", "REGION=US", "COMPARE=0"],
            )
            self.assertEqual(
                (repo / "build/ntsc-1.0/.oot-trump-region").read_text(encoding="utf-8"),
                "US\n",
            )

    def test_full_build_requires_complete_voice_inputs(self) -> None:
        missing = "missing 175 voice WAVs in /unused/content/voice"
        with patch("oot_trump.cli.validate", return_value=[missing]):
            with self.assertRaisesRegex(ProjectError, "missing 175 voice WAVs"):
                build(Path("/unused"))


if __name__ == "__main__":
    unittest.main()
