# Repository maintenance guide

These instructions apply to the entire repository.

## Purpose and layout

This repository builds a clearly fictional English-language parody mod on top
of the pinned ZeldaRET OoT decomp. It must contain only original mod code and
rights-cleared generated assets, never a Nintendo ROM or extracted Nintendo
assets.

- `content/dialogue.en.json`: canonical English dialogue and voice filenames.
- `content/voice/`: the complete, tracked production WAV catalog.
- `oot_trump/`: validation, ZeldaRET patching, audio installation, and build CLI.
- `scripts/build_fairy_model.py`: canonical Blender/Fast64 model generator.
- `scripts/build-rom.sh`: canonical one-shot entry point.
- `.work/oot/`: ignored, pinned ZeldaRET checkout and generated build state.

## ROM and generated-file rules

- Never modify, overwrite, commit, copy, download, or redistribute the user's
  baserom. The build validates it and stages a copy under `.work/oot/baseroms/`.
- Supported input is NTSC 1.0 and its accepted MD5 values live in
  `config/project.json`. Do not expand this list without implementing and
  testing the corresponding ZeldaRET version.
- Never commit `.z64`, `.n64`, `.v64`, extracted ZeldaRET assets, `.work/`, or
  generated `.blend` files.
- The output ROM is `.work/oot/build/ntsc-1.0/oot-ntsc-1.0.z64`.
- Treat `.work/oot` as managed generated state. Preserve user changes in this
  repository, but it is valid for the build workflow to replace generated
  files inside that pinned checkout.

## Build invariants

- Keep ZeldaRET pinned to the revision in `config/project.json`.
- Every compile/setup invocation must pass `VERSION=ntsc-1.0 REGION=US`.
- Keep `patch_default_english_language` enabled. NTSC startup and new SRAM must
  select `LANGUAGE_ENG`; do not rely solely on incremental Make flags.
- Keep the `.oot-trump-region` cache marker behavior. ZeldaRET Make does not
  notice region flag changes, so an unmarked old build must be cleaned once.
- Use `COMPARE=0` for the modified ROM. A retail checksum mismatch is expected.
- Do not weaken a validation merely to make a build pass. Fix the generated
  source or build state that violated it.

Canonical Linux/WSL build:

```bash
OOT_TRUMP_BLENDER=/path/to/blender ./scripts/build-rom.sh /path/to/baserom.z64
```

Windows Blender may be launched from WSL by setting `OOT_TRUMP_BLENDER` to its
`/mnt/c/.../blender.exe` path. Keep the `wslpath` conversion and
`--python-exit-code 1`; without the latter Blender can leave a stale export
after a Python exception while returning success.

## Fast64 model invariants

- Restore pristine `fairy_skel.c/.h` from pinned Git before every import. Never
  import a model left by an earlier build retry.
- The exported symbol must remain `gFairySkel`, and the generated source must
  contain `TrumpFairy` geometry.
- `En_Elf` requires a rigid `SkeletonHeader`, not `FlexSkeletonHeader`. The
  entire joined mesh is deliberately assigned to one bone group.
- Bind the model to zero-based `gFairySkel` limb 7. `EnElf_OverrideLimbDraw`
  applies Navi's scale at the corresponding one-based draw limb 8.
- Center the measured vertical model bounds on the fairy pivot before export.
- Fast64's Blender 5.2 BSDF fallback does not enable exported colored lights
  by default. Preserve the explicit per-material F3D color transfer and alpha.
- Keep `trump_face/trump_face_smug_n64.png` at 32x32 RGBA. Convert it with
  Fast64's normal textured-material path, then apply `TEXEL0` alpha and
  `G_RM_AA_ZB_TEX_EDGE2` directly to the F3D material; Blender 5.2's named
  cutout-preset path is unreliable. Its runtime cost is 2 KiB as RGBA16, below
  the RDP's 4 KiB TMEM limit; do not point the exporter at the full-resolution
  source image or restore the former 64x64 RGBA version.
- Keep the matching talking frame at 32x32 RGBA. Fast64 exports both textures;
  the post-export patch routes the visible face through segment 9 and En_Elf
  alternates frames every four game frames only while a Trump voice is active.
- Keep export limits at or below 1,800 vertices and 16 materials unless the N64
  runtime budget is measured again.
- Fast64 overwrites `fairy_skel.c/.h`, which also house shared glow assets.
  Preserve the post-export glow merge and its `tex_len.h`,
  `circle_glow_textures.h`, and `gfx.h` dependencies.
- The rigid single-limb model intentionally has static wings. Changing to
  separately animated wings requires face-boundary-safe rigid meshes and an
  in-game draw-path test; do not casually introduce mixed-bone triangles.

Expected successful model log markers include:

```text
restored vanilla gFairySkel as the Fast64 import source
[NAVI-TRUMP] Centered refined model on Navi pivot and applied 0.42 scale
[NAVI-TRUMP] Validated 952+ model vertices against adult Link's near-model budget.
[NAVI-TRUMP] Applied explicit colors to 11 Fast64 materials.
[NAVI-TRUMP] Fast64 skeleton export completed.
preserved gameplay_keep glow assets alongside the Trump Fairy export
installed voice-synchronized Trump Navi mouth animation
validated Fast64 Trump Navi source replacement
```

## Dialogue and audio invariants

- Replace only the English `MSG(...)` slot. Preserve Japanese and all other
  language data.
- Preserve every `required_hint`; jokes must not obscure progression-critical
  instructions.
- The current catalog is exactly 177 single-page message clips plus six short
  Navi cue clips. Multi-page message audio is intentionally rejected until a
  page-advance playback hook is implemented.
- Filenames are deterministic: `trump_<message-id>_<page-index>.wav`.
- WAVs must be mono signed 16-bit PCM, 16 kHz, and no longer than eight seconds.
- Normalize every added or replaced WAV before committing:

```bash
python3 scripts/normalize_voice_catalog.py
python3 scripts/normalize_voice_catalog.py --check
```

- Active speech target is -20 dBFS within 0.5 dB; peak ceiling is -3 dBFS.
  Keep short edge fades to avoid click/spike artifacts.
- Keep the estimated VADPCM catalog within the 10 MiB configured budget.
- Soundfonts 38, 39, and 40 contain at most 64 effects each. Sequence 0's
  extended-page dispatch and voice-table limit must stay synchronized.
- Message start/continue starts a clip and message close stops it. Exercise
  rapid advance/close behavior after changing playback code.
- Stock Navi vocals must remain absent from patched ZeldaRET C sources. All six
  cue IDs must report through `OotTrump_IsVoicePlaying()` so the talking face
  animates for “Hey, listen,” targeting, talk-open, and introduction cues too.
- Face textures exported in `gameplay_keep` are segmented addresses. Preserve
  the `SEGMENTED_TO_VIRTUAL` conversion before assigning texture segment 9;
  using the symbol directly produces corrupted blue/green pixels.
- Keep `content/voice-provenance.json` complete and preserve the synthetic
  parody disclosure. Do not generate or replace performances without explicit
  user authorization and documented rights/permission.

## Required verification

Run before committing:

```bash
python3 -m py_compile oot_trump/*.py scripts/*.py tests/*.py
python3 -B -m unittest discover -s tests -v
python3 scripts/normalize_voice_catalog.py --check
python3 -m oot_trump validate-content
git diff --check
```

For documentation-only changes, the unit tests and `git diff --check` are the
minimum. A successful compile is not final runtime acceptance. Cold-boot the
new ROM rather than loading an old emulator save state, then test English file
select, model color/centering, ordinary hints, early and late enemy advice,
voice interruption, scene changes, and long-sample playback. Remember that
replacing shared `gFairySkel` affects other `En_Elf` fairy instances as well as
Navi.

When diagnosing logs, find the first compiler/linker/Python error rather than
the trailing `CalledProcessError`; later failures are usually consequences.
