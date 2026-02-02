bl_info = {
    "name": "For Honor ASCII Import",
    "author": "DarkBlade909",
    "version": (2, 2, 4),
    "blender": (5, 0, 0),
    "location": "File > Import-Export",
    "description": "Community-maintained fork of the original XNALara/XPS Tools. Fully Blender 5.0+ compatible.",
    "category": "Import-Export",
    "support": "COMMUNITY",
    "credits": "2025 johnzero7 (original author), 2025 Clothoid, 2025 XNALara/XPS community, 2025 maylog (Blender 5.0+ update & Extensions submission), 2026 DarkBlade909",
}

from . import (
    xps_tools,
    xps_toolshelf,
    xps_const,
    xps_types,
    xps_material,
    write_ascii_xps,
    write_bin_xps,
    read_ascii_xps,
    read_bin_xps,
    mock_xps_data,
    import_xnalara_model,
    import_xnalara_pose,
    ascii_ops,
    bin_ops,
    timing,
    material_creator,
    node_shader_utils,
    import_dds,
    custom_properties,
    texconv,
    astcenc,
)


modules = (
    xps_const,
    xps_types,
    xps_material,
    read_ascii_xps,
    read_bin_xps,
    write_ascii_xps,
    write_bin_xps,
    mock_xps_data,
    material_creator,
    node_shader_utils,
    timing,
    ascii_ops,
    bin_ops,
    import_xnalara_model,
    import_xnalara_pose,
    xps_tools,
    xps_toolshelf,
    import_dds,
    texconv,
    astcenc,
)

def register():
    for mod in modules:
        if hasattr(mod, "register"):
            mod.register()

def unregister():
    for mod in reversed(modules):
        if hasattr(mod, "unregister"):
            mod.unregister()
    unload_texconv()
    unload_astcenc()