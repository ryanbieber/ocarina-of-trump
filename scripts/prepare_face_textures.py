"""Run with Blender --background --python scripts/prepare_face_textures.py."""
from pathlib import Path
import bpy


def main():
    folder = Path(__file__).resolve().parents[1] / 'trump_face'
    scene = bpy.context.scene
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    for stem in ('trump_face_smug', 'trump_face_smug_talking'):
        image = bpy.data.images.load(str(folder / (stem + '.png')), check_existing=False)
        image.colorspace_settings.name = 'sRGB'
        image.scale(32, 32)
        image.save_render(str(folder / (stem + '_n64.png')), scene=scene)
        bpy.data.images.remove(image)


if __name__ == '__main__':
    main()
