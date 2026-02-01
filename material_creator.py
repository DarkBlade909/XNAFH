import bpy
import os
import random
from mathutils import Vector
from . import xps_material
from . import xps_const
import importlib
import addon_utils

def get_dds_addon_module():
    try:
        # Attempt to import the DDS addon module
        return importlib.import_module("blender_dds_addon")
    except ImportError:
        return None

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

def loadImage(material, suffix, search_dir):
    # Is Blender DDS Addon enabled?
    if addon_utils.check("blender_dds_addon")[1]:
        extensions = (".png",".dds")
    else:
        extensions = ".png"
    
    if not os.path.isdir(search_dir):
        print(f"[ImageLoader] Search directory does not exist: {search_dir}")
        return None

    # Texture Name Guessing :(
    suffix2 = "default"
    if material.name.lower()[:-2].endswith("chest"):
        suffix2 = "torso_" + suffix.lower()
        suffix = "chest_" + suffix.lower()
    elif material.name.lower()[:-2].endswith("torso"):
        suffix2 = "chest_" + suffix.lower()
        suffix = "torso_" + suffix.lower()
    elif material.name.lower()[:-2].endswith("arms") | material.name.lower()[:-2].endswith("armrd") | material.name.lower()[:-2].endswith("armld") | material.name.lower()[:-2].endswith("armru") | material.name.lower()[:-2].endswith("armlu") | material.name.lower()[:-2].endswith("armsrd") | material.name.lower()[:-2].endswith("armsld") | material.name.lower()[:-2].endswith("armsru") | material.name.lower()[:-2].endswith("armslu") | material.name.lower()[:-2].endswith("armsu"):
        suffix = "arms_" + suffix.lower()
    elif material.name.lower()[:-2].endswith("helm"):
        suffix = "helm_" + suffix.lower()
    elif material.name.lower()[:-2].endswith("helmet"):
        suffix = "helmet_" + suffix.lower()
    elif material.name.lower()[:-2].endswith("face"):
        suffix = "helm_face_" + suffix.lower()
    elif material.name.lower()[:-2].endswith("head"):
        suffix2 = "helm_" + suffix.lower()
        suffix = "head_" + suffix.lower()
    elif material.name.lower()[:-2].endswith("hat"):
        suffix = "specific_" + suffix.lower()
    elif material.name.lower()[:-2].endswith("legs"):
        suffix = "legs_" + suffix.lower()
    elif material.name.lower()[:-2].endswith("shoulderr"):
        suffix = "shoulderr_" + suffix.lower()
    elif material.name.lower()[:-2].endswith("shoulderl"):
        suffix = "shoulderl_" + suffix.lower()
    elif material.name.lower()[:-2].endswith("map"):
        suffix = "specific_" + suffix.lower()
    elif material.name.lower()[:-2].endswith("belt"):
        suffix = "chest_" + suffix.lower()
    elif material.name.lower()[:-2].endswith("eyesteeth"):
        suffix = "eye_" + suffix.lower()[:-8]
    else:
        suffix = "missing"
        suffix2 = "missing"

    for filename in os.listdir(search_dir):
        name, ext = os.path.splitext(filename)

        if ext.lower() not in extensions:
            continue

        if suffix == "missing":
            continue

        if name.lower().endswith(suffix.lower()) | name.lower().endswith(suffix2.lower()):
            full_path = os.path.join(search_dir, filename)
            directory, file = os.path.split(full_path)

            # Avoid reloading if already in Blender
            pngexist = bpy.data.images.get(name + ".png")
            ddsexist = bpy.data.images.get(name + ".dds")
            if pngexist:
                print(f"[ImageLoader] Using already loaded image: {name}.png")
                return pngexist
            elif ddsexist:
                print(f"[ImageLoader] Using already loaded image: {name}.dds")
                return ddsexist
            
            print(f"[ImageLoader] Loading image: {full_path}")

            # DDS
            if ext.lower() == ".dds":

                # Use PNG if possible
                if os.path.exists(os.path.join(search_dir, name + ".png")):
                    full_path = os.path.join(search_dir, name + ".png")
                    return bpy.data.images.load(full_path)

                # Load DDS
                before = set(bpy.data.images)
                bpy.ops.dds.import_dds('EXEC_DEFAULT', directory=directory + os.sep, files=[{"name": file}])
                after = set(bpy.data.images)
                new_images = after - before

                if not new_images:
                    raise RuntimeError("DDS import did not create an image")

                return new_images.pop()

            # PNG
            else:
                return bpy.data.images.load(full_path)

    print(f"[ImageLoader] No texture found with suffix '{suffix}' or '{suffix2}' in {search_dir}")
    return None


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

    if useAlpha:
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
    lib_path = os.path.join(addon_dir, "resources", "ForHonorShader.blend")

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
    texpath = os.path.splitext(xpsSettings.filename)[0][:-3] + "textures"

    input_diffuse = makeImageNode(material.node_tree, (-400, 0), loadImage(material, "DiffuseMap_CHRTM_1", texpath), "Diffuse", "sRGB")
    input_specular = makeImageNode(material.node_tree, (-400, -250), loadImage(material, "SpecularMap_CHRTM_1", texpath), "Specular", "Non-Color")
    input_normal = makeImageNode(material.node_tree, (-400, -500), loadImage(material, "NormalMap_CHRTM_1", texpath), "Normal", "Non-Color")
    input_decal = makeImageNode(material.node_tree, (-400, -750), loadImage(material, "DecalMaskMap_CHRTM_1", texpath), "Decal Mask", "Non-Color")
    input_mask = makeImageNode(material.node_tree, (-400, -1000), loadImage(material, "ColorMaskMap_CHRTM_1", texpath), "Color Mask", "Non-Color")

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

    # Material Mask
    material.node_tree.links.new(input_mask.outputs[0], fh_shader.inputs[5])