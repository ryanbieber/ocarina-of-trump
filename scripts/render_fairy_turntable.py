"""Render the Trump fairy as a short turntable for the README.

Run from the repository root:

    blender --background --python scripts/render_fairy_turntable.py

PNG frames are written to the ignored `.work/turntable/frames` directory.
"""

import math
import os
import runpy

import bpy


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAME_DIR = os.path.join(PROJECT_ROOT, ".work", "turntable", "frames")
FRAME_COUNT = 60


def main():
    os.makedirs(FRAME_DIR, exist_ok=True)
    model = runpy.run_path(os.path.join(PROJECT_ROOT, "scripts", "build_fairy_model.py"))
    model["clear_scene"]()
    parts = model["build_character"]()

    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0.0, 0.0, 0.0))
    pivot = bpy.context.object
    pivot.name = "TrumpFairyTurntable"
    for part in parts:
        world_matrix = part.matrix_world.copy()
        part.parent = pivot
        part.matrix_world = world_matrix

    model["add_preview_camera_and_light"]()
    model["set_preview_settings"]()
    scene = bpy.context.scene
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = 420
    scene.render.resolution_y = 420
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.055, 0.06, 0.075)

    camera = scene.camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 1.75
    camera.location = (0.0, -4.0, 0.18)
    model["look_at"](camera, (0.0, 0.0, 0.0))

    for frame in range(FRAME_COUNT):
        pivot.rotation_euler.z = math.tau * frame / FRAME_COUNT
        scene.render.filepath = os.path.join(FRAME_DIR, f"frame_{frame:04d}.png")
        bpy.ops.render.render(write_still=True)

    print(f"Rendered {FRAME_COUNT} turntable frames to {FRAME_DIR}")


if __name__ == "__main__":
    main()
