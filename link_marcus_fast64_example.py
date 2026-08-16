"""Link -> Marcus: an OoT/Fast64-friendly character replacement example.

This is a standalone generator for a low-poly Link replacement based on the
supplied Marco Rubio reference.  The character keeps an OoT-style faceted
silhouette but uses Marcus's visual cues: short dark side-parted hair, a
clean-shaven smiling face, navy suit, white shirt, and red tie.

The script reuses the geometry/material helpers from the existing
``navi_trump_fast64_example.py`` file, but creates its own Link-style fallback
armature and Fast64 import/export settings.  For a real OoT project, set:

    OOT_DECOMP_PATH = r"/absolute/path/to/your/oot"
    IMPORT_LINK_FROM_DECOMP = True

Then run this file from Blender's Scripting workspace or with:

    blender --background --python link_marcus_fast64_example.py

The generated mesh is weighted to the Link root bone for a safe first pass.
With a real imported Link skeleton, assign individual parts/vertices to the
existing limb bones after checking the replacement in-game.
"""

import math
import os
import sys

import bpy
from mathutils import Vector


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

OOT_DECOMP_PATH = ""  # Example: r"/home/me/oot"
IMPORT_LINK_FROM_DECOMP = False
EXPORT_WITH_FAST64 = False

OUTPUT_BLEND = "link_marcus_fast64_example.blend"
HIGH_POLY_PREVIEW = True
OOT_STYLE = True
SMOOTH_ROUND_PARTS = False
MODEL_SCALE = 1.0

LINK_SKELETON_NAME = "gLinkAdultSkel"
LINK_ASSET_FOLDER = "object_link_boy"
LINK_ACTOR_OVERLAY = "ovl_player_actor"


# The original Navi script owns the portable Blender primitive/material
# helpers. Importing it keeps both generators consistent and avoids two
# subtly different Fast64 conversion implementations.
try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    SCRIPT_DIR = bpy.path.abspath("//")
if SCRIPT_DIR and SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import navi_trump_fast64_example as base


def log(message):
    print("[MARCUS-LINK] " + message)


def set_base_style():
    base.OOT_STYLE = OOT_STYLE
    base.SMOOTH_ROUND_PARTS = SMOOTH_ROUND_PARTS
    base.HIGH_POLY_PREVIEW = HIGH_POLY_PREVIEW
    base.MODEL_SCALE = 1.0


def deselect_all():
    base.deselect_all()


def clear_scene(keep_armature=None):
    base.clear_scene(keep_armature)


def add_tapered_tie(name, z_top, z_bottom, top_half_width, bottom_half_width, y, material):
    """Create a thin, four-sided tapered tie prism facing the preview camera."""
    y_front = y - 0.055
    y_back = y + 0.055
    outline = [
        (-top_half_width, z_top),
        (top_half_width, z_top),
        (bottom_half_width, z_bottom),
        (-bottom_half_width, z_bottom),
    ]
    vertices = [(x, y_front, z) for x, z in outline] + [(x, y_back, z) for x, z in outline]
    faces = [
        (0, 3, 2, 1),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ]
    return base.add_flat_mesh(name, vertices, faces, material)


def add_lapel(name, side, material):
    s = float(side)
    vertices = [
        (s * 0.04, -0.49, 2.30),
        (s * 0.43, -0.53, 2.42),
        (s * 0.18, -0.57, 1.98),
        (s * 0.02, -0.52, 2.19),
    ]
    return base.add_flat_mesh(name, vertices, [(0, 1, 2), (0, 2, 3)], material)


def add_shirt_collar(name, side, material):
    s = float(side)
    vertices = [
        (0.02 * s, -0.55, 2.42),
        (0.28 * s, -0.56, 2.43),
        (0.10 * s, -0.59, 2.22),
    ]
    return base.add_flat_mesh(name, vertices, [(0, 1, 2)], material)


def add_belt_buckle(name, material):
    return base.add_cube(name, (0.0, -0.48, 1.12), (0.18, 0.07, 0.16), material, bevel=0.025)


def add_fallback_link_armature():
    """Create a preview armature with familiar Link-like limb names."""
    armature_data = bpy.data.armatures.new("MarcusLinkArmatureData")
    armature = bpy.data.objects.new("MarcusLinkArmature", armature_data)
    bpy.context.collection.objects.link(armature)
    armature.show_in_front = True

    deselect_all()
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")

    bones = {}

    def bone(name, head, tail, parent=None):
        item = armature_data.edit_bones.new(name)
        item.head = head
        item.tail = tail
        if parent:
            item.parent = bones[parent]
        bones[name] = item
        return item

    bone("root", (0.0, 0.0, 0.0), (0.0, 0.0, 0.35))
    bone("waist", (0.0, 0.0, 0.35), (0.0, 0.0, 1.15), "root")
    bone("chest", (0.0, 0.0, 1.15), (0.0, 0.0, 2.25), "waist")
    bone("head", (0.0, 0.0, 2.25), (0.0, 0.0, 3.10), "chest")
    bone("l_arm", (-0.50, 0.0, 2.18), (-0.95, 0.0, 1.40), "chest")
    bone("l_hand", (-0.95, 0.0, 1.40), (-1.00, 0.0, 1.05), "l_arm")
    bone("r_arm", (0.50, 0.0, 2.18), (0.95, 0.0, 1.40), "chest")
    bone("r_hand", (0.95, 0.0, 1.40), (1.00, 0.0, 1.05), "r_arm")
    bone("l_thigh", (-0.28, 0.0, 1.15), (-0.34, 0.0, 0.60), "waist")
    bone("l_shin", (-0.34, 0.0, 0.60), (-0.36, 0.0, 0.18), "l_thigh")
    bone("l_foot", (-0.36, 0.0, 0.18), (-0.36, -0.30, 0.12), "l_shin")
    bone("r_thigh", (0.28, 0.0, 1.15), (0.34, 0.0, 0.60), "waist")
    bone("r_shin", (0.34, 0.0, 0.60), (0.36, 0.0, 0.18), "r_thigh")
    bone("r_foot", (0.36, 0.0, 0.18), (0.36, -0.30, 0.12), "r_shin")

    bpy.ops.object.mode_set(mode="OBJECT")
    return armature


def find_link_armature():
    for name in ("MarcusLinkArmature", "LinkAdultArmature", "LinkArmature"):
        obj = bpy.data.objects.get(name)
        if obj is not None and obj.type == "ARMATURE":
            return obj
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    return armatures[0] if armatures else None


def get_root_bone(armature):
    roots = [bone for bone in armature.data.bones if bone.parent is None]
    if not roots:
        raise RuntimeError("The Link armature has no root bone.")
    return roots[0]


def import_link_with_fast64():
    if not IMPORT_LINK_FROM_DECOMP or not OOT_DECOMP_PATH:
        return None
    if not hasattr(bpy.ops.object, "oot_import_skeleton"):
        log("Fast64 OoT importer is not available; using fallback Link armature.")
        return None

    decomp_path = os.path.abspath(os.path.expanduser(OOT_DECOMP_PATH))
    if not os.path.isdir(decomp_path):
        log("OoT decomp path does not exist; using fallback: " + decomp_path)
        return None

    scene = bpy.context.scene
    try:
        scene.gameEditorMode = "OOT"
    except Exception:
        pass

    try:
        scene.ootDecompPath = decomp_path
        settings = scene.fast64.oot.skeletonImportSettings
        settings.mode = "Generic"
        settings.name = LINK_SKELETON_NAME
        settings.folder = LINK_ASSET_FOLDER
        settings.actorOverlayName = LINK_ACTOR_OVERLAY
        settings.import_animations = True
        settings.importNormals = True
        settings.removeDoubles = True
        settings.autoDetectActorScale = True
        deselect_all()
        bpy.ops.object.oot_import_skeleton()
        armature = find_link_armature()
        if armature:
            armature.name = "MarcusLinkArmature"
            log("Imported " + LINK_SKELETON_NAME + " from OoT decomp.")
        return armature
    except Exception as exc:
        log("Fast64 Link import failed: " + repr(exc))
        return None


def export_with_fast64(armature):
    if not EXPORT_WITH_FAST64:
        return False
    if not hasattr(bpy.ops.object, "oot_export_skeleton"):
        log("Fast64 OoT exporter is not available; skipping export.")
        return False

    try:
        settings = bpy.context.scene.fast64.oot.skeletonExportSettings
        settings.mode = "Generic"
        settings.folder = LINK_ASSET_FOLDER
        settings.actorOverlayName = LINK_ACTOR_OVERLAY
        settings.removeVanillaData = True
        settings.isCustom = False
        settings.isCustomFilename = True
        settings.filename = "link_marcus_skel"
        deselect_all()
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.oot_export_skeleton()
        log("Fast64 Link skeleton export completed.")
        return True
    except Exception as exc:
        log("Fast64 Link export failed: " + repr(exc))
        return False


def build_character():
    """Build Marcus with OoT proportions and the reference's formal outfit."""
    if OOT_STYLE:
        skin_color = (0.64, 0.34, 0.20)
        hair_color = (0.035, 0.022, 0.018)
        hair_highlight_color = (0.12, 0.075, 0.045)
        hair_shadow_color = (0.012, 0.008, 0.006)
        suit_color = (0.018, 0.030, 0.085)
        shirt_color = (0.86, 0.86, 0.78)
        tie_color = (0.62, 0.018, 0.025)
        belt_color = (0.045, 0.025, 0.015)
        gold_color = (0.72, 0.42, 0.08)
    else:
        skin_color = (0.82, 0.49, 0.32)
        hair_color = (0.055, 0.035, 0.025)
        hair_highlight_color = (0.18, 0.11, 0.07)
        hair_shadow_color = (0.015, 0.01, 0.008)
        suit_color = (0.025, 0.05, 0.15)
        shirt_color = (0.97, 0.97, 0.91)
        tie_color = (0.86, 0.025, 0.035)
        belt_color = (0.08, 0.04, 0.02)
        gold_color = (0.95, 0.60, 0.10)

    skin = base.make_material("MarcusLink_Skin", skin_color)
    hair = base.make_material("MarcusLink_Hair", hair_color)
    hair_highlight = base.make_material("MarcusLink_HairHighlight", hair_highlight_color)
    hair_shadow = base.make_material("MarcusLink_HairShadow", hair_shadow_color)
    suit = base.make_material("MarcusLink_Suit", suit_color)
    shirt = base.make_material("MarcusLink_Shirt", shirt_color)
    tie = base.make_material("MarcusLink_Tie", tie_color)
    belt = base.make_material("MarcusLink_Belt", belt_color)
    gold = base.make_material("MarcusLink_GoldDetails", gold_color)
    eye_white = base.make_material("MarcusLink_EyeWhite", (0.76, 0.73, 0.64))
    eye_dark = base.make_material("MarcusLink_EyeDark", (0.018, 0.012, 0.010))
    mouth = base.make_material("MarcusLink_Mouth", (0.20, 0.018, 0.015))
    lip = base.make_material("MarcusLink_Lip", (0.46, 0.055, 0.045))
    shoe = base.make_material("MarcusLink_Shoes", (0.018, 0.012, 0.010))

    round_subdivisions = 2 if OOT_STYLE else (3 if HIGH_POLY_PREVIEW else 2)
    detail_subdivisions = 1 if OOT_STYLE else (2 if HIGH_POLY_PREVIEW else 1)
    parts = []

    # Compact hero body, formal jacket, trousers, and dress shoes.
    parts.append(base.add_ico("MarcusLink_SuitBody", (0.0, 0.0, 1.82), (0.76, 0.45, 0.92), suit, round_subdivisions))
    parts.append(base.add_ico("MarcusLink_Trousers", (0.0, 0.0, 1.04), (0.58, 0.39, 0.37), suit, detail_subdivisions))
    parts.append(base.add_ico("MarcusLink_ShirtFront", (0.0, -0.45, 2.12), (0.24, 0.07, 0.53), shirt, detail_subdivisions))
    parts.append(add_lapel("MarcusLink_Lapel_L", -1, suit))
    parts.append(add_lapel("MarcusLink_Lapel_R", 1, suit))
    parts.append(add_shirt_collar("MarcusLink_Collar_L", -1, shirt))
    parts.append(add_shirt_collar("MarcusLink_Collar_R", 1, shirt))
    parts.append(add_tapered_tie("MarcusLink_Tie", 2.28, 1.58, 0.105, 0.16, -0.55, tie))
    parts.append(base.add_ico("MarcusLink_TieKnot", (0.0, -0.60, 2.30), (0.13, 0.07, 0.13), tie, detail_subdivisions))
    parts.append(base.add_cube("MarcusLink_Belt", (0.0, -0.40, 1.16), (0.86, 0.08, 0.10), belt, bevel=0.025))
    parts.append(add_belt_buckle("MarcusLink_BeltBuckle", gold))

    # Suit arms taper into simple Link-like gloves/hands.
    parts.append(base.add_cylinder_between("MarcusLink_Arm_L", (-0.52, 0.0, 2.13), (-0.86, -0.01, 1.40), 0.18, suit))
    parts.append(base.add_cylinder_between("MarcusLink_Arm_R", (0.52, 0.0, 2.13), (0.86, -0.01, 1.40), 0.18, suit))
    parts.append(base.add_ico("MarcusLink_Hand_L", (-0.86, -0.02, 1.30), (0.17, 0.16, 0.20), skin, detail_subdivisions))
    parts.append(base.add_ico("MarcusLink_Hand_R", (0.86, -0.02, 1.30), (0.17, 0.16, 0.20), skin, detail_subdivisions))

    parts.append(base.add_cylinder_between("MarcusLink_Leg_L", (-0.29, 0.0, 1.00), (-0.34, 0.0, 0.38), 0.20, suit))
    parts.append(base.add_cylinder_between("MarcusLink_Leg_R", (0.29, 0.0, 1.00), (0.34, 0.0, 0.38), 0.20, suit))
    parts.append(base.add_ico("MarcusLink_Shoe_L", (-0.34, -0.15, 0.23), (0.25, 0.37, 0.14), shoe, detail_subdivisions))
    parts.append(base.add_ico("MarcusLink_Shoe_R", (0.34, -0.15, 0.23), (0.25, 0.37, 0.14), shoe, detail_subdivisions))

    # Broad, clean-shaven face with the reference's square jaw and friendly
    # smile, translated into faceted OoT geometry.
    parts.append(base.add_ico("MarcusLink_Head", (0.0, 0.0, 2.92), (0.62, 0.52, 0.70), skin, round_subdivisions))
    parts.append(base.add_ico("MarcusLink_Jaw", (0.0, -0.10, 2.67), (0.43, 0.34, 0.34), skin, detail_subdivisions))
    parts.append(base.add_ico("MarcusLink_Ear_L", (-0.57, 0.0, 2.93), (0.12, 0.15, 0.18), skin, detail_subdivisions))
    parts.append(base.add_ico("MarcusLink_Ear_R", (0.57, 0.0, 2.93), (0.12, 0.15, 0.18), skin, detail_subdivisions))

    # Short dark side part rather than Link's usual cap and long hair.
    parts.append(base.add_ico("MarcusLink_HairCap", (0.0, 0.04, 3.49), (0.64, 0.49, 0.25), hair, round_subdivisions))
    parts.append(base.add_ico("MarcusLink_HairSidePart", (-0.22, -0.20, 3.58), (0.36, 0.22, 0.14), hair_highlight, detail_subdivisions))
    parts.append(base.add_ico("MarcusLink_HairSweep", (0.28, -0.14, 3.55), (0.43, 0.27, 0.16), hair, detail_subdivisions))
    parts.append(base.add_ico("MarcusLink_Hairline_L", (-0.48, -0.10, 3.36), (0.15, 0.20, 0.16), hair_shadow, detail_subdivisions))
    parts.append(base.add_ico("MarcusLink_Hairline_R", (0.48, -0.10, 3.36), (0.15, 0.20, 0.16), hair_shadow, detail_subdivisions))

    # Warm, approachable expression from the supplied portrait.
    parts.append(base.add_ico("MarcusLink_Eye_L", (-0.22, -0.50, 3.03), (0.105, 0.040, 0.060), eye_white, detail_subdivisions))
    parts.append(base.add_ico("MarcusLink_Eye_R", (0.22, -0.50, 3.03), (0.105, 0.040, 0.060), eye_white, detail_subdivisions))
    parts.append(base.add_ico("MarcusLink_Pupil_L", (-0.22, -0.545, 3.03), (0.030, 0.018, 0.038), eye_dark, detail_subdivisions))
    parts.append(base.add_ico("MarcusLink_Pupil_R", (0.22, -0.545, 3.03), (0.030, 0.018, 0.038), eye_dark, detail_subdivisions))
    parts.append(base.add_cylinder_between("MarcusLink_Brow_L", (-0.36, -0.53, 3.19), (-0.08, -0.56, 3.22), 0.035, hair_shadow))
    parts.append(base.add_cylinder_between("MarcusLink_Brow_R", (0.08, -0.56, 3.22), (0.36, -0.53, 3.19), 0.035, hair_shadow))
    parts.append(base.add_ico("MarcusLink_NoseBridge", (0.0, -0.42, 2.98), (0.11, 0.13, 0.20), skin, detail_subdivisions))
    parts.append(base.add_cone("MarcusLink_Nose", (0.0, -0.58, 2.88), 0.12, 0.025, 0.28, skin, (math.pi / 2.0, 0.0, 0.0)))
    parts.append(base.add_cylinder_between("MarcusLink_Smile_L", (-0.16, -0.545, 2.69), (0.0, -0.57, 2.66), 0.025, mouth))
    parts.append(base.add_cylinder_between("MarcusLink_Smile_R", (0.0, -0.57, 2.66), (0.16, -0.545, 2.69), 0.025, mouth))
    parts.append(base.add_ico("MarcusLink_LowerLip", (0.0, -0.55, 2.62), (0.11, 0.025, 0.035), lip, detail_subdivisions))

    # A tiny warm lapel pin keeps the formal portrait cue without adding a
    # texture dependency; replace it with a flag texture later if desired.
    parts.append(base.add_ico("MarcusLink_LapelPin", (-0.39, -0.59, 2.08), (0.055, 0.025, 0.055), gold, detail_subdivisions))

    for obj in parts:
        obj.scale = obj.scale * MODEL_SCALE
    return parts


def join_and_bind(parts, armature):
    if not parts:
        raise RuntimeError("No Marcus mesh parts were created.")
    deselect_all()
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    mesh_obj = bpy.context.object
    mesh_obj.name = "MarcusLink_F3D_Mesh"

    world_matrix = mesh_obj.matrix_world.copy()
    mesh_obj.parent = armature
    mesh_obj.matrix_world = world_matrix

    root_name = get_root_bone(armature).name
    vertex_group = mesh_obj.vertex_groups.get(root_name) or mesh_obj.vertex_groups.new(name=root_name)
    vertex_group.add([vertex.index for vertex in mesh_obj.data.vertices], 1.0, "REPLACE")
    modifier = mesh_obj.modifiers.new(name="MarcusLinkArmature", type="ARMATURE")
    modifier.object = armature
    mesh_obj["Fast64_example_note"] = "Marcus geometry is weighted to the Link root bone for the first replacement pass."
    mesh_obj["Fast64_skeleton_note"] = "Use the imported Link skeleton and assign limbs for final animation fidelity."
    return mesh_obj


def add_preview_camera_and_light():
    bpy.ops.object.camera_add(location=(4.2, -7.0, 3.8))
    camera = bpy.context.object
    camera.name = "MarcusPreviewCamera"
    direction = Vector((0.0, 0.0, 1.75)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = camera

    bpy.ops.object.light_add(type="AREA", location=(3.5, -4.0, 6.0))
    key = bpy.context.object
    key.name = "MarcusPreviewKey"
    key.data.energy = 700.0
    key.data.shape = "DISK"
    key.data.size = 5.0
    key.rotation_euler = (Vector((0.0, 0.0, 1.65)) - key.location).to_track_quat("-Z", "Y").to_euler()

    bpy.ops.object.light_add(type="AREA", location=(-4.0, 1.0, 3.0))
    fill = bpy.context.object
    fill.name = "MarcusPreviewFill"
    fill.data.energy = 300.0
    fill.data.size = 4.0
    fill.rotation_euler = (Vector((0.0, 0.0, 1.6)) - fill.location).to_track_quat("-Z", "Y").to_euler()


def set_preview_settings():
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        try:
            scene.render.engine = "BLENDER_EEVEE"
        except Exception:
            pass
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.world.color = (0.025, 0.035, 0.07)


def output_path():
    if os.path.isabs(OUTPUT_BLEND):
        return OUTPUT_BLEND
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        base_dir = bpy.path.abspath("//")
    return os.path.abspath(os.path.join(base_dir, OUTPUT_BLEND))


def main():
    set_base_style()
    existing_armature = find_link_armature()
    imported_armature = None

    if IMPORT_LINK_FROM_DECOMP and OOT_DECOMP_PATH:
        clear_scene()
        imported_armature = import_link_with_fast64()
    else:
        clear_scene(existing_armature)

    armature = imported_armature or existing_armature or find_link_armature()
    if armature is None:
        armature = add_fallback_link_armature()
        log("Created fallback Link armature.")
    else:
        armature.name = "MarcusLinkArmature"
        base.delete_objects([obj for obj in list(armature.children) if obj.type == "MESH"])
        log("Reusing armature: " + armature.name)

    parts = build_character()
    mesh_obj = join_and_bind(parts, armature)
    add_preview_camera_and_light()
    set_preview_settings()
    base.convert_materials_to_f3d()
    export_with_fast64(armature)

    deselect_all()
    mesh_obj.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature

    path = output_path()
    bpy.ops.wm.save_as_mainfile(filepath=path)
    log("Saved blend file: " + path)
    log("Finished. Render the preview or inspect the armature before exporting to OoT.")


if __name__ == "__main__":
    main()
