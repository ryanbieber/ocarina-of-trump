# Development and validation

Read [AGENTS.md](../AGENTS.md) completely before changing the repository. Use
the [canonical build](BUILDING.md) for full model exports and ROM compilation.

## Source map

| Path | Purpose |
| --- | --- |
| `content/dialogue.en.json` | Canonical hint/dialogue definitions; the loaded manifest includes enemy advice. |
| `content/companion-story.en.json` | Additional story/warning rewrites with preserved message flow. |
| `content/companion-change-index.md` / `.json` | Human-readable and machine-readable change catalog. |
| `content/voice/` | 177 message WAVs and six short cue WAVs. |
| `content/voice-provenance.json` | Existing performances' provenance and parody disclosure. |
| `oot_trump/companion_patch.py` | English identity/story changes, embedded cues, HUD label, and model facing. |
| `oot_trump/audio_patch.py` | Soundfonts, immutable clip layers, playback hooks, and audio memory reservation. |
| `oot_trump/title_patch.py` | Original pixel lettering for the title subtitle. |
| `navi_trump_fast64_example.py` | Canonical model generator. |
| `config/project.json` | Pinned decomp revision, accepted ROM hashes, and audio limits. |
| `.work/oot/` | Ignored, managed ZeldaRET extraction and build state. |

Update both change-index formats when adding or changing a replacement. Record
its message/cue ID, text or behavior, voice coverage, and verification status.
Do not copy the game's entire extracted dialogue into the repository.

## Text and voice

Patch only English `MSG(...)` slots, retain progression-critical hints, and
preserve control codes, page breaks, and message chaining. The current voice
backend supports one-page message clips. Additional multi-page story rewrites
are text-only apart from existing short cues; do not imply full narration.

To inspect the production script and matching lookup generation:

```bash
python3 -m oot_trump prepare-voice
python3 -m oot_trump estimate-voice --words-per-minute 150
```

Do not generate or replace performances without explicit authorization and
documented permission/provenance. Existing provenance is recorded in
`content/voice-provenance.json`; the voice must remain labeled synthetic parody.
For authorized additions, use the manifest's deterministic filenames and mono
signed 16-bit PCM, 16 kHz WAVs, at most eight seconds each. Normalize and validate:

```bash
python3 scripts/normalize_voice_catalog.py
python3 scripts/normalize_voice_catalog.py --check
python3 -m oot_trump validate-content
```

Active speech targets -20 dBFS within 0.5 dB, with peaks at or below -3 dBFS and
short edge fades. Estimated VADPCM storage must remain within 10 MiB.
Incomplete-audio options are development aids, not release validation.

Each clip now has its own sequence layer. This avoids out-of-range short jumps
and mutation of shared note bytes. Soundfonts 38–40 use permanent metadata;
an extra 64 KiB audio heap reservation retains the original working pools.
Samples remain ROM-backed and DMA-cached. Exercise interruptions and scene
changes after any playback change; static validation cannot prove runtime safety.

## Model and title

The current model uses 1,349 vertices and 11 materials at default scale `0.42`.
Exports require 952–1,800 vertices and at most 16 materials. To adjust scale:

```bash
NAVI_TRUMP_MODEL_SCALE=0.38 ./scripts/build-rom.sh "/absolute/path/to/your/baserom.z64"
```

Keep the rigid `gFairySkel` binding to zero-based limb 7 (draw limb 8), the
centered pivot, and shared glow restoration. The canonical workflow restores
the pristine skeleton before import. Generated Blender files stay out of Git.

The calm and talking face textures are each 32×32 RGBA16 at runtime (2 KiB).
Preserve alpha cutout rendering and segmented-address conversion before loading
texture segment 9. The body skin color is sampled from the texture boundary and converted
from sRGB to linear for material assignment. Actor-facing yaw applies to Navi;
the shared model also affects other fairy instances. Wings remain static.

The title patch supplies original 96×8 I8 lettering in the subtitle's shadow and
foreground passes, retaining the existing fade/color behavior and main logo.

## Required checks

From the repository root, before committing:

```bash
python3 -m py_compile oot_trump/*.py scripts/*.py tests/*.py
python3 -B -m unittest discover -s tests -v
python3 scripts/normalize_voice_catalog.py --check
python3 -m oot_trump validate-content
git diff --check
```

After extraction, `python3 -m oot_trump apply --check` checks patch targets without
writing them. Build changes with the canonical command. Current results: 45
unit tests, strict content/normalization checks, and local compilation pass.
Latest runtime acceptance remains pending.

## Runtime checklist

Cold-boot the newly built ROM, without an older emulator save state, and record
the source commit and emulator/version with results:

- English title/file select and a fresh game's intro through Mido, Saria, and
  Link's house; no freeze, old Navi name, or stock “Hello”/call cue.
- Model color, centering, natural actor-facing orientation, and calm/talking transitions.
- C-Up label, ordinary hints, early and late enemy targeting/advice.
- Story message page breaks, player-name insertion, choices, and progression.
- Adult hints and Gerudo Fortress advice.
- Long clips, rapid advance/close, interrupted playback, and scene changes.
- Other fairy instances after replacing their shared skeleton.

Separate observed runtime results from unit-test/build results. Do not mark an
intro crash or audio issue resolved solely because compilation succeeds.

## Commit boundaries

Commit authored source, tests, documentation, and authorized production assets.
Never stage ROMs (`.z64`, `.n64`, `.v64`), `.work/`, extracted Nintendo assets, or
generated `.blend` files. Inspect `git diff --cached --name-only` before committing
and pushing; a local playable build is not a distributable repository artifact.
