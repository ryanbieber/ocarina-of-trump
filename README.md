# Ocarina of Trump

A fictional parody mod for **The Legend of Zelda: Ocarina of Time** that turns
Navi into Trump: a tiny suited companion with revised dialogue, synthetic voice
clips, and an OoT-style fairy model. The humor aims to fit the adventure while
keeping the clues you need to finish it.

**Inspired by GORM THE OLD’s YouTube parody about Trump in Hyrule.** This is an
independent fan project, not an official adaptation or an endorsement by GORM
THE OLD, Nintendo, or Donald Trump. The dialogue and synthetic performances are
fictional parody, not authentic recordings or statements.

## What changes

- Trump fairy model with a curved face, matching skin colors, suit, and wings.
  The face turns toward the camera horizontally and animates during voice cues.
- 177 voiced English hint/advice messages, including 89 enemy advice entries.
- Six short replacement cues, including the familiar “Hey, listen” call.
- 29 additional story/warning rewrites, including “Trump, Trump, where art thou?”
  These preserve textbox flow; they do **not** have new full-page voice tracks.
- English Navi name references and the C-Up label become Trump. Other language
  slots are preserved.
- The title-screen subtitle reads **OCARINA OF TRUMP**. The main Zelda logo remains.

See the [complete change index](content/companion-change-index.md) for message
IDs, authored text, cue replacements, and implementation fixes. A
[JSON index](content/companion-change-index.json) is also available.

## Build and play

The documented environment is **WSL Debian with Windows Blender 5.2 and Fast64**.
You need Python 3.10+, build tools, and your own legally obtained **NTSC 1.0**
baserom. The repository includes the 183 production WAV files; voice generation
is not needed to build it. No ROM is included or distributed here.

1. Follow the [setup guide](docs/BUILDING.md#one-time-setup) to install dependencies
   and Fast64, then clone the repository inside WSL.
2. In Debian, from the repository root, select your Blender executable and build:

   ```bash
   export OOT_TRUMP_BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
   python3 -m oot_trump check-model-tools
   ./scripts/build-rom.sh "/absolute/path/to/your/ntsc-1.0-baserom.z64"
   ```

3. Open the resulting `.work/oot/build/ntsc-1.0/oot-ntsc-1.0.z64` in your emulator.
   Start it fresh instead of loading an old save state. See
   [Windows copying and launch instructions](docs/BUILDING.md#run-on-windows).

The build validates the input, prepares a pinned ZeldaRET checkout, exports the
model, applies text/title/audio changes, and compiles the English NTSC ROM. Your
original baserom is left untouched. Build products stay in ignored `.work/`.

## Verification status and limits

The latest implementation passes **45 unit tests**, content validation, voice
normalization checks, and a local NTSC 1.0 ROM build. The patched English message
table was also checked for remaining Navi names and stock Navi sound IDs.

**Runtime acceptance is still pending** for the latest audio/facing changes.
A successful build does not establish that the intro freeze or all playback
issues are resolved. Please cold-boot the new output and use the
[runtime checklist](docs/DEVELOPMENT.md#runtime-checklist) when reporting results.
Real-hardware compatibility has not been verified.

The rigid model has static wings. Replacing the shared fairy skeleton also
changes other fairy instances. Additional story rewrites are text plus existing
short cues where applicable, rather than a fully voiced story.

## Documentation and credits

- [Setup, build, run, and troubleshooting](docs/BUILDING.md)
- [Development, asset workflow, and testing](docs/DEVELOPMENT.md)
- [Complete companion change index](content/companion-change-index.md)
- [Voice provenance and synthetic-parody disclosure](content/voice-provenance.json)
- [Repository maintenance instructions](AGENTS.md)

Thanks to **GORM THE OLD** for the inspiration, and to the
[ZeldaRET](https://github.com/zeldaret/oot) and
[Fast64](https://github.com/Fast-64/fast64) projects for the tools this build uses.
The game and its original assets belong to their respective owners. Keep ROMs,
extracted game assets, and generated Blender/build files out of commits and uploads.
