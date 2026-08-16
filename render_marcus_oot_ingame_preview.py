"""Render the Marcus Link blend as a small OoT/N64-style preview.

Run with:
  blender --background link_marcus_fast64_example.blend --python render_marcus_oot_ingame_preview.py
"""

import bpy


def material(name, color, roughness=1.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
    return mat


def add_tree(name, x, y, height, color):
    trunk_mat = material(name + "_Trunk", (0.12, 0.07, 0.035))
    leaf_mat = material(name + "_Leaves", color)
    bpy.ops.mesh.primitive_cylinder_add(vertices=7, radius=0.18, depth=height * 0.55, location=(x, y, height * 0.275))
    bpy.context.object.data.materials.append(trunk_mat)
    bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=1.0, radius2=0.12, depth=height * 0.80, location=(x, y, height * 0.70))
    bpy.context.object.data.materials.append(leaf_mat)


scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except Exception:
    scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 320
scene.render.resolution_y = 240
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = "link_marcus_oot_ingame_preview.png"
scene.world.color = (0.012, 0.025, 0.035)

try:
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = -0.4
    scene.view_settings.gamma = 1.0
except Exception:
    pass

ground_mat = material("MarcusOoTPreview_Ground", (0.045, 0.105, 0.065))
bpy.ops.mesh.primitive_plane_add(size=20.0, location=(0.0, 0.0, 0.0))
bpy.context.object.name = "MarcusOoTPreview_Ground"
bpy.context.object.data.materials.append(ground_mat)

add_tree("MarcusTreeLeft", -2.7, 2.6, 4.2, (0.025, 0.16, 0.08))
add_tree("MarcusTreeRight", 2.8, 3.0, 5.0, (0.02, 0.12, 0.065))
add_tree("MarcusTreeFar", -1.8, 4.0, 3.2, (0.015, 0.09, 0.05))

bpy.ops.object.light_add(type="POINT", location=(0.0, -1.0, 2.3))
fairy_light = bpy.context.object
fairy_light.name = "MarcusOoTPreview_FairyLight"
fairy_light.data.energy = 75.0
fairy_light.data.color = (0.45, 0.75, 1.0)
fairy_light.data.shadow_soft_size = 1.0

bpy.ops.object.light_add(type="AREA", location=(0.0, -4.0, 5.0))
front = bpy.context.object
front.name = "MarcusOoTPreview_FrontLight"
front.data.energy = 250.0
front.data.size = 5.0
front.rotation_euler = (0.35, 0.0, 0.0)

bpy.ops.render.render(write_still=True)
print("Wrote " + scene.render.filepath)
