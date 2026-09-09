# Applying the BPS patch

A BPS file contains the mod changes, not a playable ROM. You need your own clean
NTSC 1.0 copy of Ocarina of Time.

The patch filename includes the first eight characters of the required base ROM
MD5. For example, `ocarina-of-trump-ntsc-1.0-5bd1fe10.bps` requires a source
whose full MD5 is:

```text
5bd1fe107bf8106b2ab6650abecd54d6
```

## Windows

1. Download [Floating IPS](https://github.com/Sir-Walrus/Flips/releases).
2. Open `flips.exe` and choose **Apply Patch**.
3. Select the Ocarina of Trump `.bps` file.
4. Select your clean matching NTSC 1.0 ROM.
5. Save the result as a new `.z64` file and open that new file in your emulator.

Floating IPS will reject a source with the wrong size or checksum. Keep the
clean source and patched output as separate files.

## Command line

With the Floating IPS CLI:

```bash
flips --apply --exact ocarina-of-trump-ntsc-1.0-5bd1fe10.bps clean-ntsc-1.0.z64 ocarina-of-trump.z64
```

The BPS format stores CRC32 checksums for the source, target, and patch. The
project's build goes one step further: after creating the patch, it applies the
patch with an independent reader and compares every output byte with the built
compressed ROM.

Do not upload the source ROM or patched ROM to GitHub. Publish the `.bps` as the
release artifact.
