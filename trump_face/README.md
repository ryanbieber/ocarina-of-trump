# Trump face texture sources

The four `trump_face_{default,angry,squint,talking}.png` reference images were
provided and committed by the repository owner. Distribution requires the
owner to retain permission for those source images.

The `trump_face_smug*.png` files are original painted parody derivatives made
with OpenAI image generation on 2026-09-06 from those supplied references:

- `trump_face_smug.png`: approved full-resolution calm/smug source.
- `trump_face_smug_talking.png`: matching open-mouth animation source.
- `*_n64.png`: 32x32 RGBA runtime versions consumed by Fast64. Each becomes a
  2 KiB RGBA16 texture and fits within the N64 RDP's 4 KiB TMEM limit.

The build must use the two `_n64.png` files. Pointing Blender at either
full-resolution source would consume several MiB of ROM and exceed the N64
texture memory available for a single material.

## Continuous-head revision (2026-09-08)

The current `trump_face_smug.png` and `trump_face_smug_talking.png` were edited
with OpenAI's built-in image generation tool at the owner's request. The earlier
painted parody face was the reference. These are opaque UV textures with simpler
features, a tan boundary, and no painted hair/ears/head silhouette. They map onto
one continuous head surface instead of a separate overlay. Blender scales the
two sources to the existing 32×32 runtime PNGs; names and animation hooks remain.

Calm prompt: Create a square opaque N64-style face UV texture from the existing
Trump parody face, with broad painted features, even tan edges, no hair, ears,
head silhouette, transparency, text, or photographic pores. Place brows, eyes,
nose, and closed mouth centrally and keep the likeness readable at 32×32.
Talking edit prompt: Change only the mouth interior to a narrow opening and
restrained upper tooth strip; preserve the rest of the UV texture and colors.

Both are fictional synthetic artwork, not photographs or official game assets.
