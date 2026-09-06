"""Validate and, when possible, enable Fast64 inside Blender."""

import addon_utils
import bpy


def operator_exists(operator):
    """bpy.ops fabricates attributes, so ask Blender for registered RNA."""
    try:
        operator.get_rna_type()
        return True
    except (AttributeError, RuntimeError):
        return False


def fast64_ready():
    return (
        hasattr(bpy.context.scene, "fast64")
        and operator_exists(bpy.ops.object.oot_import_skeleton)
        and operator_exists(bpy.ops.object.oot_export_skeleton)
    )


def fast64_candidates():
    candidates = []
    for module in addon_utils.modules(refresh=True):
        info = getattr(module, "bl_info", {}) or {}
        label = str(info.get("name", ""))
        if "fast64" in module.__name__.lower() or "fast64" in label.lower():
            candidates.append(module)
    return candidates


def main():
    if not (4, 0, 0) <= bpy.app.version < (6, 0, 0):
        raise RuntimeError(
            "Ocarina of Trump requires Blender 4.x or 5.x; "
            f"found {bpy.app.version_string}"
        )
    candidates = fast64_candidates()
    enable_errors = []
    if not fast64_ready():
        for module in candidates:
            try:
                addon_utils.enable(module.__name__, default_set=True, persistent=True)
            except Exception as exc:
                enable_errors.append(module.__name__ + ": " + repr(exc))
            if fast64_ready():
                bpy.ops.wm.save_userpref()
                print("OOT_TRUMP_FAST64_ENABLED=" + module.__name__)
                break

    if not fast64_ready():
        installed = ", ".join(module.__name__ for module in candidates) or "none"
        enabled = ", ".join(
            addon.module
            for addon in bpy.context.preferences.addons
            if "fast64" in addon.module.lower()
        ) or "none"
        detail = " | ".join(enable_errors) or "no Fast64 add-on candidate could be enabled"
        raise RuntimeError(
            "Fast64 is not loaded with its OoT operators and scene properties. "
            f"Installed candidates: {installed}. Enabled Fast64 modules: {enabled}. {detail}"
        )

    print("OOT_TRUMP_MODEL_TOOLS_OK=" + bpy.app.version_string)


if __name__ == "__main__":
    main()
