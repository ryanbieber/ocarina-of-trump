"""Navi -> stylized Trump fairy example for Blender + Fast64.

What this script does:
  * Builds a deliberately low-poly parody character with wings.
  * Reuses an already-imported OoT/Fast64 armature when one exists.
  * Can import gFairySkel automatically when OOT_DECOMP_PATH is configured.
  * Converts the generated Principled materials to Fast64 F3D materials when
    the Fast64 addon is installed.
  * Saves a .blend file next to this script.

Important:
  * This is an example/template, not a finished ROM hack.
  * The generated mesh is weighted to Navi's root bone so it follows her
    movement. Assign the wing vertices to Navi's wing bones later if you want
    animated wings.
  * Do not add bones to the imported Navi skeleton until the basic replacement
    works. En_Elf expects the original fairy skeleton structure.

Run from Blender's Scripting workspace, or from a Blender command line:

  blender --background --python navi_trump_fast64_example.py

To import Navi from an OoT decompilation before building the model, set:

  OOT_DECOMP_PATH = r"/absolute/path/to/your/oot"
  IMPORT_NAVI_FROM_DECOMP = True

Fast64's current OoT operators used here are:
  object.oot_import_skeleton
  object.oot_export_skeleton
  object.convert_bsdf
"""

import importlib
import math
import os
import sys

import bpy
from mathutils import Vector


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

OOT_DECOMP_PATH = os.environ.get("OOT_DECOMP_PATH", "")
IMPORT_NAVI_FROM_DECOMP = os.environ.get("NAVI_TRUMP_IMPORT", "0") == "1"

# Leave False for the first test. Set True only after checking the model in
# Blender and confirming that your decomp path/export settings are correct.
EXPORT_WITH_FAST64 = os.environ.get("NAVI_TRUMP_EXPORT", "0") == "1"

# A relative path is resolved next to this script when run with --python.
OUTPUT_BLEND = os.environ.get("NAVI_TRUMP_BLEND_OUTPUT", "navi_trump_fast64_example.blend")

# Higher detail is useful while modeling. Before a final ROM export, you may
# want to reduce these values again because the original N64 renderer has tight
# memory and vertex limits.
HIGH_POLY_PREVIEW = True
# OoT's original actors are angular and rely on flat vertex normals. Keep the
# extra geometry available for editing, but shade it like an N64 model.
OOT_STYLE = True
SMOOTH_ROUND_PARTS = False
ADD_OOT_GLOW = True
MODEL_SCALE = 1.0

# SkelAnime uses one-based draw limb indices. Fast64 names the corresponding
# deform bones after the zero-based gFairySkel limb symbols. OoT animates four
# wing display limbs: 4, 7, 11, and 14.
WING_BONES = {
    "L": {"upper": 3, "lower": 6},
    "R": {"upper": 10, "lower": 13},
}
MAX_EXPORT_VERTICES = 1800
MAX_EXPORT_MATERIALS = 16


# -----------------------------------------------------------------------------
# General Blender helpers
# -----------------------------------------------------------------------------


def log(message):
    print("[NAVI-TRUMP] " + message)


def deselect_all():
    for obj in bpy.context.selected_objects:
        obj.select_set(False)


def delete_objects(objects):
    for obj in list(objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def clear_scene(keep_armature=None):
    delete_objects(
        [obj for obj in list(bpy.data.objects) if keep_armature is None or obj != keep_armature]
    )


def find_armature():
    preferred = bpy.data.objects.get("NaviFairyArmature")
    if preferred is not None and preferred.type == "ARMATURE":
        return preferred

    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    return armatures[0] if armatures else None


def get_root_bone(armature):
    roots = [bone for bone in armature.data.bones if bone.parent is None]
    if not roots:
        raise RuntimeError("The armature has no root bone.")
    return roots[0]


def get_limb_bone(armature, limb_index):
    """Resolve a Fast64 fairy limb bone without depending on its prefix."""
    suffix = "gFairySkelLimb_{0}".format(limb_index)
    matches = [bone for bone in armature.data.bones if bone.name.endswith(suffix)]
    if len(matches) != 1:
        raise RuntimeError(
            "Expected one bone ending in {0}; found {1}".format(suffix, len(matches))
        )
    return matches[0]


def apply_surface_shading(obj, smooth=False):
    if obj.type != "MESH":
        return
    for poly in obj.data.polygons:
        poly.use_smooth = smooth


def apply_flat_shading(obj):
    apply_surface_shading(obj, smooth=False)


def make_material(name, color, alpha=1.0):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True

    nodes = material.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf is not None:
        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = (
                color[0],
                color[1],
                color[2],
                alpha,
            )
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.9
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha

    material.diffuse_color = (color[0], color[1], color[2], alpha)
    material["Fast64_example_material"] = True

    # Blender 3.x uses blend_method; newer Blender versions use
    # surface_render_method. The try blocks keep this script portable.
    if alpha < 1.0:
        try:
            material.blend_method = "BLEND"
        except Exception:
            pass
        try:
            material.surface_render_method = "DITHERED"
        except Exception:
            pass

    return material


def attach_material(obj, material):
    obj.data.materials.append(material)
    return obj


def add_ico(name, location, scale, material, subdivisions=2, smooth=None):
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=subdivisions,
        radius=1.0,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    attach_material(obj, material)
    if smooth is None:
        smooth = SMOOTH_ROUND_PARTS
    apply_surface_shading(obj, smooth=smooth)
    return obj


def add_uv_sphere(name, location, scale, material, segments=16, rings=8, smooth=None):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        radius=1.0,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    attach_material(obj, material)
    if smooth is None:
        smooth = SMOOTH_ROUND_PARTS
    apply_surface_shading(obj, smooth=smooth)
    return obj


def add_cube(name, location, scale, material, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    attach_material(obj, material)
    if bevel > 0.0:
        modifier = obj.modifiers.new(name="Tiny bevel", type="BEVEL")
        modifier.width = bevel
        modifier.segments = 1
        bpy.context.view_layer.objects.active = obj
        try:
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        except Exception:
            pass
    apply_flat_shading(obj)
    return obj


def add_cone(name, location, radius1, radius2, depth, material, rotation=None):
    bpy.ops.mesh.primitive_cone_add(
        vertices=10,
        radius1=radius1,
        radius2=radius2,
        depth=depth,
        location=location,
        rotation=rotation or (0.0, 0.0, 0.0),
    )
    obj = bpy.context.object
    obj.name = name
    attach_material(obj, material)
    apply_surface_shading(obj, smooth=False)
    return obj


def add_cylinder_between(name, start, end, radius, material):
    start = Vector(start)
    end = Vector(end)
    direction = end - start
    length = direction.length
    if length < 0.0001:
        return add_ico(name, start, (radius, radius, radius), material, subdivisions=1)

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=12,
        radius=radius,
        depth=length,
        location=(start + end) * 0.5,
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    attach_material(obj, material)
    apply_surface_shading(obj, smooth=SMOOTH_ROUND_PARTS)
    return obj


def add_flat_mesh(name, vertices, faces, material):
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    attach_material(obj, material)
    apply_flat_shading(obj)
    return obj


def add_wing(name, side, material):
    """Create a faceted wing as a small triangle fan."""
    s = float(side)
    vertices = [
        (s * 0.25, 0.20, 1.90),
        (s * 0.62, 0.26, 2.38),
        (s * 1.08, 0.30, 2.62),
        (s * 1.55, 0.32, 2.50),
        (s * 1.85, 0.30, 2.05),
        (s * 1.65, 0.27, 1.72),
        (s * 1.55, 0.25, 1.45),
        (s * 0.90, 0.22, 1.48),
        (s * 0.55, 0.20, 1.66),
        (s * 1.22, 0.30, 1.98),
    ]
    faces = [
        (0, 1, 9),
        (1, 2, 9),
        (2, 3, 9),
        (3, 4, 9),
        (4, 5, 9),
        (5, 6, 9),
        (6, 7, 9),
        (7, 8, 9),
        (8, 0, 9),
    ]
    # Mirroring the vertices reverses the winding order. Flip the face order
    # on the left wing so both wings receive light from the same side.
    if side < 0:
        faces = [tuple(reversed(face)) for face in faces]

    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    attach_material(obj, material)
    apply_flat_shading(obj)
    return obj


def add_lapel(name, side, material):
    s = float(side)
    vertices = [
        (s * 0.05, -0.51, 2.05),
        (s * 0.40, -0.57, 2.18),
        (s * 0.18, -0.59, 1.66),
        (s * 0.02, -0.54, 1.92),
    ]
    faces = [(0, 1, 2), (0, 2, 3)]
    return add_flat_mesh(name, vertices, faces, material)


def add_fallback_armature():
    """Make a preview armature with Navi-like bone names.

    This is only a local preview. A real Fast64 export should use the armature
    imported from gFairySkel in the OoT decomp project.
    """
    armature_data = bpy.data.armatures.new("NaviFairyArmatureData")
    armature = bpy.data.objects.new("NaviFairyArmature", armature_data)
    bpy.context.collection.objects.link(armature)
    armature.show_in_front = True

    deselect_all()
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")

    root = armature_data.edit_bones.new("bone000_gFairySkelLimb_0")
    root.head = (0.0, 0.0, 0.0)
    root.tail = (0.0, 0.0, 1.0)

    for index in range(1, 14):
        bone = armature_data.edit_bones.new(
            "bone{0:03d}_gFairySkelLimb_{0}".format(index)
        )
        bone.parent = root
        bone.head = (0.0, 0.0, 0.15 + index * 0.03)
        bone.tail = (0.0, 0.0, 0.45 + index * 0.03)

    bpy.ops.object.mode_set(mode="OBJECT")
    return armature


# -----------------------------------------------------------------------------
# Optional Fast64 integration
# -----------------------------------------------------------------------------


def configure_fast64_scene(scene, decomp_path):
    """Fill legacy Fast64 scene properties omitted by some Blender 5.2 installs."""
    added = []
    if not hasattr(bpy.types.Scene, "ootDecompPath"):
        bpy.types.Scene.ootDecompPath = bpy.props.StringProperty(
            name="OoT Decomp Folder", subtype="DIR_PATH"
        )
        added.append("ootDecompPath")
    if not hasattr(bpy.types.Scene, "saveTextures"):
        bpy.types.Scene.saveTextures = bpy.props.BoolProperty(
            name="Save Textures As PNGs", default=False
        )
        added.append("saveTextures")

    scene.ootDecompPath = decomp_path
    scene.saveTextures = False
    try:
        scene.fast64.oot.oot_version = "ntsc-1.0"
    except Exception:
        pass
    if added:
        log("Added Blender 5.2 Fast64 compatibility properties: " + ", ".join(added))


def import_navi_with_fast64():
    if not IMPORT_NAVI_FROM_DECOMP or not OOT_DECOMP_PATH:
        return None

    if not hasattr(bpy.ops.object, "oot_import_skeleton"):
        log("Fast64 OoT importer is not available; using fallback armature.")
        return None

    scene = bpy.context.scene
    decomp_path = os.path.abspath(os.path.expanduser(OOT_DECOMP_PATH))
    if not os.path.isdir(decomp_path):
        log("OoT decomp path does not exist; using fallback armature: " + decomp_path)
        return None

    try:
        scene.gameEditorMode = "OOT"
    except Exception:
        pass

    try:
        configure_fast64_scene(scene, decomp_path)
        settings = scene.fast64.oot.skeletonImportSettings
        settings.mode = "Generic"
        settings.name = "gFairySkel"
        settings.folder = "gameplay_keep"
        settings.actorOverlayName = "ovl_En_Elf"
        # The generated replacement keeps ZeldaRET's existing gFairyAnim.
        # Importing every animation referenced by split gameplay_keep sources
        # makes Fast64 chase unrelated symbols such as gArrow1_Anim and abort
        # before returning the otherwise valid gFairySkel armature.
        settings.import_animations = False
        settings.importNormals = True
        settings.removeDoubles = True
        settings.autoDetectActorScale = True

        deselect_all()
        bpy.ops.object.oot_import_skeleton()
        armature = find_armature()
        if armature:
            armature.name = "NaviFairyArmature"
            log("Imported gFairySkel from OoT decomp.")
        return armature
    except Exception as exc:
        log("Fast64 import failed: " + repr(exc))
        log("Continuing with fallback armature.")
        return None


def convert_materials_to_f3d():
    """Use Fast64's current BSDF converter when the addon is installed."""
    scene = bpy.context.scene
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]

    def converted():
        materials = {
            slot.material
            for obj in meshes
            for slot in obj.material_slots
            if slot.material is not None
        }
        return bool(materials) and all(getattr(material, "is_f3d", False) for material in materials)

    # Fast64's registered operator is the preferred path on supported Blender
    # releases.
    try:
        if hasattr(scene, "bsdf_conv_all"):
            scene.bsdf_conv_all = True
        if hasattr(scene, "rename_uv_maps"):
            scene.rename_uv_maps = True

        deselect_all()
        for obj in meshes:
            obj.select_set(True)
        if meshes and hasattr(bpy.ops.object, "convert_bsdf"):
            bpy.context.view_layer.objects.active = meshes[0]
            bpy.ops.object.convert_bsdf()
            if converted():
                log("Converted generated materials to Fast64 F3D materials.")
                return True
    except Exception as exc:
        log("Fast64 registered material converter failed: " + repr(exc))

    # Blender 5.2 can load Fast64's OoT operators while failing to register the
    # legacy material-conversion operator. The implementation is still usable,
    # so locate the enabled package and invoke it directly.
    roots = []
    export_class = getattr(bpy.types, "OOT_ExportSkeleton", None)
    if export_class is not None and ".fast64_internal" in export_class.__module__:
        roots.append(export_class.__module__.partition(".fast64_internal")[0])
    roots.extend(
        name
        for name in bpy.context.preferences.addons.keys()
        if "fast64" in name.lower()
    )
    loaded_converter_modules = [
        name for name in sys.modules if name.endswith("fast64_internal.f3d_material_converter")
    ]

    failures = []
    module_names = loaded_converter_modules + [
        root + ".fast64_internal.f3d_material_converter" for root in roots if root
    ]
    module_names.append("fast64_internal.f3d_material_converter")
    for module_name in dict.fromkeys(module_names):
        try:
            converter = importlib.import_module(module_name)
            converter.convertAllBSDFtoF3D(meshes, True)
            if converted():
                log("Converted generated materials through the Blender 5.2 Fast64 fallback.")
                return True
            failures.append(module_name + " left non-F3D materials")
        except Exception as exc:
            failures.append(module_name + ": " + repr(exc))

    if failures:
        log("Fast64 direct material conversion failed: " + " | ".join(failures))
    else:
        log("Fast64 material converter module could not be located.")
    return False


def export_with_fast64(armature):
    if not EXPORT_WITH_FAST64:
        return False
    if not hasattr(bpy.ops.object, "oot_export_skeleton"):
        log("Fast64 OoT exporter is not available; skipping export.")
        return False

    scene = bpy.context.scene
    try:
        # Generic Fast64 exports derive the C skeleton symbol from the Blender
        # armature name. En_Elf links against gFairySkel, so keep that exact
        # symbol instead of exporting a parallel NaviFairyArmature skeleton.
        armature.name = "gFairySkel"
        settings = scene.fast64.oot.skeletonExportSettings
        settings.mode = "Generic"
        settings.folder = "gameplay_keep"
        settings.actorOverlayName = "ovl_En_Elf"
        settings.removeVanillaData = True
        settings.isCustom = False
        settings.isCustomFilename = True
        settings.filename = "fairy_skel"

        deselect_all()
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.oot_export_skeleton()
        log("Fast64 skeleton export completed.")
        return True
    except Exception as exc:
        log("Fast64 export failed: " + repr(exc))
        return False


# -----------------------------------------------------------------------------
# Character construction
# -----------------------------------------------------------------------------


def build_character():
    # Match the reference's recognizable features while preserving an OoT
    # low-poly treatment: swept blond hair, narrowed eyes, heavy brows, a
    # long nose, pursed frown, navy suit, white shirt, and red tie.
    if OOT_STYLE:
        skin_color = (0.66, 0.29, 0.13)
        hair_color = (0.92, 0.52, 0.10)
        hair_highlight_color = (1.00, 0.75, 0.34)
        hair_shadow_color = (0.48, 0.15, 0.015)
        suit_color = (0.025, 0.035, 0.085)
        shirt_color = (0.78, 0.78, 0.70)
        tie_color = (0.55, 0.018, 0.025)
        wing_color = (0.30, 0.68, 0.92)
    else:
        skin_color = (0.86, 0.52, 0.34)
        hair_color = (0.95, 0.55, 0.08)
        hair_highlight_color = (1.0, 0.78, 0.38)
        hair_shadow_color = (0.66, 0.25, 0.025)
        suit_color = (0.035, 0.07, 0.18)
        shirt_color = (0.95, 0.95, 0.88)
        tie_color = (0.75, 0.03, 0.025)
        wing_color = (0.72, 0.90, 1.0)

    skin = make_material("TrumpFairy_Skin", skin_color)
    hair = make_material("TrumpFairy_Hair", hair_color)
    hair_highlight = make_material("TrumpFairy_HairHighlight", hair_highlight_color)
    hair_shadow = make_material("TrumpFairy_HairShadow", hair_shadow_color)
    suit = make_material("TrumpFairy_Suit", suit_color)
    shirt = make_material("TrumpFairy_Shirt", shirt_color)
    tie = make_material("TrumpFairy_Tie", tie_color)
    eye_white = make_material("TrumpFairy_EyeWhite", (0.72, 0.70, 0.62))
    eye_dark = make_material("TrumpFairy_EyeDark", (0.025, 0.012, 0.01))
    mouth = make_material("TrumpFairy_Mouth", (0.17, 0.012, 0.012))
    lip = make_material("TrumpFairy_Lip", (0.48, 0.055, 0.045))
    shoe = make_material("TrumpFairy_Shoes", (0.02, 0.015, 0.012))
    wing = make_material("TrumpFairy_Wings", wing_color, alpha=0.62 if OOT_STYLE else 1.0)

    round_subdivisions = 2 if OOT_STYLE else (3 if HIGH_POLY_PREVIEW else 2)
    detail_subdivisions = 1 if OOT_STYLE else (2 if HIGH_POLY_PREVIEW else 1)
    parts = []

    # Navy's body becomes a compact suit torso with the original fairy flight.
    parts.append(add_ico("TrumpFairy_SuitBody", (0.0, 0.0, 1.42), (0.80, 0.50, 0.92), suit, round_subdivisions))
    parts.append(add_ico("TrumpFairy_ShirtFront", (0.0, -0.47, 1.72), (0.25, 0.08, 0.50), shirt, detail_subdivisions))
    parts.append(add_lapel("TrumpFairy_Lapel_L", -1, suit))
    parts.append(add_lapel("TrumpFairy_Lapel_R", 1, suit))
    parts.append(add_cone("TrumpFairy_Tie", (0.0, -0.59, 1.57), 0.13, 0.035, 0.72, tie, (0.0, 0.0, 0.0)))
    parts.append(add_ico("TrumpFairy_TieKnot", (0.0, -0.62, 1.98), (0.14, 0.065, 0.13), tie, detail_subdivisions))
    parts.append(add_cylinder_between("TrumpFairy_Arm_L", (-0.58, 0.0, 1.86), (-0.96, -0.02, 1.18), 0.19, suit))
    parts.append(add_cylinder_between("TrumpFairy_Arm_R", (0.58, 0.0, 1.86), (0.96, -0.02, 1.18), 0.19, suit))
    parts.append(add_ico("TrumpFairy_Hand_L", (-0.96, -0.02, 1.08), (0.20, 0.18, 0.20), skin, detail_subdivisions))
    parts.append(add_ico("TrumpFairy_Hand_R", (0.96, -0.02, 1.08), (0.20, 0.18, 0.20), skin, detail_subdivisions))
    parts.append(add_ico("TrumpFairy_Shoe_L", (-0.36, -0.12, 0.38), (0.28, 0.38, 0.14), shoe, detail_subdivisions))
    parts.append(add_ico("TrumpFairy_Shoe_R", (0.36, -0.12, 0.38), (0.28, 0.38, 0.14), shoe, detail_subdivisions))

    # Broad, low-poly head with a heavier jaw than the previous fairy face.
    parts.append(add_ico("TrumpFairy_Head", (0.0, 0.0, 2.70), (0.76, 0.60, 0.73), skin, round_subdivisions))
    parts.append(add_ico("TrumpFairy_Jaw", (0.0, -0.12, 2.43), (0.50, 0.38, 0.31), skin, detail_subdivisions))
    parts.append(add_ico("TrumpFairy_Ear_L", (-0.70, 0.0, 2.70), (0.15, 0.18, 0.20), skin, detail_subdivisions))
    parts.append(add_ico("TrumpFairy_Ear_R", (0.70, 0.0, 2.70), (0.15, 0.18, 0.20), skin, detail_subdivisions))

    # High forehead, comb-over, and layered blond hair.
    parts.append(add_ico("TrumpFairy_HairCap", (0.02, 0.05, 3.16), (0.80, 0.56, 0.30), hair, round_subdivisions))
    parts.append(add_ico("TrumpFairy_HairSweep", (0.10, -0.16, 3.28), (0.68, 0.30, 0.19), hair_highlight, detail_subdivisions))
    for index, location, scale, material_choice in [
        (0, (-0.57, -0.04, 3.16), (0.34, 0.30, 0.16), hair_shadow),
        (1, (-0.35, -0.25, 3.27), (0.36, 0.22, 0.15), hair),
        (2, (-0.02, -0.35, 3.33), (0.38, 0.18, 0.13), hair_highlight),
        (3, (0.32, -0.28, 3.31), (0.38, 0.20, 0.14), hair),
        (4, (0.58, -0.08, 3.19), (0.32, 0.25, 0.16), hair_shadow),
    ]:
        parts.append(add_ico("TrumpFairy_HairLock_{0}".format(index), location, scale, material_choice, detail_subdivisions))
    parts.append(add_ico("TrumpFairy_Sideburn_L", (-0.62, -0.18, 2.91), (0.12, 0.12, 0.24), hair_shadow, detail_subdivisions))
    parts.append(add_ico("TrumpFairy_Sideburn_R", (0.62, -0.18, 2.91), (0.12, 0.12, 0.24), hair_shadow, detail_subdivisions))

    # Reference-like narrowed eyes, furrowed brows, strong nose, and frown.
    parts.append(add_ico("TrumpFairy_Eye_L", (-0.26, -0.585, 2.79), (0.13, 0.045, 0.075), eye_white, detail_subdivisions))
    parts.append(add_ico("TrumpFairy_Eye_R", (0.26, -0.585, 2.79), (0.13, 0.045, 0.075), eye_white, detail_subdivisions))
    parts.append(add_ico("TrumpFairy_Pupil_L", (-0.25, -0.635, 2.79), (0.040, 0.020, 0.050), eye_dark, detail_subdivisions))
    parts.append(add_ico("TrumpFairy_Pupil_R", (0.25, -0.635, 2.79), (0.040, 0.020, 0.050), eye_dark, detail_subdivisions))
    parts.append(add_cylinder_between("TrumpFairy_Brow_L", (-0.42, -0.61, 2.98), (-0.08, -0.65, 2.91), 0.055, hair_shadow))
    parts.append(add_cylinder_between("TrumpFairy_Brow_R", (0.08, -0.65, 2.91), (0.42, -0.61, 2.98), 0.055, hair_shadow))
    parts.append(add_ico("TrumpFairy_NoseBridge", (0.0, -0.49, 2.73), (0.15, 0.18, 0.24), skin, detail_subdivisions))
    parts.append(add_cone("TrumpFairy_Nose", (0.0, -0.69, 2.60), 0.18, 0.03, 0.42, skin, (math.pi / 2.0, 0.0, 0.0)))
    parts.append(add_cylinder_between("TrumpFairy_Frown_L", (-0.20, -0.63, 2.40), (0.0, -0.66, 2.35), 0.035, mouth))
    parts.append(add_cylinder_between("TrumpFairy_Frown_R", (0.0, -0.66, 2.35), (0.20, -0.63, 2.40), 0.035, mouth))
    parts.append(add_ico("TrumpFairy_LowerLip", (0.0, -0.65, 2.31), (0.16, 0.025, 0.045), lip, detail_subdivisions))

    # Navi wings stay behind the suit; this is still a fairy replacement.
    parts.append(add_wing("TrumpFairy_Wing_L", -1, wing))
    parts.append(add_wing("TrumpFairy_Wing_R", 1, wing))

    for obj in parts:
        obj.scale = obj.scale * MODEL_SCALE

    return parts


def add_oot_glow(armature):
    """Add a preview-only, faceted glow behind the fairy."""
    if not ADD_OOT_GLOW or EXPORT_WITH_FAST64:
        return None

    glow_material = make_material("TrumpFairy_OoTGlow", (0.55, 0.82, 1.0), alpha=0.20)
    glow = add_ico(
        "TrumpFairy_OoTGlow_PREVIEW_ONLY",
        (0.0, 0.30, 1.75),
        (1.35, 0.08, 1.35),
        glow_material,
        subdivisions=2,
        smooth=False,
    )
    glow.parent = armature
    glow["Fast64_preview_only"] = True
    glow["Fast64_export_note"] = "Delete or hide this glow before final ROM export if needed."
    return glow


def join_and_bind(parts, armature):
    if not parts:
        raise RuntimeError("No generated mesh parts were created.")

    root_name = get_root_bone(armature).name
    wing_names = {
        side: {
            position: get_limb_bone(armature, index).name
            for position, index in positions.items()
        }
        for side, positions in WING_BONES.items()
    }

    # Bind body geometry to the fairy root. Split each generated wing between
    # the real upper/lower wing limbs so the original gFairyAnim motion is
    # retained after Fast64 export.
    for obj in parts:
        if obj.name.startswith("TrumpFairy_Wing_"):
            side = "L" if obj.name.endswith("_L") else "R"
            upper = obj.vertex_groups.new(name=wing_names[side]["upper"])
            lower = obj.vertex_groups.new(name=wing_names[side]["lower"])
            upper_indices = [vertex.index for vertex in obj.data.vertices if vertex.co.z >= 2.0]
            lower_indices = [vertex.index for vertex in obj.data.vertices if vertex.co.z < 2.0]
            if upper_indices:
                upper.add(upper_indices, 1.0, "REPLACE")
            if lower_indices:
                lower.add(lower_indices, 1.0, "REPLACE")
        else:
            group = obj.vertex_groups.new(name=root_name)
            group.add([vertex.index for vertex in obj.data.vertices], 1.0, "REPLACE")

    deselect_all()
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    mesh_obj = bpy.context.object
    mesh_obj.name = "NaviTrump_F3D_Mesh"

    # Preserve the generated mesh's world position when making it an armature
    # child, even when Fast64 imported the armature with a non-unit scale.
    world_matrix = mesh_obj.matrix_world.copy()
    mesh_obj.parent = armature
    mesh_obj.matrix_world = world_matrix

    modifier = mesh_obj.modifiers.new(name="NaviFairyArmature", type="ARMATURE")
    modifier.object = armature

    mesh_obj["Fast64_example_note"] = "Body uses the fairy root; wings use limbs 4, 7, 11, and 14."

    if EXPORT_WITH_FAST64:
        vertex_count = len(mesh_obj.data.vertices)
        material_count = len(mesh_obj.data.materials)
        if vertex_count > MAX_EXPORT_VERTICES:
            raise RuntimeError(
                "Model has {0} vertices; export budget is {1}.".format(
                    vertex_count, MAX_EXPORT_VERTICES
                )
            )
        if material_count > MAX_EXPORT_MATERIALS:
            raise RuntimeError(
                "Model has {0} materials; export budget is {1}.".format(
                    material_count, MAX_EXPORT_MATERIALS
                )
            )

    return mesh_obj


# -----------------------------------------------------------------------------
# Preview scene and save
# -----------------------------------------------------------------------------


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_preview_camera_and_light():
    bpy.ops.object.camera_add(location=(4.0, -6.4, 3.6))
    camera = bpy.context.object
    camera.name = "PreviewCamera"
    look_at(camera, (0.0, 0.0, 1.7))
    bpy.context.scene.camera = camera

    bpy.ops.object.light_add(type="AREA", location=(3.5, -4.0, 6.0))
    key = bpy.context.object
    key.name = "PreviewKey"
    key.data.energy = 700.0
    key.data.shape = "DISK"
    key.data.size = 5.0
    look_at(key, (0.0, 0.0, 1.6))

    bpy.ops.object.light_add(type="AREA", location=(-4.0, 1.0, 3.0))
    fill = bpy.context.object
    fill.name = "PreviewFill"
    fill.data.energy = 300.0
    fill.data.size = 4.0
    look_at(fill, (0.0, 0.0, 1.5))


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
    if "__file__" in globals():
        base = os.path.dirname(os.path.abspath(__file__))
    else:
        base = bpy.path.abspath("//")
    return os.path.abspath(os.path.join(base, OUTPUT_BLEND))


def main():
    existing_armature = find_armature()
    imported_armature = None

    if IMPORT_NAVI_FROM_DECOMP and OOT_DECOMP_PATH:
        clear_scene()
        imported_armature = import_navi_with_fast64()
    else:
        # Preserve a manually imported Navi armature if one is already open.
        clear_scene(existing_armature)

    armature = imported_armature or existing_armature or find_armature()
    if armature is None:
        armature = add_fallback_armature()
        log("Created fallback preview armature.")
    else:
        armature.name = "NaviFairyArmature"
        # Remove old imported mesh children so the generated model is the only
        # visible mesh under the skeleton.
        delete_objects([obj for obj in list(armature.children) if obj.type == "MESH"])
        log("Reusing armature: " + armature.name)

    parts = build_character()
    mesh_obj = join_and_bind(parts, armature)
    add_oot_glow(armature)
    add_preview_camera_and_light()
    set_preview_settings()

    # Fast64 converts all visible mesh materials at once when this operator is
    # available. If Fast64 is absent, the blend still opens normally.
    materials_converted = convert_materials_to_f3d()

    if EXPORT_WITH_FAST64:
        if imported_armature is None:
            raise RuntimeError("Fast64 could not import the real gFairySkel; export aborted.")
        if not materials_converted:
            raise RuntimeError("Fast64 could not convert the generated materials to F3D.")
        if not export_with_fast64(armature):
            raise RuntimeError("Fast64 could not export the Trump Navi model.")

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
