# Ocarina of Trump

A private, clearly fictional parody mod that replaces Navi's appearance,
English hints, enemy advice, and voice with Trump-themed material while
preserving Ocarina of Time's progression clues.

This repository contains only original mod code and assets. It does not contain
an Ocarina of Time ROM or extracted Nintendo assets. You must provide your own
legally obtained NTSC 1.0 baserom.

## Current state

- A low-poly Fast64 Trump fairy generator and preview blend.
- A complete v1 text catalog for Navi's active infospots, quest/flow messages,
  forced door advice, and all 89 used enemy advice IDs (`0x0600` through
  `0x065C`, excluding unused slots): 176 voiced message pages total.
- A provider-neutral AI voice production sheet, WAV validator, sample WAV,
  deterministic C lookup generator, and a 10 MiB estimated VADPCM budget.
- Generated sequence-0 playback using three 64-effect soundfonts, a 304-entry
  voice SFX table, and message open/continue/close hooks.
- A patcher that replaces only the English slot in ZeldaRET's extracted
  `message_data.h`, preserving Japanese and other language slots.
- A pinned ZeldaRET checkout/build CLI for NTSC 1.0.

The generated production voice WAVs are checked in so a clone contains the
complete voice catalog. The Fast64-exported in-game model and final ROM remain
generated outputs and are not checked in.

## Requirements

- Python 3.10+
- Git and the dependencies listed by
  [ZeldaRET OoT](https://github.com/zeldaret/oot)
- A supported NTSC 1.0 baserom
- Blender 4.x and Fast64 for model export
- Rights-cleared synthetic parody WAVs for voice-over

The build pins ZeldaRET commit
`cbe814b25455f14a343a7457c4b1c92af40ede6a`. Both accepted NTSC 1.0 baserom
MD5 hashes are recorded in `config/project.json`.

## One-shot build

After installing the requirements, build from a legally obtained NTSC 1.0
baserom with one command:

```bash
./scripts/build-rom.sh /absolute/path/to/baserom.z64
```

The full build first launches Blender in background mode and verifies that it
is Blender 4.x or 5.x with Fast64's OoT skeleton importer and exporter enabled. Run
the same preflight by itself with:

```bash
python3 -m oot_trump check-model-tools
```

The preflight uses Blender's registered RNA rather than the dynamic `bpy.ops`
attribute list. If Fast64 is installed but disabled, it attempts to enable the
add-on and save that Blender profile's preference before validating it.

For Blender 5.2, where Fast64 may load its OoT operators without registering
the legacy BSDF conversion operator, the model script calls Fast64's underlying
material converter directly and verifies that every exported material is F3D.

On WSL, either Linux Blender or Windows Blender can be used. For Windows
Blender, set `OOT_TRUMP_BLENDER` to its WSL path; the exporter automatically
converts the decomp, script, and output paths for Windows. For example:

```bash
OOT_TRUMP_BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" \
python3 -m oot_trump check-model-tools
```

The equivalent PowerShell flow uses WSL for ZeldaRET compilation and the
installed Windows copy of Blender/Fast64:

```powershell
$Blender = Get-ChildItem "$env:ProgramFiles\Blender Foundation\Blender *\blender.exe" | Sort-Object FullName -Descending | Select-Object -First 1
$WslBlender = (& wsl.exe wslpath -u $Blender.FullName).Trim()
$Rom = "C:\path\to\legally-obtained-baserom.z64"
$WslRom = (& wsl.exe wslpath -u $Rom).Trim()

& wsl.exe env "OOT_TRUMP_BLENDER=$WslBlender" bash -lc 'export PATH="$HOME/miniconda3/bin:$PATH"; cd ~/ocarina-of-trump && ./scripts/build-rom.sh "$1"' _ "$WslRom"
```

The one-shot command forces the NTSC build to `REGION=US` so the English
message slot is active. It validates the ROM before copying it, clones and pins ZeldaRET, runs
`make setup` when needed, exports the Trump Navi model through Blender/Fast64,
patches all English Navi dialogue, installs the voice soundfonts, and builds the
ROM. The result remains under `.work/oot/build/`. The command is safe to rerun;
it reuses an existing extraction and generated checkout.

For an audio-and-dialogue test ROM that retains vanilla Navi's model:

```bash
./scripts/build-rom.sh /absolute/path/to/baserom.z64 --skip-model
```

The command intentionally stops before downloading or compiling anything when
voice assets or their provenance are incomplete.

## Dialogue and voice workflow

Validate the authored text while voice production is in progress:

```bash
python3 -m oot_trump validate-content --allow-missing-audio
```

Generate `voice-script.json` for an AI audio workflow and the matching C lookup:

```bash
python3 -m oot_trump prepare-voice
```

Place the resulting files in `content/voice/`. Each file must be mono,
16-bit PCM, 16 kHz, no longer than eight seconds, and named exactly as specified
by the manifest (for example `trump_0601_00.wav`). Then update
`content/voice-provenance.json` with the generator, date, and applicable
license/permission information.

The voice is a fictional synthetic parody performance. It must not be labeled
or distributed as an authentic recording or statement.

Regenerate the included neutral test clip at any time:

```bash
python3 -B scripts/generate_sample_wav.py
```

After `make setup`, install just the WAVs currently present (useful for testing
the sample before the full recording pass):

```bash
python3 -m oot_trump install-voice --allow-missing-audio
```

The installer copies WAVs into ZeldaRET's sample tree, adds them to
`SampleBank_0`, creates soundfonts 38 through 40, extends sequence 0 and the voice
SFX table, generates the text-ID lookup, and hooks message start/continue/close.
It is idempotent, so rerun it after adding or replacing WAVs.

Strict validation checks every required message ID, textbox dimensions, audio
format/duration, consistent -20 dBFS active-speech loudness, a -3 dBFS peak
ceiling, deterministic filename, provenance, and the 10 MiB estimated
N64 VADPCM budget:

```bash
python3 scripts/normalize_voice_catalog.py
python3 scripts/normalize_voice_catalog.py --check
python3 -m oot_trump validate-content
```

At the current 2,534-word script length, expected compressed audio is roughly
8.7 MiB at typical delivery speed; the extra budget covers pauses, codebooks,
and table overhead. The audio belongs in ROM-backed `Audiotable` storage and
must be DMA-cached during playback rather than retained wholesale in RDRAM.

Recalculate the estimate after dialogue edits or for a different delivery rate:

```bash
python3 -m oot_trump estimate-voice --words-per-minute 150
```

## ZeldaRET setup and text patch

Clone the exact supported decomp revision into the ignored working directory:

```bash
python3 -m oot_trump setup
```

Place the NTSC 1.0 baserom at `.work/oot/baseroms/ntsc-1.0/baserom.z64`, then:

```bash
python3 -m oot_trump setup --run-make-setup
python3 -m oot_trump apply --check
python3 -m oot_trump apply
```

`apply --check` verifies that every manifest ID exists without writing to the
decomp. `apply` updates the English `MSG(...)` argument in the extracted text
file. A strict `build` requires all 176 voice files and completed provenance:

```bash
python3 -m oot_trump build
```

Generated ROMs remain inside `.work/oot/build/` and are ignored by Git. `build`
applies the English dialogue, installs the generated audio backend, and invokes
ZeldaRET. It stops before compilation if any production WAV is missing.

## Fast64 model workflow

The model script reads configuration from the environment and binds the rigid
replacement to Navi's central scaled display limb. The current generated wings
are static; this keeps the `SkeletonHeader` draw path required by `En_Elf`:

```bash
OOT_DECOMP_PATH="$PWD/.work/oot" \
NAVI_TRUMP_IMPORT=1 \
blender --background --python navi_trump_fast64_example.py
```

After inspecting the result, enable export:

```bash
OOT_DECOMP_PATH="$PWD/.work/oot" \
NAVI_TRUMP_IMPORT=1 \
NAVI_TRUMP_EXPORT=1 \
blender --background --python navi_trump_fast64_example.py
```

Export mode omits the preview glow and rejects models over 1,800 vertices or
16 materials. It retains the original `gFairySkel` structure expected by
`En_Elf`.

## Tests

```bash
python3 -B -m unittest discover -s tests -v
git diff --check
```

Final acceptance still requires emulator and real-hardware smoke testing of the
intro, quest hints, enemy targeting, Gerudo Fortress, adult hints, rapid text
skipping, scene changes, wing animation, and long-sample audio cache behavior.
