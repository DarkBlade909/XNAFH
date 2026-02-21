import bpy
import os
from pathlib import Path
import random
from mathutils import Vector
from . import xps_material
from . import xps_const
from .import_dds import import_dds
import importlib
import addon_utils

ALPHA_MODE_CHANNEL = 'CHANNEL_PACKED'
# Nodes Layout
NODE_FRAME = 'NodeFrame'

# Nodes Shaders
BSDF_DIFFUSE_NODE = 'ShaderNodeBsdfDiffuse'
BSDF_EMISSION_NODE = 'ShaderNodeEmission'
BSDF_GLOSSY_NODE = 'ShaderNodeBsdfGlossy'
PRINCIPLED_SHADER_NODE = 'ShaderNodeBsdfPrincipled'
BSDF_TRANSPARENT_NODE = 'ShaderNodeBsdfTransparent'
BSDF_GLASS_NODE = 'ShaderNodeBsdfGlass'
SHADER_ADD_NODE = 'ShaderNodeAddShader'
SHADER_MIX_NODE = 'ShaderNodeMixShader'

# Nodes Color
RGB_MIX_NODE = 'ShaderNodeMixRGB'
INVERT_NODE = 'ShaderNodeInvert'

# Nodes Input
TEXTURE_IMAGE_NODE = 'ShaderNodeTexImage'
VALUE_NODE = 'ShaderNodeValue'
ENVIRONMENT_IMAGE_NODE = 'ShaderNodeTexEnvironment'
COORD_NODE = 'ShaderNodeTexCoord'

# Nodes Outputs
OUTPUT_NODE = 'ShaderNodeOutputMaterial'

# Nodes Vector
MAPPING_NODE = 'ShaderNodeMapping'
NORMAL_MAP_NODE = 'ShaderNodeNormalMap'

# Nodes Convert
SHADER_NODE_MATH = 'ShaderNodeMath'
RGB_TO_BW_NODE = 'ShaderNodeRGBToBW'
SHADER_NODE_SEPARATE_COLOR = 'ShaderNodeSeparateColor'
SHADER_NODE_COMBINE_COLOR = 'ShaderNodeCombineColor'

# Node Groups
NODE_GROUP = 'ShaderNodeGroup'
NODE_GROUP_INPUT = 'NodeGroupInput'
NODE_GROUP_OUTPUT = 'NodeGroupOutput'
SHADER_NODE_TREE = 'ShaderNodeTree'

# Node Custom Groups
INVERT_CHANNEL_NODE = 'Invert Channel'
MIX_NORMAL_NODE = 'Normal Mix'
NORMAL_MASK_NODE = 'Normal Mask'
FH_SHADER_NODE = 'For Honor Shader'

# Sockets
NODE_SOCKET_COLOR = 'NodeSocketColor'
NODE_SOCKET_FLOAT = 'NodeSocketFloat'
NODE_SOCKET_FLOAT_FACTOR = 'NodeSocketFloatFactor'
NODE_SOCKET_SHADER = 'NodeSocketShader'
NODE_SOCKET_VECTOR = 'NodeSocketVector'

# Colors
DIFFUSE_COLOR = (0.9, 0.9, 0.9, 1)
SPECULAR_COLOR = (0.707, 0.707, 0.707, 1)
LIGHTMAP_COLOR = (1, 1, 1, 1)
NORMAL_COLOR = (0.5, 0.5, 1, 1)
GREY_COLOR = (0.5, 0.5, 0.5, 1)


if bpy.app.version < (4, 0):
    def new_input_socket(node_tree, socket_type, socket_name):
        return node_tree.inputs.new(socket_type, socket_name)

    def new_output_socket(node_tree, socket_type, socket_name):
        return node_tree.outputs.new(socket_type, socket_name)

    def clear_sockets(node_tree):
        node_tree.inputs.clear()
        node_tree.outputs.clear()
else:
    # Blender 4.0 moved NodeTree inputs and outputs into a combined interface.
    # Additionally, only base socket types can be created directly. Subtypes must be set explicitly after socket
    # creation.
    NODE_SOCKET_SUBTYPES = {
        # There are a lot more, but this is the only one in use currently.
        NODE_SOCKET_FLOAT_FACTOR: ('FACTOR', NODE_SOCKET_FLOAT),
    }

    def _new_socket(node_tree, socket_type, socket_name, in_out):
        subtype, base_type = NODE_SOCKET_SUBTYPES.get(socket_type, (None, None))
        new_socket = node_tree.interface.new_socket(socket_name, in_out=in_out,
                                                    socket_type=base_type if base_type else socket_type)
        if subtype:
            new_socket.subtype = subtype
        return new_socket

    def new_input_socket(node_tree, socket_type, socket_name):
        return _new_socket(node_tree, socket_type, socket_name, 'INPUT')

    def new_output_socket(node_tree, socket_type, socket_name):
        return _new_socket(node_tree, socket_type, socket_name, 'OUTPUT')

    def clear_sockets(node_tree):
        node_tree.interface.clear()


def makeMaterialOutputNode(node_tree):
    node = node_tree.nodes.new(OUTPUT_NODE)
    node.location = 200, -8000
    return node



def makeImageNode(node_tree, location=(-400, 0), image=None, label=None, colorspace=None):
    node = node_tree.nodes.new(TEXTURE_IMAGE_NODE)
    node.location = location

    if label:
        node.label = label
        node.name = label

    if image:
        node.image = image

        # Set color space if provided
        if colorspace:
            try:
                node.image.colorspace_settings.name = colorspace
            except:
                print(f"Invalid colorspace: {colorspace}")

    return node

def makeValueNode(node_tree, location=(-400, 0)):
    node = node_tree.nodes.new(VALUE_NODE)
    node.location = location
    return node


def makeEnvironmentNode(node_tree):
    node = node_tree.nodes.new(ENVIRONMENT_IMAGE_NODE)
    node.location = -400, 0
    return node


def makeTransparencyNode(node_tree):
    node = node_tree.nodes.new(BSDF_TRANSPARENT_NODE)
    node.location = -400, -200
    return node


def makeShaderMixNode(node_tree):
    node = node_tree.nodes.new(SHADER_MIX_NODE)
    node.location = -400, -400
    return node


def randomColor():
    randomR = random.random()
    randomG = random.random()
    randomB = random.random()
    return (randomR, randomG, randomB)


def setNodeScale(node, value):
    # Change from 2.80 to 2.81
    if 'Scale' in node.inputs:
        node.inputs['Scale'].default_value = (value, value, value)
    else:
        node.scale = (value, value, value)

def create_group_nodes():
    node = fh_shader_group()
    return node

def getNodeGroup(node_tree, group):
    node = fh_shader_group()
    return node

# def getNodeGroup(node_tree, group):
#     node = node_tree.nodes.new(NODE_GROUP)
#     node.node_tree = bpy.data.node_groups[group]
#     return node


def makeImageFilepath(rootDir, textureFilename):
    return os.path.join(rootDir, textureFilename)

def loadImage(material, texname, search_dir):
    extensions = (".png",".dds")

    if not os.path.isdir(search_dir):
        print(f"[ImageLoader] Search directory does not exist: {search_dir}")
        return None
    
    # Fix name
    if len(texname) > 8:
        texname = texname[:-5] # Remove "Spec"

        # Check for both 'set01am' and 'set01aam'
        if texname.find("set0"):
            set_idx = texname.find("set0")
            target_name = texname
            target_name2 = texname[:set_idx+5] + 'a' + texname[set_idx+5:] # add extra 'a'
        else:
            target_name = texname
            target_name2 = texname
    else:
        target_name = '_MISSING_'
        target_name2 = '_MISSING_'
        
    # Find texture
    for filename in os.listdir(search_dir):
        name, ext = os.path.splitext(filename)

        # Skip wrong filetype
        if ext.lower() not in extensions:
            continue

        if name == target_name or name == target_name2:
            full_path = os.path.join(search_dir, filename)
            directory, file = os.path.split(full_path)
            
            # Use high-res if possible
            if os.path.exists(os.path.join(search_dir, name + "_CHRTM_0" + ext)):
                name = name + "_CHRTM_0"
                full_path = os.path.join(search_dir, name + ext)
            elif os.path.exists(os.path.join(search_dir, name + "_CHRTM_1" + ext)):
                name = name + "_CHRTM_1"
                full_path = os.path.join(search_dir, name + ext)

            # Avoid reloading if already in Blender
            existing = bpy.data.images.get(name)
            if existing:
                return existing

            # DDS
            if ext.lower() == ".dds":

                # Use PNG if possible
                if os.path.exists(os.path.join(search_dir, name + ".png")):
                    full_path = os.path.join(search_dir, name + ".png")
                    return bpy.data.images.load(full_path)

                # Load DDS
                before = set(bpy.data.images)
                import_dds(bpy.context, full_path)
                after = set(bpy.data.images)
                new_images = after - before

                if not new_images:
                    raise RuntimeError("DDS import did not create an image")

                return new_images.pop()

            # PNG
            else:
                return bpy.data.images.load(full_path)

    # No texture found, load default
    print(f"[ImageLoader] No texture found with name {target_name} in {search_dir}")
    addon_dir = os.path.dirname(os.path.realpath(__file__))
    return bpy.data.images.load(os.path.join(addon_dir, "resources", "_MISSING_.png"))


def newTextureSlot(materialData):
    textureSlot = materialData.texture_slots.add()
    textureSlot.texture_coords = "UV"
    # textureSlot.texture = imgTex
    textureSlot.use_map_alpha = True
    textureSlot.alpha_factor = 1.0
    return textureSlot


def makeMaterial(xpsSettings, rootDir, mesh_da, meshInfo, flags):
    # Create the material for Nodes
    meshFullName = meshInfo.name
    materialData = bpy.data.materials.new(meshFullName)
    mesh_da.materials.append(materialData)

    # Create
    makeNodesMaterial(xpsSettings, materialData, rootDir, mesh_da, meshInfo, flags)


def makeNodesMaterial(xpsSettings, materialData, rootDir, mesh_da, meshInfo, flags):
    textureFilepaths = meshInfo.textures
    materialData.use_nodes = True
    node_tree = materialData.node_tree
    node_tree.nodes.clear()

    meshFullName = materialData.name
    renderType = xps_material.makeRenderType(meshFullName)
    renderGroup = xps_material.RenderGroup(renderType)
    param1 = renderType.texRepeater1
    param2 = renderType.texRepeater2
    strengthFac = renderType.specularity

    useAlpha = renderGroup.rgAlpha

    # -----------------------------
    # OUTPUT NODE
    ouputNode = makeMaterialOutputNode(node_tree)

    # -----------------------------
    # LOAD / APPEND NODE GROUP
    shader_group = fh_shader_group()
    if shader_group is None:
        return

    # CREATE GROUP NODE INSTANCE
    xpsShadeNode = node_tree.nodes.new("ShaderNodeGroup")
    xpsShadeNode["For Honor Shader"] = True
    xpsShadeNode.node_tree = shader_group
    xpsShadeNode.location = Vector((0, 0))

    ouputNode.location = xpsShadeNode.location + Vector((200, 0))

    materialData.blend_method = 'HASHED'

    node_tree.links.new(xpsShadeNode.outputs['BSDF'], ouputNode.inputs['Surface'])

    create_inputs(materialData, xpsSettings)

def find_fh_shader_node(material):
    node_tree = material.node_tree
    for node in node_tree.nodes:
        if node.get("For Honor Shader"):
            return node
    return None


def fh_shader_group():
    # If already loaded in this file, reuse it
    if FH_SHADER_NODE in bpy.data.node_groups:
        return bpy.data.node_groups[FH_SHADER_NODE]

    # Path to the blend file inside your addon
    addon_dir = os.path.dirname(os.path.realpath(__file__))
    lib_path = os.path.join(addon_dir, "resources", "ForHonorShader3.blend")

    # Append the node group
    with bpy.data.libraries.load(lib_path, link=False) as (data_from, data_to):
        if FH_SHADER_NODE in data_from.node_groups:
            data_to.node_groups = [FH_SHADER_NODE]
        else:
            print(f"Node group '{FH_SHADER_NODE}' not found in library!")
            return None

    return bpy.data.node_groups.get(FH_SHADER_NODE)


def create_inputs(material, xpsSettings):
    fh_shader = find_fh_shader_node(material)
    
    parent = Path(xpsSettings.filename).parent
    matpath = None
    texpath = None

    # Find texture/material paths
    for item in parent.iterdir():
        if item.is_dir():
            if not matpath and item.name.endswith("materials"):
                matpath = item
            elif not texpath and item.name.endswith("_textures"):
                texpath = item
            if matpath and texpath:
                break

    # Find Material File
    matname = material.name[-16:]
    for item in os.listdir(matpath):
        if item.startswith(matname):
            fh_material = item
            break
    
    # Read Material File
    if fh_material:
        with open(os.path.join(matpath, fh_material), "r") as mat_txt:
            mat_data = mat_txt.readlines()
            ColorMask = mat_data[0].split(' ')[-1]
            DecalMask = mat_data[1].split(' ')[-1]
            ClothMask = mat_data[2].split(' ')[-1]
            DiffuseMap = mat_data[3].split(' ')[-1]
            NormalMap = mat_data[4].split(' ')[-1]
            SpecularMap = mat_data[5].split(' ')[-1]
    else:
        ColorMask = ''
        DecalMask = ''
        ClothMask = ''
        DiffuseMap = ''
        NormalMap = ''
        SpecularMap = ''
        print(f'Material not found! {matname}')

    input_diffuse = makeImageNode(material.node_tree, (-400, 0), loadImage(material, DiffuseMap, texpath), "Diffuse", "sRGB")
    input_specular = makeImageNode(material.node_tree, (-400, -250), loadImage(material, SpecularMap, texpath), "Specular", "Non-Color")
    input_normal = makeImageNode(material.node_tree, (-400, -500), loadImage(material, NormalMap, texpath), "Normal", "Non-Color")
    input_decal = makeImageNode(material.node_tree, (-400, -750), loadImage(material, DecalMask, texpath), "Decal Mask", "Non-Color")
    input_mask = makeImageNode(material.node_tree, (-400, -1000), loadImage(material, ColorMask, texpath), "Color Mask", "Non-Color")
    input_cloth = makeImageNode(material.node_tree, (-400, -1250), loadImage(material, "_TODO_", texpath), "Cloth Mask", "Non-Color")
    input_pattern = makeImageNode(material.node_tree, (-400, -1500), loadImage(material, "_TODO_", texpath), "Color Mask", "Non-Color")

    # Diffuse
    material.node_tree.links.new(input_diffuse.outputs[0], fh_shader.inputs[0])

    # Alpha
    material.node_tree.links.new(input_diffuse.outputs[1], fh_shader.inputs[1])

    # Specular
    material.node_tree.links.new(input_specular.outputs[0], fh_shader.inputs[2])

    # Normals
    material.node_tree.links.new(input_normal.outputs[0], fh_shader.inputs[3])

    # Decal Mask
    material.node_tree.links.new(input_decal.outputs[0], fh_shader.inputs[4])

    # Color Mask
    material.node_tree.links.new(input_mask.outputs[0], fh_shader.inputs[5])

    # Cloth Mask
    material.node_tree.links.new(input_cloth.outputs[0], fh_shader.inputs[6])

    # Pattern
    material.node_tree.links.new(input_pattern.outputs[0], fh_shader.inputs[14])

    # Pattern Alpha
    material.node_tree.links.new(input_pattern.outputs[1], fh_shader.inputs[15])