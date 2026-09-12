# Ocarina of Trump

Navi is Trump now. That's the idea.

I saw [GORM THE OLD's video about Trump in Hyrule](https://www.youtube.com/watch?v=UkEZqnLr5Nc)
and thought it would be a funny, dumb thing to turn into a mod pack. It turns
Navi into a tiny Trump in a suit who flies around Hyrule, gives you advice, and
speaks with Trump-style synthetic voiceovers.

**Required game version:** The Legend of Zelda: Ocarina of Time, North American
NTSC-U 1.0 in big-endian `.z64` format. A clean matching ROM has MD5
`5bd1fe107bf8106b2ab6650abecd54d6`. Later revisions, PAL releases, and GameCube
versions are not supported.

<img src="docs/images/trump-fairy-turntable.gif" alt="A rotating Blender render of the Trump fairy, wearing a suit and fairy wings" width="420">

*A turntable rendered from the current Blender model. This isn't an in-game screenshot.*

## What's in it

- A Trump fairy model with a talking face. He follows Navi's direction instead
  of always staring at the camera.
- Rewritten English hints and enemy advice, with 177 voice clips and six short
  calls replacing things like “Hey, listen!”
- Navi's name changed to Trump in English dialogue and the C-Up label.
- 29 extra story and warning rewrites. Those aren't fully voiced.
- “Ocarina of Trump” under the Zelda logo on the title screen.

The jokes still leave the actual game hints intact. It's meant to be funny
without making every line the same Trump joke.

## Hear a few clips

[▶ Play or download the voice sample reel](https://github.com/ryanbieber/ocarina-of-trump/releases/download/v0.1/ocarina-of-trump-voice-samples.mp4)

The reel contains four clips from the game:

- “Hey, listen. We have a tremendous quest.”
- “A door ought to do one thing.”
- “All mouth, no results.”
- “Would I certify it? I would not.”

## The face needed some work

The old face looked pasted onto his head. We replaced the separate face piece
with one continuous head, gave the nose a proper shape, and simplified the
texture so the skin matches better.

| Earlier Blender model | Current Blender model |
| --- | --- |
| <img src="docs/images/head-before.png" alt="Earlier front view with the painted face overlay" width="300"> | <img src="docs/images/head-after.png" alt="Current front view with the face mapped onto the head" width="300"> |

[More pictures and a few notes](docs/MODEL.md) · [Full list of changes](content/companion-change-index.md)

## How to play

You'll need your own **North American NTSC-U 1.0 Ocarina of Time ROM**. There isn't a ROM download
in this repo. The voice files are already included.

The build uses **WSL Debian, Python 3.10+, and Blender with Fast64**. Our current
setup uses Windows Blender 5.2. Start with the
[setup and build guide](docs/BUILDING.md) if you haven't installed everything.
The build also creates a BPS patch that can be shared without sharing a ROM.

Once that's set up, run this from the repo folder in Debian:

```bash
export OOT_TRUMP_BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
python3 -m oot_trump check-model-tools
./scripts/build-rom.sh "/path/to/your/ntsc-1.0-baserom.z64"
```

Adjust the paths for your computer. The command creates the complete compressed
ROM under `.work/oot/build/ntsc-1.0/` and a verified patch such as
`dist/ocarina-of-trump-ntsc-1.0-5bd1fe10.bps`. The hash in the filename identifies
the exact clean ROM it accepts.

To use a BPS release, apply it to your own matching NTSC 1.0 ROM with
[Floating IPS](https://github.com/Sir-Walrus/Flips) or another BPS patcher, then
open the new `.z64` in your emulator. See the [patching guide](docs/PATCHING.md)
for the short version. Start fresh; don't load a save state from an older build.

## Still a work in progress

The ROM builds and all 53 tests pass. The latest audio and facing changes still
need more in-game testing, especially the intro. The wings don't flap, and
other fairies share the replacement model too. Real hardware hasn't been tested.

If something breaks, include your emulator/version, the build you're playing,
and where it happened. [Build help](docs/BUILDING.md#troubleshooting) and
[developer notes](docs/DEVELOPMENT.md) are here if you need them.

## Thanks

[GORM THE OLD](https://www.youtube.com/watch?v=UkEZqnLr5Nc) for the inspiration,
[ZeldaRET](https://github.com/zeldaret/oot) for
the decomp, and [Fast64](https://github.com/Fast-64/fast64) for the model tools.

This is an unofficial fan parody. The voice is synthetic, not a real Trump
recording. [Voice credits](content/voice-provenance.json) and
[texture notes](trump_face/README.md) cover the assets. No affiliation or
endorsement is implied. Please don't upload ROMs or extracted game assets here.
