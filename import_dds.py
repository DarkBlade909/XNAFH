"""UI panel and operator to import DDS files."""

import os
import time
import shutil
import tempfile
import traceback

import bpy
from bpy.props import StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
import numpy as np

from .dds import DDSHeader, DDS
from .texconv import Texconv
from .astcenc import Astcenc
from .bpy_util import (get_image_editor_space,
                       load_texture, load_texture_from_buffer,
                       dds_properties_exist, flush_stdout, dxgi_to_dtype)
from .custom_properties import DDS_FMT_NAMES


def load_uncompressed_dds(file, cubemap_layout='h-cross',
                          premultiplied_alpha=False, color_space='Non-Color'):
    dds = DDS.load(file)
    w, h = dds.header.width, dds.header.height
    bpb = dds.header.get_byte_per_block()
    fmt = dds.header.get_format_as_str()
    buffers = [b[:bpb * w * h] for b in dds.slice_bin_list]
    tex = load_texture_from_buffer(os.path.basename(file)[:-4],
                                   w, h, buffers,
                                   dxgi_to_dtype(fmt),
                                   premultiplied_alpha=premultiplied_alpha,
                                   cubemap_layout=cubemap_layout,
                                   color_space=color_space)
    return tex


def load_dds_via_tga(texconv, file, out_dir, cubemap_layout='h-cross',
                     invert_normals=False, premultiplied_alpha=False, color_space='Non-Color'):
    tga = texconv.convert_to_tga(file, out=out_dir, cubemap_layout=cubemap_layout,
                                 invert_normals=invert_normals, premultiplied_alpha=premultiplied_alpha)
    if tga is None:
        raise RuntimeError('Failed to convert texture.')
    tex = load_texture(tga, name=os.path.basename(tga)[:-4], color_space=color_space)
    return tex


def load_dds(file, invert_normals=False,
             premultiplied_alpha=False,
             cubemap_layout='h-cross',
             colorspace_ldr='sRGB', colorspace_hdr='Non-Color',
             texconv=None, astcenc=None):
    """Import a texture form .dds file.

    Args:
        file (string): file path to .dds file
        invert_normals (bool): Flip y axis if the texture is normal map.
        premultiplied_alpha (bool): Convert premultiplied alpha to straight alpha.
        cubemap_layout (string): Layout for cubemap faces.
        colorspace_ldr: Color space for LDR textures.
        colorspace_hdr: Color space for HDR textures.
        texconv (Texconv): Texture converter for dds.
        astcenc (Astcenc): Astc converter.

    Returns:
        tex (bpy.types.Image): loaded texture
    """
    tex_list = []
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = os.path.join(temp_dir, os.path.basename(file))
            shutil.copyfile(file, temp)

            if texconv is None:
                texconv = Texconv()
            if astcenc is None:
                astcenc = Astcenc()

            dds_header = DDSHeader.read_from_file(temp)

            if dds_header.is_astc():
                dds = DDS.load(temp)
                dds.remove_mips()
                dds.decompress_astc(astcenc)
                dds.save(temp)

            # Check dxgi_format
            if dds_header.is_hdr():
                color_space = colorspace_hdr
            else:
                color_space = colorspace_ldr

            fmt = dds_header.get_format_as_str()

            # Disassemble if it's a non-2D texture
            if dds_header.is_3d() or dds_header.is_array():
                dds = DDS.load(temp)
                dds_list = dds.get_disassembled_dds_list()
                base_name = os.path.basename(temp)
                for new_dds, i in zip(dds_list, range(len(dds_list))):
                    new_name = ".".join(base_name.split(".")[:-1])
                    if i >= 1:
                        new_name += f"-{i}"
                    new_name += ".dds"
                    new_path = os.path.join(temp_dir, new_name)
                    new_dds.save(new_path)
                    if fmt == "R32G32B32A32_FLOAT" or fmt == "R16G16B16A16_FLOAT":
                        tex = load_uncompressed_dds(new_path, cubemap_layout=cubemap_layout,
                                                    premultiplied_alpha=premultiplied_alpha,
                                                    color_space=color_space)
                    else:
                        tex = load_dds_via_tga(texconv, new_path, temp_dir, cubemap_layout=cubemap_layout,
                                               invert_normals=invert_normals,
                                               premultiplied_alpha=premultiplied_alpha,
                                               color_space=color_space)
                    tex_list.append(tex)
            else:
                if fmt == "R32G32B32A32_FLOAT" or fmt == "R16G16B16A16_FLOAT":
                    tex = load_uncompressed_dds(temp, cubemap_layout=cubemap_layout,
                                                premultiplied_alpha=premultiplied_alpha,
                                                color_space=color_space)
                else:
                    tex = load_dds_via_tga(texconv, temp, temp_dir, cubemap_layout=cubemap_layout,
                                           invert_normals=invert_normals,
                                           premultiplied_alpha=premultiplied_alpha,
                                           color_space=color_space)
                tex_list.append(tex)

        tex = tex_list[0]
        if dds_properties_exist():
            # Update custom properties
            props = tex.dds_props
            dxgi = dds_header.get_format_as_str()
            if dxgi in DDS_FMT_NAMES:
                props.dxgi_format = dxgi
            props.no_mip = dds_header.mipmap_num <= 1
            props.texture_type = dds_header.get_texture_type()
            if dds_header.is_cube():
                props.cubemap_layout = cubemap_layout
            if dds_header.is_3d() or dds_header.is_array():
                for tex in tex_list[1:]:
                    new_item = props.texture_list.add()
                    new_item.texture = tex

        for tex in tex_list:
            if cubemap_layout.endswith("-fnz"):
                # Flip -z face for cubemaps
                w, h = tex.size
                pix = np.array(tex.pixels).reshape((h, w, -1))
                if cubemap_layout[0] == "v":
                    pix[h//4 * 0: h//4 * 1, w//3 * 1: w//3 * 2] = \
                        (pix[h//4 * 0: h//4 * 1, w//3 * 1: w//3 * 2])[::-1, ::-1]
                else:
                    pix[h//3 * 1: h//3 * 2, w//4 * 3: w//4 * 4] = \
                        (pix[h//3 * 1: h//3 * 2, w//4 * 3: w//4 * 4])[::-1, ::-1]
                pix = pix.flatten()
                tex.pixels = list(pix)

            tex.update()

    except Exception as e:
        for tex in tex_list:
            if tex is not None:
                bpy.data.images.remove(tex)
        raise e

    return tex_list[0]


def import_dds(context, file, texconv=None, astcenc=None):
    """Import a file."""
    tex = load_dds(file, invert_normals=False,
                   premultiplied_alpha=False,
                   cubemap_layout='h-cross',
                   colorspace_ldr='sRGB', colorspace_hdr='Non-Color',
                   texconv=texconv, astcenc=astcenc)


def import_dds_rec(context, folder, texconv=None, astcenc=None):
    """Search a folder recursively, and import found dds files."""
    count = 0
    for file in sorted(os.listdir(folder)):
        path = os.path.join(folder, file)
        if os.path.isdir(path):
            count += import_dds_rec(context, path)
        elif file.split('.')[-1].lower() == "dds":
            import_dds(context, path, texconv=texconv, astcenc=astcenc)
            count += 1
    return count
