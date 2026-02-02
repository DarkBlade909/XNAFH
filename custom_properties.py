import bpy
from bpy.props import BoolProperty, EnumProperty, PointerProperty, CollectionProperty, IntProperty
from bpy.types import PropertyGroup
from .bpy_util import get_selected_tex, dds_properties_exist
from .dxgi_format import DXGI_FORMAT

fmt_list = [fmt.name for fmt in DXGI_FORMAT]
fmt_list = [fmt for fmt in fmt_list if "BC" in fmt] + [fmt for fmt in fmt_list if "BC" not in fmt]

alt_format = {
    "BC1_UNORM": " (DXT1)",
    "BC3_UNORM": " (DXT5)",
    "BC4_UNORM": " (ATI1)",
    "BC5_UNORM": " (ATI2)",
}


def get_alt_fmt(fmt):
    """Add alt name for the format."""
    if fmt in alt_format:
        return fmt + alt_format[fmt]
    return fmt


def is_supported(fmt):
    return ('TYPELESS' not in fmt) and\
           (len(fmt) > 4) and (fmt not in {"UNKNOWN", "OPAQUE_420"})


DDS_FMT_ITEMS = [(fmt, get_alt_fmt(fmt), '') for fmt in fmt_list if is_supported(fmt)]
DDS_FMT_NAMES = [fmt for fmt in fmt_list if is_supported(fmt)]
