# Ocarina of Trump assets

This repository contains OoT/Fast64-style parody character generators and
preview tooling. The original asset is a Navi replacement called Trump; the
new Link replacement is called Marcus.

Files:

- `navi_trump_fast64_example.py` — Blender Python script.
- `navi_trump_fast64_example.blend` — generated low-poly preview blend.

## Use with a real OoT/Fast64 project

1. Install Blender 4.x and Fast64.
2. Open the Python file in Blender's **Scripting** workspace.
3. At the top of the script, set:

   ```python
   OOT_DECOMP_PATH = r"/absolute/path/to/your/oot"
   IMPORT_NAVI_FROM_DECOMP = True
   ```

4. Run the script.
5. Inspect the generated model and leave `EXPORT_WITH_FAST64 = False` until it looks right.
6. After testing, set `EXPORT_WITH_FAST64 = True` and run it again to export the skeleton.

The included blend was generated without an OoT decomp folder, so it contains a
preview armature with Navi-like bone names rather than the real imported
`gFairySkel`. The script can import the real skeleton when `OOT_DECOMP_PATH` is
configured.

The model is weighted to the fairy root bone for simplicity. The wings are
static until their vertices are assigned to the existing fairy wing bones.

The script now defaults to an OoT-style faceted look: flatter shading, a
muted N64 palette, translucent blue fairy wings, and a preview-only glow aura.
`HIGH_POLY_PREVIEW` remains available for editing, but the OoT style uses
moderate subdivisions so the result still resembles an N64 actor.

The current benchmark pass is based on the supplied Trump reference: broad
low-poly head, swept blond hair, narrowed eyes, furrowed brows, long nose,
pursed frown, navy suit, white shirt, and red tie. The wings and fairy behavior
remain Navi-oriented.

Delete or hide `TrumpFairy_OoTGlow_PREVIEW_ONLY` before a final ROM export if
Fast64 reports an extra mesh or material that you do not want included.

## Marcus Link variant

The repository also includes a Link replacement based on the supplied Marco
Rubio reference. The character is called Marcus and uses short dark side-parted
hair, a clean-shaven smiling face, a navy suit, white shirt, red tie, and a
small gold lapel pin in an OoT-style faceted treatment.

Files:

- `link_marcus_fast64_example.py` — standalone Blender/Fast64 generator.
- `link_marcus_fast64_example.blend` — generated blend after running the script.
- `render_marcus_oot_ingame_preview.py` — 320x240 preview renderer.

The Marcus `.blend` and PNG are generated artifacts rather than checked-in
files until the script is run in Blender; this workspace does not include a
Blender runtime.

For a real Link skeleton, set `OOT_DECOMP_PATH`, enable
`IMPORT_LINK_FROM_DECOMP`, and run the Marcus script from Blender. It targets
the adult Link skeleton (`gLinkAdultSkel`) in `object_link_boy` and the player
actor overlay. The generated preview fallback uses a Link-like armature when a
decompilation or Fast64 is not available.
