from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .audio_patch import install_audio_backend
from .manifest import load_manifest, load_voice_cues, validate_manifest, validate_voice_cues
from .message_patch import MessagePatchError, patch_file
from .project import (
    ProjectConfig,
    ProjectError,
    ROOT,
    assert_oot_checkout,
    find_baserom,
    md5,
    patch_armips_pthread,
    patch_default_english_language,
    run,
    stage_baserom,
)
from .title_patch import patch_title_screen
from .companion_patch import apply_companion
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
    preflight = path_for_blender(ROOT / "scripts" / "blender_fast64_preflight.py", blender)
    try:
        result = subprocess.run(
            [blender, "--background", "--python-exit-code", "1", "--python", preflight],
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
    patch_default_english_language(repo)
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
    cue_errors, _cue_bytes = validate_voice_cues(
        load_voice_cues(), config, ROOT / "content" / "voice", allow_missing_audio
    )
    errors.extend(cue_errors)
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
    patch_title_screen(repo, check=check)
    apply_companion(repo, check=check)


def build(repo: Path) -> None:
    config = ProjectConfig.load()
    errors = validate(allow_missing_audio=False)
    if errors:
        raise ProjectError("content validation failed:\n- " + "\n- ".join(errors))
    region_marker = repo / "build" / config.version / ".oot-trump-region"
    try:
        cached_region = region_marker.read_text(encoding="utf-8").strip()
    except OSError:
        cached_region = ""
    if cached_region != "US":
        print("clearing cached ZeldaRET objects so REGION=US is applied")
        run(
            ["make", "clean", f"VERSION={config.version}", "REGION=US"],
            cwd=repo,
            clean_toolchain=True,
        )

    apply(repo, check=False)
    count = install_audio_backend(
        repo, load_manifest(), config, require_all=True, cues=load_voice_cues()
    )
    print(f"installed {count} voice clips into ZeldaRET")
    run(
        ["make", f"VERSION={config.version}", "REGION=US", "COMPARE=0"],
        cwd=repo,
        clean_toolchain=True,
    )
    region_marker.parent.mkdir(parents=True, exist_ok=True)
    region_marker.write_text("US\n", encoding="utf-8")


def validate_exported_navi_model(repo: Path) -> None:
    source = repo / "assets" / "objects" / "gameplay_keep" / "fairy_skel.c"
    try:
        data = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProjectError(f"Fast64 did not produce the expected model source: {source}") from exc
    if "FlexSkeletonHeader gFairySkel" in data:
        raise ProjectError(
            "Fast64 exported Trump Navi as a flex skeleton; En_Elf requires rigid vertex binding"
        )
    missing = [marker for marker in ("gFairySkel", "TrumpFairy") if marker not in data]
    if missing:
        raise ProjectError(
            "Fast64 completed without replacing Navi's compiled skeleton; "
            f"{source} is missing: {', '.join(missing)}"
        )
    print("validated Fast64 Trump Navi source replacement")


def _between(data: str, start: str, end: str, label: str) -> str:
    start_index = data.find(start)
    end_index = data.find(end, start_index + len(start))
    if start_index < 0 or end_index < 0:
        raise ProjectError(f"Could not preserve vanilla {label} around the Fast64 export")
    return data[start_index:end_index].rstrip() + "\n"


def merge_fairy_shared_assets(
    generated_header: str,
    generated_source: str,
    vanilla_header: str,
    vanilla_source: str,
) -> tuple[str, str]:
    """Put gameplay_keep's non-fairy glow assets back after Fast64 overwrites the file."""
    header_assets = _between(
        vanilla_header,
        "extern Vtx gGlowCircleVtx[];",
        "extern StandardLimb gFairySkelLimb_0;",
        "fairy glow declarations",
    )
    source_assets = _between(
        vanilla_source,
        "Vtx gGlowCircleVtx[] = {",
        "StandardLimb gFairySkelLimb_0 = {",
        "fairy glow definitions",
    )
    if "gGlowCircleTextureLoadDL" not in generated_header:
        tex_len_include = '#include "tex_len.h"\n'
        if tex_len_include not in generated_header:
            first_line_end = generated_header.find("\n") + 1
            generated_header = (
                generated_header[:first_line_end]
                + tex_len_include
                + generated_header[first_line_end:]
            )
        closing_guard = generated_header.rfind("#endif")
        if closing_guard < 0:
            raise ProjectError("Fast64 fairy_skel.h has no closing include guard")
        generated_header = (
            generated_header[:closing_guard].rstrip()
            + "\n\n"
            + header_assets
            + "\n"
            + generated_header[closing_guard:]
        )
    if "gGlowCircleTextureLoadDL" not in generated_source:
        required_includes = ('#include "circle_glow_textures.h"\n', '#include "gfx.h"\n')
        first_line_end = generated_source.find("\n") + 1
        missing_includes = "".join(
            include for include in required_includes if include not in generated_source
        )
        generated_source = (
            generated_source[:first_line_end]
            + missing_includes
            + generated_source[first_line_end:]
        )
        generated_source = generated_source.rstrip() + "\n\n" + source_assets
    return generated_header, generated_source


def read_pinned_oot_file(repo: Path, relative: Path) -> str:
    try:
        return subprocess.run(
            ["git", "show", f"HEAD:{relative.as_posix()}"],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ProjectError(f"Could not load pinned ZeldaRET file: {relative}") from exc


def restore_vanilla_fairy_skeleton(repo: Path) -> None:
    """Ensure Fast64 imports the pinned skeleton rather than a prior generated retry."""
    relative_base = Path("assets/objects/gameplay_keep/fairy_skel")
    for suffix in (".h", ".c"):
        relative = relative_base.with_suffix(suffix)
        destination = repo / relative
        destination.write_text(read_pinned_oot_file(repo, relative), encoding="utf-8")
    print("restored vanilla gFairySkel as the Fast64 import source")


def preserve_fairy_shared_assets(repo: Path) -> None:
    """Recover assets colocated with gFairySkel that Fast64 does not know about."""
    relative_base = Path("assets/objects/gameplay_keep/fairy_skel")
    header_path = repo / relative_base.with_suffix(".h")
    source_path = repo / relative_base.with_suffix(".c")
    try:
        vanilla_header = read_pinned_oot_file(repo, relative_base.with_suffix(".h"))
        vanilla_source = read_pinned_oot_file(repo, relative_base.with_suffix(".c"))
        generated_header = header_path.read_text(encoding="utf-8")
        generated_source = source_path.read_text(encoding="utf-8")
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ProjectError("Could not load fairy_skel assets for the Fast64 compatibility merge") from exc

    merged_header, merged_source = merge_fairy_shared_assets(
        generated_header, generated_source, vanilla_header, vanilla_source
    )
    header_path.write_text(merged_header, encoding="utf-8")
    source_path.write_text(merged_source, encoding="utf-8")
    print("preserved gameplay_keep glow assets alongside the Trump Fairy export")


def install_navi_face_animation(repo: Path) -> None:
    """Route Fast64's face texture through a runtime-selectable N64 segment."""
    skeleton_dir = repo / "assets" / "objects" / "gameplay_keep"
    source_path = skeleton_dir / "fairy_skel.c"
    header_path = skeleton_dir / "fairy_skel.h"
    actor_path = repo / "src" / "overlays" / "actors" / "ovl_En_Elf" / "z_en_elf.c"
    for path in (source_path, header_path, actor_path):
        if not path.is_file():
            raise ProjectError(f"missing ZeldaRET face-animation input: {path}")

    source = source_path.read_text(encoding="utf-8")
    texture_call = re.compile(
        r"gsDPSetTextureImage\(\s*[^,\n]+,\s*[^,\n]+,\s*[^,\n]+,\s*"
        r"(?P<symbol>[A-Za-z_]\w*)\s*\)"
    )
    symbols = {match.group("symbol") for match in texture_call.finditer(source)}
    # Fast64 5.2 derives texture symbols from the material and source filename,
    # ignoring the Blender image datablock name. Resolve each texture through
    # the generated face material display list instead of assuming a particular
    # texture symbol spelling.
    material_array = re.compile(
        r"\bGfx\s+(?P<material>[A-Za-z_]\w*)\s*\[\s*\]\s*=\s*\{"
        r"(?P<body>.*?)^\s*\};",
        flags=re.DOTALL | re.MULTILINE,
    )
    idle_candidates: set[str] = set()
    talking_candidates: set[str] = set()
    discovered_materials = []
    for match in material_array.finditer(source):
        material = match.group("material")
        normalized = re.sub(r"[^a-z0-9]", "", material.lower())
        if "trumpfairyface" not in normalized:
            continue
        discovered_materials.append(material)
        loaded_texture = texture_call.search(match.group("body"))
        if loaded_texture is None:
            continue
        symbol = loaded_texture.group("symbol")
        if "talking" in normalized:
            talking_candidates.add(symbol)
        else:
            idle_candidates.add(symbol)

    # Retain compatibility with older Fast64 exports that honored the explicit
    # Blender image names even if their material arrays were formatted in an
    # unexpected way.
    if not idle_candidates:
        idle_candidates.update(
            symbol
            for symbol in symbols
            if "TrumpFairyFaceTexture" in symbol and "Talking" not in symbol
        )
    if not talking_candidates:
        talking_candidates.update(
            symbol for symbol in symbols if "TrumpFairyFaceTalkingTexture" in symbol
        )
    idle_candidates = sorted(idle_candidates)
    talking_candidates = sorted(talking_candidates)
    if len(idle_candidates) != 1 or len(talking_candidates) != 1:
        raise ProjectError(
            "Fast64 face export must contain exactly one idle and one talking texture "
            f"(found idle={idle_candidates}, talking={talking_candidates}, "
            f"face materials={discovered_materials})"
        )
    idle_symbol = idle_candidates[0]
    talking_symbol = talking_candidates[0]

    def use_dynamic_segment(match: re.Match[str]) -> str:
        if match.group("symbol") != idle_symbol:
            return match.group(0)
        return match.group(0).replace(idle_symbol, "0x09000000")

    source, replacement_count = texture_call.subn(use_dynamic_segment, source)
    if replacement_count < 1 or "0x09000000" not in source:
        raise ProjectError("could not route the idle Trump face texture through segment 9")
    source_path.write_text(source, encoding="utf-8")

    declarations = []
    for symbol in (idle_symbol, talking_symbol):
        declaration = re.search(
            rf"\b(?P<type>u8|u16|u32|u64)\s+{re.escape(symbol)}\s*\[", source
        )
        if declaration is None:
            raise ProjectError(f"could not determine Fast64 texture type for {symbol}")
        declarations.append(f"extern {declaration.group('type')} {symbol}[];")

    header = header_path.read_text(encoding="utf-8")
    header_start = "/* OOT_TRUMP_FACE_TEXTURES_START */"
    header_end = "/* OOT_TRUMP_FACE_TEXTURES_END */"
    header_block = "\n".join([header_start, *declarations, header_end])
    if header_start in header:
        header = re.sub(
            re.escape(header_start) + r".*?" + re.escape(header_end),
            header_block,
            header,
            flags=re.DOTALL,
        )
    else:
        endif = header.rfind("#endif")
        if endif < 0:
            raise ProjectError("Fast64 fairy_skel.h has no closing #endif")
        header = header[:endif] + header_block + "\n\n" + header[endif:]
    header_path.write_text(header, encoding="utf-8")

    actor = actor_path.read_text(encoding="utf-8")
    segmented_include = '#include "segmented_address.h" /* OOT_TRUMP_FACE_SEGMENTS */'
    if segmented_include not in actor:
        include_anchor = '#include "assets/objects/gameplay_keep/fairy_anim.h"'
        if include_anchor not in actor:
            raise ProjectError("En_Elf face-animation include anchor not found")
        actor = actor.replace(include_anchor, segmented_include + "\n" + include_anchor, 1)
    declaration = "extern s32 OotTrump_IsVoicePlaying(void); /* OOT_TRUMP_FACE_VOICE_STATE */"
    if declaration not in actor:
        include_anchor = '#include "assets/objects/gameplay_keep/fairy_anim.h"'
        if include_anchor not in actor:
            raise ProjectError("En_Elf face-animation include anchor not found")
        actor = actor.replace(include_anchor, include_anchor + "\n\n" + declaration, 1)

    draw_anchor = "            POLY_XLU_DISP = SkelAnime_Draw("
    face_start = "            /* OOT_TRUMP_FACE_SEGMENT_START */"
    face_end = "            /* OOT_TRUMP_FACE_SEGMENT_END */"
    face_block = "\n".join(
        [
            face_start,
            "            gSPSegment(POLY_XLU_DISP++, 0x09,",
            "                       SEGMENTED_TO_VIRTUAL(",
            "                           ((this->actor.params == FAIRY_NAVI) && OotTrump_IsVoicePlaying() &&",
            "                            ((this->timer >> 2) & 1))",
            f"                               ? {talking_symbol}",
            f"                               : {idle_symbol}));",
            face_end,
        ]
    )
    if face_start in actor:
        actor = re.sub(
            re.escape(face_start) + r".*?" + re.escape(face_end),
            face_block,
            actor,
            flags=re.DOTALL,
        )
    elif draw_anchor in actor:
        actor = actor.replace(draw_anchor, face_block + "\n" + draw_anchor, 1)
    else:
        raise ProjectError("En_Elf skeleton draw anchor not found")
    actor_path.write_text(actor, encoding="utf-8")
    print("installed voice-synchronized Trump Navi mouth animation")


def export_navi_model(repo: Path, blender: str | None = None) -> None:
    if blender is None:
        blender = validate_model_tools()
    restore_vanilla_fairy_skeleton(repo)
    settings = {
        "OOT_DECOMP_PATH": path_for_blender(repo, blender),
        "NAVI_TRUMP_IMPORT": "1",
        "NAVI_TRUMP_EXPORT": "1",
        "NAVI_TRUMP_BLEND_OUTPUT": path_for_blender(
            ROOT / ".work" / "navi_trump_export.blend", blender
        ),
        # Explicit injection also makes this knob work when a Windows Blender
        # process is launched from WSL, where Linux environment inheritance is
        # otherwise inconsistent.
        "NAVI_TRUMP_MODEL_SCALE": os.environ.get("NAVI_TRUMP_MODEL_SCALE", "0.42"),
    }
    script = path_for_blender(ROOT / "navi_trump_fast64_example.py", blender)
    # Linux environment variables are not automatically inherited by a Win32
    # process launched through WSL. Inject the settings in Blender's Python so
    # this behaves identically with Linux Blender and Windows blender.exe.
    expression = (
        f"import os, runpy; os.environ.update({settings!r}); "
        f"runpy.run_path({script!r}, run_name='__main__')"
    )
    subprocess.run(
        [blender, "--background", "--python-exit-code", "1", "--python-expr", expression],
        cwd=ROOT,
        check=True,
    )
    preserve_fairy_shared_assets(repo)
    install_navi_face_animation(repo)
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
                repo,
                load_manifest(),
                config,
                require_all=not args.allow_missing_audio,
                cues=load_voice_cues(),
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
            export_voice_script(
                entries, output / "voice-script.json", cues=load_voice_cues()
            )
            generate_voice_map(entries, output / "trump_voice_map.inc.c")
            print(f"wrote voice production files to {output}")
        elif args.command == "estimate-voice":
            if args.words_per_minute <= 0:
                raise ProjectError("--words-per-minute must be positive")
            estimate = estimate_script(
                load_manifest(), args.words_per_minute, cues=load_voice_cues()
            )
            print(json.dumps(estimate, indent=2))
        return 0
    except (MessagePatchError, ProjectError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
