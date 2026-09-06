from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .audio_patch import install_audio_backend
from .manifest import load_manifest, validate_manifest
from .message_patch import MessagePatchError, patch_file
from .project import (
    ProjectConfig,
    ProjectError,
    ROOT,
    assert_oot_checkout,
    find_baserom,
    md5,
    patch_armips_pthread,
    run,
    stage_baserom,
)
from .voice import estimate_script, export_voice_script, generate_voice_map


DEFAULT_OOT_DIR = ROOT / ".work" / "oot"
BLENDER_ENV = "OOT_TRUMP_BLENDER"


def find_blender() -> str:
    """Locate the Blender executable used by the Fast64 exporter."""
    configured = os.environ.get(BLENDER_ENV, "blender")
    blender = shutil.which(configured)
    if blender is None:
        raise ProjectError(
            "Blender was not found in this environment. On WSL, the Windows "
            "Blender installation is not normally on the Linux PATH. Set "
            f"{BLENDER_ENV} to either a Linux `blender` binary or the WSL path "
            "to Windows `blender.exe`"
        )
    return blender


def is_windows_blender(blender: str) -> bool:
    return Path(os.path.realpath(blender)).suffix.lower() == ".exe"


def path_for_blender(path: Path, blender: str) -> str:
    """Convert WSL paths when invoking Blender's Windows build."""
    if not is_windows_blender(blender):
        return str(path)
    try:
        result = subprocess.run(
            ["wslpath", "-w", str(path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ProjectError(
            "Windows Blender was selected, but the build could not convert its "
            "Linux paths with `wslpath`. Run the build from WSL or select Linux Blender"
        ) from exc
    return result.stdout.strip()


def validate_model_tools() -> str:
    """Start Blender and prove that the required Fast64 OoT operators exist."""
    blender = find_blender()
    expression = "; ".join(
        (
            "import bpy",
            "version=bpy.app.version",
            "assert (4, 0, 0) <= version < (6, 0, 0), "
            "f'Ocarina of Trump requires Blender 4.x or 5.x; found {bpy.app.version_string}'",
            "assert hasattr(bpy.ops.object, 'oot_import_skeleton'), "
            "'Fast64 is not enabled or its OoT skeleton importer is unavailable'",
            "assert hasattr(bpy.ops.object, 'oot_export_skeleton'), "
            "'Fast64 is not enabled or its OoT skeleton exporter is unavailable'",
            "print('OOT_TRUMP_MODEL_TOOLS_OK=' + bpy.app.version_string)",
        )
    )
    try:
        result = subprocess.run(
            [blender, "--background", "--python-expr", expression],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProjectError("Blender/Fast64 validation timed out after 120 seconds") from exc

    marker = "OOT_TRUMP_MODEL_TOOLS_OK="
    success_line = next(
        (line.strip() for line in result.stdout.splitlines() if line.startswith(marker)),
        None,
    )
    if result.returncode != 0 or success_line is None:
        details = "\n".join(result.stdout.strip().splitlines()[-12:])
        message = (
            "Blender/Fast64 validation failed. Start this Linux Blender, enable "
            "Fast64 in its preferences, save preferences, and retry."
        )
        if details:
            message += "\nBlender output:\n" + details
        raise ProjectError(message)

    version = success_line.removeprefix(marker)
    print(f"validated Blender {version} with Fast64 OoT import/export")
    return blender


def bootstrap(repo: Path, config: ProjectConfig, setup: bool) -> None:
    if not repo.exists():
        repo.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", config.oot_repository, str(repo)])
    run(["git", "fetch", "origin", config.oot_revision], cwd=repo)
    run(["git", "checkout", "--detach", config.oot_revision], cwd=repo)
    patch_armips_pthread(repo)
    if setup:
        find_baserom(repo, config)
        run(
            ["make", "setup", f"VERSION={config.version}", "REGION=US"],
            cwd=repo,
            clean_toolchain=True,
        )


def validate(allow_missing_audio: bool) -> list[str]:
    config = ProjectConfig.load()
    entries = load_manifest()
    errors = validate_manifest(
        entries, config, ROOT / "content" / "voice", allow_missing_audio
    )
    provenance = ROOT / "content" / "voice-provenance.json"
    try:
        data = json.loads(provenance.read_text(encoding="utf-8"))
        if data.get("synthetic_parody") is not True:
            errors.append("voice provenance must declare synthetic_parody=true")
        if not allow_missing_audio:
            for field in ("generator", "generated_at", "license_or_permission", "disclosure"):
                value = data.get(field)
                if not value or str(value).startswith("TO BE"):
                    errors.append(f"voice provenance {field} is required before release")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid voice provenance: {exc}")
    return errors


def apply(repo: Path, check: bool) -> None:
    config = ProjectConfig.load()
    assert_oot_checkout(repo, config)
    path = repo / config.message_data
    if not path.exists():
        raise ProjectError(
            f"Missing extracted {path}; run setup with a supported baserom first"
        )
    patch_file(path, load_manifest(), check=check)


def build(repo: Path) -> None:
    config = ProjectConfig.load()
    errors = validate(allow_missing_audio=False)
    if errors:
        raise ProjectError("content validation failed:\n- " + "\n- ".join(errors))
    apply(repo, check=False)
    count = install_audio_backend(repo, load_manifest(), config, require_all=True)
    print(f"installed {count} voice clips into ZeldaRET")
    run(
        ["make", f"VERSION={config.version}", "REGION=US", "COMPARE=0"],
        cwd=repo,
        clean_toolchain=True,
    )


def validate_exported_navi_model(repo: Path) -> None:
    source = repo / "assets" / "objects" / "gameplay_keep" / "fairy_skel.c"
    try:
        data = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProjectError(f"Fast64 did not produce the expected model source: {source}") from exc
    missing = [marker for marker in ("gFairySkel", "TrumpFairy") if marker not in data]
    if missing:
        raise ProjectError(
            "Fast64 completed without replacing Navi's compiled skeleton; "
            f"{source} is missing: {', '.join(missing)}"
        )
    print("validated Fast64 Trump Navi source replacement")


def export_navi_model(repo: Path, blender: str | None = None) -> None:
    if blender is None:
        blender = validate_model_tools()
    environment = os.environ.copy()
    environment.update(
        {
            "OOT_DECOMP_PATH": path_for_blender(repo, blender),
            "NAVI_TRUMP_IMPORT": "1",
            "NAVI_TRUMP_EXPORT": "1",
            "NAVI_TRUMP_BLEND_OUTPUT": path_for_blender(
                ROOT / ".work" / "navi_trump_export.blend", blender
            ),
        }
    )
    subprocess.run(
        [
            blender,
            "--background",
            "--python",
            path_for_blender(ROOT / "navi_trump_fast64_example.py", blender),
        ],
        cwd=ROOT,
        env=environment,
        check=True,
    )
    validate_exported_navi_model(repo)


def build_rom(repo: Path, baserom: Path | None, skip_model: bool) -> None:
    """Run the complete reproducible build from a baserom to a patched ROM."""
    errors = validate(allow_missing_audio=False)
    if errors:
        raise ProjectError("content validation failed:\n- " + "\n- ".join(errors))

    config = ProjectConfig.load()
    # Validate an explicit input before cloning or running the expensive setup.
    if baserom is not None:
        source = baserom.resolve()
        if not source.is_file():
            raise ProjectError(f"Baserom file not found: {source}")
        if source.suffix.lower() not in {".z64", ".n64", ".v64"}:
            raise ProjectError("Baserom must use a .z64, .n64, or .v64 extension")
        checksum = md5(source)
        if checksum not in config.baserom_md5:
            raise ProjectError(f"Unsupported {config.version} baserom checksum: {checksum}")

    # Fail before cloning, extraction, or compilation if model tooling is not
    # usable in the environment that launched this one-shot build.
    blender = None if skip_model else validate_model_tools()

    bootstrap(repo, config, setup=False)
    if baserom is not None:
        destination = stage_baserom(baserom, repo, config)
        print(f"staged baserom at {destination}")
    else:
        find_baserom(repo, config)

    if not (repo / config.message_data).is_file():
        run(
            ["make", "setup", f"VERSION={config.version}", "REGION=US"],
            cwd=repo,
            clean_toolchain=True,
        )
    else:
        print("ZeldaRET extraction already exists; skipping make setup")

    if skip_model:
        print("skipping Fast64 Navi export (--skip-model)")
    else:
        export_navi_model(repo, blender)
    build(repo)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oot-trump")
    sub = parser.add_subparsers(dest="command", required=True)
    setup = sub.add_parser("setup", help="clone and optionally prepare the pinned OoT decomp")
    setup.add_argument("--oot-dir", type=Path, default=DEFAULT_OOT_DIR)
    setup.add_argument("--run-make-setup", action="store_true")
    validate_parser = sub.add_parser("validate-content", help="validate dialogue and voice assets")
    validate_parser.add_argument("--allow-missing-audio", action="store_true")
    apply_parser = sub.add_parser("apply", help="apply dialogue to an extracted OoT checkout")
    apply_parser.add_argument("--oot-dir", type=Path, default=DEFAULT_OOT_DIR)
    apply_parser.add_argument("--check", action="store_true")
    build_parser = sub.add_parser(
        "build", help="build once the expanded full-voice backend is installed"
    )
    build_parser.add_argument("--oot-dir", type=Path, default=DEFAULT_OOT_DIR)
    one_shot_parser = sub.add_parser(
        "build-rom", help="one-shot setup, patch, model export, and ROM build"
    )
    one_shot_parser.add_argument(
        "--baserom", type=Path, help="path to a legally obtained NTSC 1.0 baserom"
    )
    one_shot_parser.add_argument("--oot-dir", type=Path, default=DEFAULT_OOT_DIR)
    one_shot_parser.add_argument(
        "--skip-model", action="store_true", help="build with the existing vanilla fairy model"
    )
    sub.add_parser(
        "check-model-tools", help="validate Blender and the Fast64 OoT import/export operators"
    )
    install_parser = sub.add_parser(
        "install-voice", help="install available WAVs and generated soundfont playback"
    )
    install_parser.add_argument("--oot-dir", type=Path, default=DEFAULT_OOT_DIR)
    install_parser.add_argument("--allow-missing-audio", action="store_true")
    verify_parser = sub.add_parser("verify", help="run strict content and checkout checks")
    verify_parser.add_argument("--oot-dir", type=Path, default=DEFAULT_OOT_DIR)
    voice_parser = sub.add_parser(
        "prepare-voice", help="generate the provider-neutral AI recording script and C lookup"
    )
    voice_parser.add_argument("--output-dir", type=Path, default=ROOT / "dist" / "voice")
    estimate_parser = sub.add_parser(
        "estimate-voice", help="estimate PCM and N64 VADPCM storage from the script"
    )
    estimate_parser.add_argument("--words-per-minute", type=int, default=150)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        if args.command == "setup":
            bootstrap(args.oot_dir.resolve(), ProjectConfig.load(), args.run_make_setup)
        elif args.command == "validate-content":
            errors = validate(args.allow_missing_audio)
            if errors:
                print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
                return 1
            print("content validation passed")
        elif args.command == "apply":
            apply(args.oot_dir.resolve(), args.check)
            print("dialogue patch check passed" if args.check else "dialogue patch applied")
        elif args.command == "build":
            build(args.oot_dir.resolve())
        elif args.command == "build-rom":
            build_rom(
                args.oot_dir.resolve(),
                args.baserom.resolve() if args.baserom is not None else None,
                args.skip_model,
            )
        elif args.command == "check-model-tools":
            validate_model_tools()
        elif args.command == "install-voice":
            config = ProjectConfig.load()
            repo = args.oot_dir.resolve()
            assert_oot_checkout(repo, config)
            count = install_audio_backend(
                repo, load_manifest(), config, require_all=not args.allow_missing_audio
            )
            print(f"installed {count} voice clips into ZeldaRET")
        elif args.command == "verify":
            errors = validate(False)
            assert_oot_checkout(args.oot_dir.resolve(), ProjectConfig.load())
            if errors:
                raise ProjectError("content validation failed:\n- " + "\n- ".join(errors))
            apply(args.oot_dir.resolve(), check=True)
            print("verification passed")
        elif args.command == "prepare-voice":
            output = args.output_dir.resolve()
            output.mkdir(parents=True, exist_ok=True)
            entries = load_manifest()
            export_voice_script(entries, output / "voice-script.json")
            generate_voice_map(entries, output / "trump_voice_map.inc.c")
            print(f"wrote voice production files to {output}")
        elif args.command == "estimate-voice":
            if args.words_per_minute <= 0:
                raise ProjectError("--words-per-minute must be positive")
            estimate = estimate_script(load_manifest(), args.words_per_minute)
            print(json.dumps(estimate, indent=2))
        return 0
    except (MessagePatchError, ProjectError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
