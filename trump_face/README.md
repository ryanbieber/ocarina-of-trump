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
