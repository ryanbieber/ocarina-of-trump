"""Build and export the Trump fairy replacement for Blender + Fast64.

What this script does:
  * Builds a compact, N64-budget parody likeness with wings.
  * Reuses an already-imported OoT/Fast64 armature when one exists.
  * Can import gFairySkel automatically when OOT_DECOMP_PATH is configured.
  * Converts the generated Principled materials to Fast64 F3D materials when
    the Fast64 addon is installed.
  * Saves generated .blend files under the ignored .work/ directory.

Important:
  * The generated mesh is rigidly bound to Navi's display limb. En_Elf uses a
    rigid SkeletonHeader, so weighted/flex geometry will not render correctly.
  * Wings are intentionally static because every vertex uses that one limb.
  * Do not add bones to the imported Navi skeleton until the basic replacement
    works. En_Elf expects the original fairy skeleton structure.

Run from Blender's Scripting workspace, or from a Blender command line:

  blender --background --python scripts/build_fairy_model.py

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

# Relative output overrides resolve from the project root.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_BLEND = os.environ.get(
    "NAVI_TRUMP_BLEND_OUTPUT", os.path.join(PROJECT_ROOT, ".work", "trump_fairy.blend")
)
FACE_TEXTURE_PATH = os.path.join(
    PROJECT_ROOT,
    "trump_face",
    "trump_face_smug_n64.png",
)
FACE_TALKING_TEXTURE_PATH = os.path.join(
    PROJECT_ROOT,
    "trump_face",
    "trump_face_smug_talking_n64.png",
)

# Higher detail is useful while modeling. Before a final ROM export, you may
# want to reduce these values again because the original N64 renderer has tight
# memory and vertex limits.
HIGH_POLY_PREVIEW = True
# Smooth normals and carefully limited UV spheres give the face a recognizable
# silhouette without exceeding the actor's N64 vertex budget.
OOT_STYLE = True
SMOOTH_ROUND_PARTS = True
ADD_OOT_GLOW = True
MODEL_SCALE = float(os.environ.get("NAVI_TRUMP_MODEL_SCALE", "0.42"))

# SkelAnime uses one-based draw limb indices. EnElf_OverrideLimbDraw applies
# Navi's model scale at draw limb 8, which is Fast64's zero-based limb 7 bone.
FAIRY_MODEL_BONE = 7
MAX_EXPORT_VERTICES = 1800
MAX_EXPORT_MATERIALS = 16
# The pinned OoT asset XML declares 952 vertices across adult Link's active
# near-model limb display lists (child Link uses 895). Keep the replacement at
# least this detailed while retaining a conservative single-actor upper bound.
LINK_ADULT_NEAR_VERTEX_REFERENCE = 952
TRUMP_MATERIAL_COLORS = {}


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
    TRUMP_MATERIAL_COLORS[name] = (color[0], color[1], color[2], alpha)

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


def make_texture_material(name, image_path, image_name):
    """Create a Principled material Fast64 can convert to a cutout texture."""
    if not os.path.isfile(image_path):
        raise RuntimeError("Required Trump face texture is missing: " + image_path)

    material = make_material(name, (1.0, 1.0, 1.0))
    nodes = material.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    image = bpy.data.images.load(image_path, check_existing=True)
    image.name = image_name
    image.colorspace_settings.name = "sRGB"
    texture = nodes.new("ShaderNodeTexImage")
    texture.name = "TrumpFairyFaceImage"
    texture.image = image
    material.node_tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    if "Alpha" in bsdf.inputs:
        material.node_tree.links.new(texture.outputs["Alpha"], bsdf.inputs["Alpha"])
    # Marker retained for source inspection and validation. Cutout settings are
    # applied directly to the converted F3D material because Fast64's named
    # preset conversion is not stable across Blender releases.
    material["Fast64_cutout_texture"] = True
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


def sample_face_skin(image_path):
    """Match solid skin to opaque border texels, in Blender's linear space."""
    image = bpy.data.images.load(image_path, check_existing=True)
    width, height = image.size
    pixels = list(image.pixels)
    samples = []
    # Sample the UV boundary that meets solid skin, avoiding painted highlights.
    for x_fraction in (0.01, 0.99):
        for y_fraction in (0.40, 0.45, 0.50, 0.55):
            offset = 4 * (int(y_fraction * height) * width + int(x_fraction * width))
            if pixels[offset + 3] > 0.95:
                samples.append(pixels[offset:offset + 3])
    if not samples:
        raise RuntimeError("Face texture has no opaque cheek samples for skin matching")
    # Image pixels are encoded sRGB; BSDF and Fast64 color properties are linear.
    rgb = tuple(sorted(sample[c] for sample in samples)[len(samples) // 2] for c in range(3))
    linear = tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb)
    log("Matched skin to face border sRGB: " + repr(tuple(round(c, 3) for c in rgb)))
    return linear


def add_tailored_form(name, rings, material, segments=12):
    """Closed polygon rings give clothing a continuous, deliberately cut shape."""
    vertices = []
    for z, rx, ry, cx, cy in rings:
        for index in range(segments):
            angle = math.tau * index / segments
            vertices.append((cx + rx * math.cos(angle), cy + ry * math.sin(angle), z))
    faces = [tuple(reversed(range(segments)))]
    for ring in range(len(rings) - 1):
        for i in range(segments):
            j = (i + 1) % segments
            a, b = ring * segments, (ring + 1) * segments
            faces.append((a + i, a + j, b + j, b + i))
    faces.append(tuple((len(rings) - 1) * segments + i for i in range(segments)))
    obj = add_flat_mesh(name, vertices, faces, material)
    apply_surface_shading(obj, smooth=True)
    return obj


def add_wing(name, side, material):
    """Two narrow, pointed lobes echo Navi's silhouette without broad panels."""
    vertices, faces = [], []
    for outline in (
        ((0.35, 0.27, 1.84), (0.65, 0.34, 2.27), (1.24, 0.42, 2.66),
         (1.08, 0.37, 2.12), (0.68, 0.29, 1.83)),
        ((0.36, 0.29, 1.75), (0.77, 0.37, 1.68), (1.03, 0.42, 1.19),
         (0.64, 0.34, 1.35), (0.43, 0.29, 1.58)),
    ):
        base = len(vertices)
        vertices.extend((side * x, y, z) for x, y, z in outline)
        for i in range(1, len(outline) - 1):
            triangle = (base, base + i, base + i + 1)
            faces.append(tuple(reversed(triangle)) if side > 0 else triangle)
    return add_flat_mesh(name, vertices, faces, material)


def add_lapel(name, side, material):
    vertices = [(side * x, y, z) for x, y, z in (
        (0.15, -0.305, 2.04), (0.36, -0.325, 1.97),
        (0.23, -0.345, 1.79), (0.28, -0.35, 1.73), (0.07, -0.35, 1.38),
    )]
    faces = [(0, 1, 2), (0, 2, 4), (2, 3, 4)]
    if side > 0:
        faces = [tuple(reversed(face)) for face in faces]
    return add_flat_mesh(name, vertices, faces, material)


def head_geometry(segments=24, rings=16):
    """One welded head surface: front UVs, solid rear, and a real nose profile."""
    vertices, uvs = [(0.0, 0.0, 1.95)], [(0.5, 0.0)]
    for ring in range(1, rings):
        latitude = -math.pi / 2 + math.pi * ring / rings
        v = math.sin(latitude)
        radius = math.cos(latitude)
        # Narrow the lower jaw without pinching the brow or temples.
        jaw = 1.0 - 0.14 * max(0.0, -v)
        for index in range(segments):
            angle = math.tau * index / segments
            x = 0.67 * radius * math.sin(angle) * jaw
            y = -0.53 * radius * math.cos(angle)
            if math.cos(angle) > 0:
                nose = 0.16 * math.exp(-((x / 0.15) ** 2 + ((v + 0.06) / 0.24) ** 2))
                y -= nose * math.cos(angle)
            vertices.append((x, y, 2.67 + 0.72 * v))
            uvs.append((0.5 + 0.5 * math.sin(angle), 0.5 + 0.5 * v))
    top = len(vertices)
    vertices.append((0.0, 0.0, 3.39))
    uvs.append((0.5, 1.0))
    faces, materials = [], []
    for index in range(segments):
        nxt = (index + 1) % segments
        # Material boundary is exactly at the temples, shared by both halves.
        material = 0 if math.cos(math.tau * (index + 0.5) / segments) > 0 else 1
        faces.append((0, 1 + nxt, 1 + index))
        materials.append(material)
        for ring in range(rings - 2):
            a, b = 1 + ring * segments, 1 + (ring + 1) * segments
            faces.append((a + index, a + nxt, b + nxt, b + index))
            materials.append(material)
        last = 1 + (rings - 2) * segments
        faces.append((last + index, last + nxt, top))
        materials.append(material)
    return vertices, faces, uvs, materials


def add_textured_head(name, face, skin):
    vertices, faces, uvs, materials = head_geometry()
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for polygon, material in zip(mesh.polygons, materials):
        polygon.material_index = material
        for loop_index in polygon.loop_indices:
            uv_layer.data[loop_index].uv = uvs[mesh.loops[loop_index].vertex_index]
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    attach_material(obj, face)
    attach_material(obj, skin)
    apply_surface_shading(obj, smooth=True)
    return obj


def add_hidden_texture_carrier(name, material):
    """Keep an alternate face texture in the export without visible geometry."""
    vertices = [(-0.01, 0.0, 2.65), (0.01, 0.0, 2.65), (0.0, 0.0, 2.67)]
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], [(0, 1, 2)])
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for loop_index, uv in enumerate(((0.0, 0.0), (1.0, 0.0), (0.5, 1.0))):
        uv_layer.data[loop_index].uv = uv
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    attach_material(obj, material)
    return obj


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


def fast64_converter_module_names():
    roots = []
    export_class = getattr(bpy.types, "OOT_ExportSkeleton", None)
    if export_class is not None and ".fast64_internal" in export_class.__module__:
        roots.append(export_class.__module__.partition(".fast64_internal")[0])
    roots.extend(
        name
        for name in bpy.context.preferences.addons.keys()
        if "fast64" in name.lower()
    )
    loaded = [
        name for name in sys.modules if name.endswith("fast64_internal.f3d_material_converter")
    ]
    return list(
        dict.fromkeys(
            loaded
            + [root + ".fast64_internal.f3d_material_converter" for root in roots if root]
            + ["fast64_internal.f3d_material_converter"]
        )
    )


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
    failures = []
    for module_name in fast64_converter_module_names():
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


def apply_trump_colors_to_f3d(meshes):
    """Make Fast64 emit the generated colors instead of inheriting white actor lights."""
    updated = set()
    for obj in meshes:
        for slot in obj.material_slots:
            material = slot.material
            if material is None or material in updated or not getattr(material, "is_f3d", False):
                continue
            base_name = material.name.removesuffix("_f3d")
            color = TRUMP_MATERIAL_COLORS.get(base_name)
            if color is None:
                continue
            updated.add(material)
            with bpy.context.temp_override(material=material):
                f3d_mat = material.f3d_mat
                # Fast64's BSDF converter copies the color to this field but
                # its Shaded Solid preset leaves set_lights off. Enable the
                # generated light so each material exports its own hue.
                f3d_mat.use_default_lighting = True
                f3d_mat.set_ambient_from_light = True
                f3d_mat.default_light_color = color
                f3d_mat.set_lights = True
                # Blender 5.2's Fast64 fallback accepts its normal textured
                # conversion but does not consistently expose named cutout
                # presets. Apply the two material differences directly after
                # conversion: take alpha from TEXEL0 and use the N64 texture-
                # edge render mode. This also avoids the converter's broken
                # hidden material-library plane selection path.
                if base_name.startswith("TrumpFairy_Face"):
                    f3d_mat.combiner1.D_alpha = "TEXEL0"
                    f3d_mat.rdp_settings.set_rendermode = True
                    f3d_mat.rdp_settings.rendermode_preset_cycle_2 = "G_RM_AA_ZB_TEX_EDGE2"
                    f3d_mat.rdp_settings.g_cull_back = False
                    if hasattr(f3d_mat, "draw_layer") and hasattr(f3d_mat.draw_layer, "oot"):
                        f3d_mat.draw_layer.oot = "Opaque"
                else:
                    if base_name == "TrumpFairy_Wings":
                        # Thin rigid wings must remain visible from either side.
                        f3d_mat.rdp_settings.g_cull_back = False
                    f3d_mat.prim_color = (1.0, 1.0, 1.0, color[3])
                    f3d_mat.combiner1.D_alpha = "PRIMITIVE"
    if len(updated) != len(TRUMP_MATERIAL_COLORS):
        raise RuntimeError(
            "Applied explicit F3D colors to {0} of {1} Trump materials.".format(
                len(updated), len(TRUMP_MATERIAL_COLORS)
            )
        )
    log("Applied explicit colors to {0} Fast64 materials.".format(len(updated)))


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
    # The likeness is carried by silhouette and proportions rather than dense
    # geometry: broad forehead, tapered jaw, swept blond hair, narrowed eyes,
    # pronounced brows, rounded nose, pursed mouth, navy suit, and red tie.
    if OOT_STYLE:
        # Sample the actual cheek color instead of guessing a tan swatch.
        skin_color = sample_face_skin(FACE_TEXTURE_PATH)
        hair_color = (0.48, 0.30, 0.105)
        hair_highlight_color = (0.63, 0.43, 0.18)
        hair_shadow_color = (0.28, 0.16, 0.055)
        suit_color = (0.015, 0.025, 0.055)
        shirt_color = (0.92, 0.91, 0.84)
        tie_color = (0.68, 0.025, 0.035)
        wing_color = (0.65, 0.78, 0.86)
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
    shoe = make_material("TrumpFairy_Shoes", (0.02, 0.015, 0.012))
    wing = make_material("TrumpFairy_Wings", wing_color, alpha=0.42 if OOT_STYLE else 1.0)
    face = make_texture_material(
        "TrumpFairy_Face", FACE_TEXTURE_PATH, "TrumpFairyFaceTexture"
    )
    talking_face = make_texture_material(
        "TrumpFairy_FaceTalking",
        FACE_TALKING_TEXTURE_PATH,
        "TrumpFairyFaceTalkingTexture",
    )

    parts = []

    # A jacket hem and visible trousers replace the round floating toy body.
    parts.append(add_tailored_form("TrumpFairy_SuitBody", (
        (1.02, 0.43, 0.29, 0.0, 0.02), (1.26, 0.46, 0.31, 0.0, 0.02),
        (1.66, 0.49, 0.31, 0.0, 0.02), (1.96, 0.52, 0.28, 0.0, 0.02),
        (2.06, 0.28, 0.22, 0.0, 0.02),
    ), suit, 16))
    parts.append(add_flat_mesh("TrumpFairy_ShirtFront", [
        (-0.16, -0.29, 2.08), (-0.22, -0.33, 1.92), (0.0, -0.35, 1.42),
        (0.22, -0.33, 1.92), (0.16, -0.29, 2.08),
    ], [(0, 1, 2), (0, 2, 4), (2, 3, 4)], shirt))
    parts.append(add_lapel("TrumpFairy_Lapel_L", -1, suit))
    parts.append(add_lapel("TrumpFairy_Lapel_R", 1, suit))
    parts.append(add_flat_mesh("TrumpFairy_Tie", [
        (-0.045, -0.365, 1.93), (-0.07, -0.375, 1.39), (0.0, -0.38, 1.29),
        (0.07, -0.375, 1.39), (0.045, -0.365, 1.93),
    ], [(0, 1, 2), (0, 2, 4), (2, 3, 4)], tie))
    parts.append(add_tailored_form("TrumpFairy_TieKnot", (
        (1.89, 0.04, 0.025, 0.0, -0.355), (1.99, 0.07, 0.025, 0.0, -0.335),
    ), tie, 4))
    for side, suffix in ((-1, "L"), (1, "R")):
        parts.append(add_tailored_form("TrumpFairy_Sleeve_" + suffix, (
            (1.14, 0.115, 0.125, side * 0.61, -0.04),
            (1.53, 0.15, 0.16, side * 0.59, 0.01),
            (1.90, 0.17, 0.20, side * 0.47, 0.02),
        ), suit))
        parts.append(add_uv_sphere("TrumpFairy_Hand_" + suffix, (side * 0.61, -0.06, 1.04), (0.12, 0.11, 0.15), skin, 10, 6, True))
        parts.append(add_tailored_form("TrumpFairy_Trouser_" + suffix, (
            (0.30, 0.145, 0.17, side * 0.22, 0.015),
            (0.64, 0.16, 0.18, side * 0.22, 0.02),
            (1.10, 0.20, 0.23, side * 0.22, 0.02),
        ), suit))
        parts.append(add_uv_sphere("TrumpFairy_Shoe_" + suffix, (side * 0.22, -0.075, 0.27), (0.17, 0.29, 0.12), shoe, 10, 6, False))

    # One welded surface carries the expression and the solid rear scalp.
    parts.append(add_uv_sphere("TrumpFairy_Neck", (0.0, 0.0, 2.12), (0.19, 0.19, 0.24), skin, 8, 5, True))
    # The UV and solid regions share geometry and smooth normals at the temples.
    parts.append(add_textured_head("TrumpFairy_Head", face, skin))
    parts.append(add_uv_sphere("TrumpFairy_Ear_L", (-0.65, 0.0, 2.66), (0.11, 0.13, 0.18), skin, 10, 6, True))
    parts.append(add_uv_sphere("TrumpFairy_Ear_R", (0.65, 0.0, 2.66), (0.11, 0.13, 0.18), skin, 10, 6, True))

    # The layered comb-over is asymmetric and projects forward over the brow.
    # That silhouette remains readable when Navi is only a few pixels tall.
    parts.append(add_uv_sphere("TrumpFairy_HairCap", (0.0, 0.06, 3.15), (0.69, 0.49, 0.28), hair, 18, 10, True))
    forelock = add_uv_sphere("TrumpFairy_HairSweep", (0.0, -0.29, 3.21), (0.63, 0.23, 0.13), hair_highlight, 16, 7, True)
    forelock.rotation_euler.y = -0.10
    parts.append(forelock)
    parts.append(add_uv_sphere("TrumpFairy_Sideburn_L", (-0.57, -0.14, 2.88), (0.09, 0.09, 0.20), hair_shadow, 10, 6, True))
    parts.append(add_uv_sphere("TrumpFairy_Sideburn_R", (0.57, -0.14, 2.88), (0.09, 0.09, 0.20), hair_shadow, 10, 6, True))

    # Export the matching talking image for the existing segment-9 animation.
    parts.append(
        add_hidden_texture_carrier("TrumpFairy_FaceTalkingCarrier", talking_face)
    )

    # Keep the expression and hair aligned while giving the body more height.
    head_names = ("Head", "Ear_", "Hair", "Sideburn_", "Face")
    for obj in parts:
        if any(obj.name.startswith("TrumpFairy_" + prefix) for prefix in head_names):
            # Some helpers author vertices in world coordinates, others use
            # object transforms. Apply one common affine change to both.
            obj.location *= 0.80
            obj.location.z += 2.05 * 0.20 + 0.16
            obj.scale *= 0.80

    # Navi wings stay behind the suit; this is still a fairy replacement.
    parts.append(add_wing("TrumpFairy_Wing_L", -1, wing))
    parts.append(add_wing("TrumpFairy_Wing_R", 1, wing))

    # Navi's display limb is centered on the fairy, while these modeling
    # primitives were authored upward from the shoes. Center their real
    # world-space vertical bounds on the limb so neither head nor feet are
    # pushed off screen as the fairy flies near the camera.
    bpy.context.view_layer.update()
    vertical_bounds = [
        (obj.matrix_world @ Vector(corner)).z
        for obj in parts
        for corner in obj.bound_box
    ]
    vertical_center = (min(vertical_bounds) + max(vertical_bounds)) * 0.5
    for obj in parts:
        obj.location.z -= vertical_center
        # Scale both the primitive and its layout position. Scaling only
        # obj.scale made the old body smaller while leaving its parts spread
        # over the original oversized height.
        obj.location *= MODEL_SCALE
        obj.scale *= MODEL_SCALE
    log(
        "Centered refined model on Navi pivot and applied {0:.2f} scale "
        "(vertical offset {1:.3f}).".format(MODEL_SCALE, vertical_center)
    )

    return parts


def add_oot_glow(armature):
    """Add a preview-only, faceted glow behind the fairy."""
    if not ADD_OOT_GLOW or EXPORT_WITH_FAST64:
        return None

    glow_material = make_material("TrumpFairy_OoTGlow", (0.55, 0.82, 1.0), alpha=0.20)
    glow = add_ico(
        "TrumpFairy_OoTGlow_PREVIEW_ONLY",
        (0.0, 0.18, 0.0),
        (0.98, 0.05, 0.98),
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

    deselect_all()
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    mesh_obj = bpy.context.object
    mesh_obj.name = "NaviTrump_F3D_Mesh"

    # En_Elf uses the rigid skeleton initializer and draw routine. Make that
    # invariant explicit by giving the entire joined mesh exactly one bone
    # group. Limb 7 receives Navi's pulsing model scale at draw limb 8.
    model_bone_name = get_limb_bone(armature, FAIRY_MODEL_BONE).name
    armature.data.bones[model_bone_name].use_deform = True
    for group in list(mesh_obj.vertex_groups):
        mesh_obj.vertex_groups.remove(group)
    model_group = mesh_obj.vertex_groups.new(name=model_bone_name)
    model_group.add([vertex.index for vertex in mesh_obj.data.vertices], 1.0, "REPLACE")

    # Preserve the generated mesh's world position when making it an armature
    # child, even when Fast64 imported the armature with a non-unit scale.
    world_matrix = mesh_obj.matrix_world.copy()
    mesh_obj.parent = armature
    mesh_obj.matrix_world = world_matrix

    modifier = mesh_obj.modifiers.new(name="NaviFairyArmature", type="ARMATURE")
    modifier.object = armature

    mesh_obj["Fast64_example_note"] = "Rigid replacement uses gFairySkel draw limb 8."

    if EXPORT_WITH_FAST64:
        vertex_count = len(mesh_obj.data.vertices)
        material_count = len(mesh_obj.data.materials)
        if vertex_count < LINK_ADULT_NEAR_VERTEX_REFERENCE:
            raise RuntimeError(
                "Model has {0} vertices; adult Link's active near model uses {1}.".format(
                    vertex_count, LINK_ADULT_NEAR_VERTEX_REFERENCE
                )
            )
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
        log(
            "Validated {0} model vertices against adult Link's {1}-vertex "
            "near-model reference ({2} material slots).".format(
                vertex_count, LINK_ADULT_NEAR_VERTEX_REFERENCE, material_count
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
    bpy.ops.object.camera_add(location=(2.2, -3.6, 1.6))
    camera = bpy.context.object
    camera.name = "PreviewCamera"
    look_at(camera, (0.0, 0.0, 0.0))
    bpy.context.scene.camera = camera

    bpy.ops.object.light_add(type="AREA", location=(3.5, -4.0, 6.0))
    key = bpy.context.object
    key.name = "PreviewKey"
    key.data.energy = 700.0
    key.data.shape = "DISK"
    key.data.size = 5.0
    look_at(key, (0.0, 0.0, 0.0))

    bpy.ops.object.light_add(type="AREA", location=(-4.0, 1.0, 3.0))
    fill = bpy.context.object
    fill.name = "PreviewFill"
    fill.data.energy = 300.0
    fill.data.size = 4.0
    look_at(fill, (0.0, 0.0, 0.0))


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
        base = PROJECT_ROOT
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
    if materials_converted:
        apply_trump_colors_to_f3d([mesh_obj])

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
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path)
    log("Saved blend file: " + path)
    log("Finished. Render the preview or inspect the armature before exporting to OoT.")


if __name__ == "__main__":
    main()
