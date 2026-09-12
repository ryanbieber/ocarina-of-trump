# Setup, build, and run

Run the shell commands below in **WSL Debian**, from the repository root unless
stated otherwise. Windows Blender performs the model export; Debian compiles
the game. Keep the checkout in the Linux filesystem for faster builds.

## One-time setup

1. Install WSL Debian if needed. In an administrator PowerShell window:

   ```powershell
   wsl --install -d Debian
   ```

   Follow the Windows prompts, restart if requested, and create your Debian user.
   Open Debian with `wsl -d Debian` for the remaining shell commands.

2. Install build dependencies:

   ```bash
   sudo apt-get update
   sudo apt-get install git build-essential curl python3 python3-pip python3-venv libxml2-dev binutils-mips-linux-gnu
   python3 --version
   ```

   Python must be 3.10 or newer. The pinned ZeldaRET setup installs its additional
   build dependencies. An internet connection is needed for initial setup.

3. Install Windows Blender 5.2 and the
   [Fast64 add-on](https://github.com/Fast-64/fast64), following its installation
   instructions. Enable Fast64 in that Blender profile. Blender 4.x/5.x is
   accepted by the preflight; this project's current export was built with 5.2.

4. Clone the mod into your Debian home directory:

   ```bash
   cd ~
   git clone https://github.com/ryanbieber/ocarina-of-trump.git
   cd ocarina-of-trump
   git switch main
   export OOT_TRUMP_BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
   python3 -m oot_trump check-model-tools
   python3 -m oot_trump validate-content
   ```

   Adjust the Blender path to your installation. Set the export again in each
   new shell. The preflight checks Fast64's OoT skeleton importer/exporter and
   may enable an installed but disabled add-on and save Blender preferences.

## Build the complete mod

Supply your own supported NTSC 1.0 baserom. Other game versions are not supported.
Accepted MD5 values in [project configuration](../config/project.json) are:

```text
9f04c8e68534b870f707c247fa4b50fc
5bd1fe107bf8106b2ab6650abecd54d6
```

From the repository root:

```bash
./scripts/build-rom.sh "/absolute/path/to/your/ntsc-1.0-baserom.z64"
```

For an input stored on Windows, use its WSL path, for example
`/mnt/c/Users/YOUR_WINDOWS_USER/Games/baserom.z64`. Replace placeholders with
your actual paths and quote paths containing spaces. The build validates and
stages its own copy without modifying the original.

The one-shot command prepares ZeldaRET revision
`cbe814b25455f14a343a7457c4b1c92af40ede6a`, extracts local assets, restores the
pristine skeleton before Fast64 export, installs the mod, and compiles with
`VERSION=ntsc-1.0 REGION=US COMPARE=0`. It can be rerun using the same command.

Successful outputs:

```text
.work/oot/build/ntsc-1.0/oot-ntsc-1.0-compressed.z64
dist/ocarina-of-trump-ntsc-1.0-BASEHASH.bps
```

The workflow builds ZeldaRET's normal Yaz0-compressed image with every model,
message, and voice asset intact. It then builds a delta BPS with a pinned
Floating IPS revision and independently applies it in memory to prove that it
reproduces the compressed ROM byte for byte. Floating IPS is cloned and compiled
under ignored `.work/` storage on first use.

`BASEHASH` is the first eight characters of the clean input's MD5. A BPS patch
only accepts the exact source used to create it, so builds from the two accepted
base dumps get distinct filenames. Do not publish or commit either `.z64` file.
The `.bps` is the distributable mod artifact. See [Applying the BPS patch](PATCHING.md).

## Run on Windows

Copy only the **built mod output** to Downloads. In Debian, replace
`YOUR_WINDOWS_USER` below with your Windows account folder name:

```bash
cp .work/oot/build/ntsc-1.0/oot-ntsc-1.0-compressed.z64 "/mnt/c/Users/YOUR_WINDOWS_USER/Downloads/ocarina-of-trump.z64"
cp dist/ocarina-of-trump-ntsc-1.0-*.bps "/mnt/c/Users/YOUR_WINDOWS_USER/Downloads/"
```

This replaces a previous output with that filename. Choose a new filename if
you want to retain an older build for comparison.

In Project64, end any running emulation and use **File → Open ROM** to select
the new file. Configure your controller in the emulator, then start a new game
to check the introduction. Use your mapped C-Up button for companion hints.
Do not load a save state made with an earlier ROM: the patched audio memory
layout has changed. The latest build still needs the
[runtime checks](DEVELOPMENT.md#runtime-checklist); other emulators and real
hardware have not been established as supported by this testing.

## Update or rebuild

For a clean checkout, get the latest source and rerun the full build:

```bash
git pull --ff-only origin main
./scripts/build-rom.sh "/absolute/path/to/your/ntsc-1.0-baserom.z64"
```

After an initial complete build, text/audio-only iterations can use:

```bash
python3 -m oot_trump build
```

Both build commands regenerate the compressed ROM and verified BPS. To recreate
only the BPS from an existing build:

```bash
python3 -m oot_trump create-patch --baserom "/absolute/path/to/your/ntsc-1.0-baserom.z64"
```

Model generator or texture changes require the full one-shot build to export
again. `--skip-model` skips that export and retains whatever skeleton is already
in the managed checkout; it does not restore vanilla Navi on an existing build.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Unsupported ROM hash | Confirm NTSC 1.0 and an accepted hash; do not bypass validation. |
| Blender/Fast64 preflight fails | Check the executable path, install/enable Fast64 in that Blender profile, and rerun `check-model-tools`. |
| WSL cannot find a Windows file | Use `/mnt/c/...` paths and quotes around spaces. |
| Compilation fails | Find the first compiler, linker, or Python error above the final command failure. |
| Old title, names, or voice cues | Confirm the emulator opened the freshly built output, then cold-boot without an old save state. |
| Intro freeze or interrupted/incorrect audio | Record the scene, exact output filename, emulator/version, and whether a fresh boot reproduces it. Latest audio fixes still need runtime confirmation. |
| Wrong language after reusing a build | Use the canonical build so English startup and the region-cache marker are applied. |

All 183 required WAVs should arrive with the clone. If validation reports a
missing or malformed clip, restore the catalog and inspect the error rather
than using an incomplete-audio option for a release build.
