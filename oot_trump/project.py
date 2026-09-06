from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class ProjectError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProjectConfig:
    version: str
    oot_repository: str
    oot_revision: str
    baserom_md5: tuple[str, ...]
    message_data: str
    max_voice_seconds: float
    max_voice_vadpcm_bytes: int
    voice_sample_rate: int
    voice_channels: int
    voice_sample_width: int

    @classmethod
    def load(cls, path: Path | None = None) -> "ProjectConfig":
        source = path or ROOT / "config" / "project.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        return cls(
            version=data["version"],
            oot_repository=data["oot_repository"],
            oot_revision=data["oot_revision"],
            baserom_md5=tuple(data["baserom_md5"]),
            message_data=data["message_data"],
            max_voice_seconds=float(data["max_voice_seconds"]),
            max_voice_vadpcm_bytes=int(data["max_voice_vadpcm_bytes"]),
            voice_sample_rate=int(data["voice_sample_rate"]),
            voice_channels=int(data["voice_channels"]),
            voice_sample_width=int(data["voice_sample_width"]),
        )


HOST_TOOLCHAIN_VARIABLES = (
    "AR",
    "AS",
    "CC",
    "CFLAGS",
    "CPATH",
    "CPPFLAGS",
    "CPLUS_INCLUDE_PATH",
    "CXX",
    "CXXFLAGS",
    "LD",
    "LDFLAGS",
    "LIBRARY_PATH",
)


def clean_toolchain_environment() -> dict[str, str]:
    """Return an environment without host flags that break the N64 IDO compiler."""
    environment = os.environ.copy()
    for name in HOST_TOOLCHAIN_VARIABLES:
        environment.pop(name, None)
    return environment


def run(
    command: list[str],
    cwd: Path | None = None,
    *,
    clean_toolchain: bool = False,
) -> None:
    environment = clean_toolchain_environment() if clean_toolchain else None
    subprocess.run(command, cwd=cwd, env=environment, check=True)


def patch_armips_pthread(repo: Path) -> None:
    """Make the pinned armips build link correctly on modern Linux hosts."""
    makefile = repo / "tools" / "Makefile"
    try:
        source = makefile.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProjectError(f"Missing ZeldaRET tool Makefile: {makefile}") from exc
    armips_rule = (
        "\t$(CXX) $(WARNFLAGS) -std=c++17 $(OPTFLAGS) -s -fno-rtti -pipe "
        "-Wno-unused-parameter -Wno-sign-compare $< -o $@"
    )
    patched_rule = armips_rule.replace(" $< -o $@", " -pthread $< -o $@")
    if patched_rule in source:
        return
    if armips_rule not in source:
        raise ProjectError("Pinned ZeldaRET armips build rule was not found")
    makefile.write_text(source.replace(armips_rule, patched_rule, 1), encoding="utf-8")
    print("patched ZeldaRET armips linker flags (-pthread)")


def patch_default_english_language(repo: Path) -> None:
    """Force this English-language mod to start and initialize SRAM in English."""
    common_data = repo / "src" / "code" / "z_common_data.c"
    sram = repo / "src" / "code" / "z_sram.c"
    try:
        common_source = common_data.read_text(encoding="utf-8")
        sram_source = sram.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProjectError("Pinned ZeldaRET language sources were not found") from exc

    region_selection = """#if OOT_NTSC && OOT_VERSION < GC_US || PLATFORM_IQUE
    if (gCurrentRegion == REGION_JP) {
        gSaveContext.language = LANGUAGE_JPN;
    }
    if (gCurrentRegion == REGION_US) {
        gSaveContext.language = LANGUAGE_ENG;
    }
"""
    forced_english = """#if OOT_NTSC && OOT_VERSION < GC_US || PLATFORM_IQUE
    gSaveContext.language = LANGUAGE_ENG;
"""
    if region_selection in common_source:
        common_data.write_text(
            common_source.replace(region_selection, forced_english, 1), encoding="utf-8"
        )
    elif forced_english not in common_source:
        raise ProjectError("Pinned ZeldaRET startup language block was not found")

    japanese_sram = """#if OOT_NTSC
    LANGUAGE_JPN, // SRAM_HEADER_LANGUAGE
"""
    english_sram = """#if OOT_NTSC
    LANGUAGE_ENG, // SRAM_HEADER_LANGUAGE
"""
    if japanese_sram in sram_source:
        sram.write_text(sram_source.replace(japanese_sram, english_sram, 1), encoding="utf-8")
    elif english_sram not in sram_source:
        raise ProjectError("Pinned ZeldaRET SRAM language block was not found")
    print("forced NTSC startup and SRAM language to English")


def git_revision(repo: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True, capture_output=True
    )
    return result.stdout.strip()


def assert_oot_checkout(repo: Path, config: ProjectConfig) -> None:
    if not (repo / ".git").exists():
        raise ProjectError(f"Not a Git checkout: {repo}")
    revision = git_revision(repo)
    if revision != config.oot_revision:
        raise ProjectError(
            f"OoT revision mismatch: expected {config.oot_revision}, found {revision}"
        )


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_baserom(repo: Path, config: ProjectConfig) -> Path:
    base = repo / "baseroms" / config.version
    for name in ("baserom.z64", "baserom.n64", "baserom.v64"):
        candidate = base / name
        if candidate.exists():
            checksum = md5(candidate)
            if checksum not in config.baserom_md5:
                raise ProjectError(
                    f"Unsupported {config.version} baserom checksum: {checksum}"
                )
            return candidate
    raise ProjectError(f"Place a legally obtained baserom in {base}")


def stage_baserom(source: Path, repo: Path, config: ProjectConfig) -> Path:
    """Validate and copy a user-supplied baserom into ZeldaRET's expected tree."""
    source = source.resolve()
    if not source.is_file():
        raise ProjectError(f"Baserom file not found: {source}")
    suffix = source.suffix.lower()
    if suffix not in {".z64", ".n64", ".v64"}:
        raise ProjectError("Baserom must use a .z64, .n64, or .v64 extension")
    checksum = md5(source)
    if checksum not in config.baserom_md5:
        raise ProjectError(f"Unsupported {config.version} baserom checksum: {checksum}")

    destination = repo / "baseroms" / config.version / f"baserom{suffix}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if md5(destination) != checksum:
            raise ProjectError(
                f"A different baserom already exists at {destination}; move it before retrying"
            )
        return destination
    shutil.copy2(source, destination)
    return destination
