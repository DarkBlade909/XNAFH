import bpy
import copy
import operator
import os
import re
from contextlib import ExitStack

from . import import_xnalara_pose
from . import read_ascii_xps
from . import read_bin_xps
from . import xps_types
from . import material_creator

import math
import mathutils
from math import radians
from mathutils import Vector
from mathutils import Matrix

rootDir = ''
blenderBoneNames = []
MIN_BONE_LENGHT = 0.005
xpsData = None
xpsSettings = None

anchor_bones = [
    "RightHand_Weapon_Ref",
    "LeftHand_Weapon_Ref",
    "Ornament_Anchor_A",
    "Ornament_Anchor_B",
    "Ornament_Anchor_C",
    "Ornament_Anchor_Rank"
]
def newBoneName():
    global blenderBoneNames
    blenderBoneNames = []

def addBoneName(newName):
    global blenderBoneNames
    blenderBoneNames.append(newName)

def getBoneName(originalIndex):
    if originalIndex < len(blenderBoneNames):
        return blenderBoneNames[originalIndex]
    else:
        return None

def coordTransform(coords):
    x, y, z = coords
    z = -z
    return (x, z, y)

def faceTransform(face):
    return [face[0], face[2], face[1]]

def faceTransformList(faces):
    return list(map(faceTransform, faces))

def uvTransform(uv):
    u = uv[0] + xpsSettings.uvDisplX
    v = 1 + xpsSettings.uvDisplY - uv[1]
    return [u, v]

def rangeFloatToByte(float):
    return int(float * 255) % 256

def rangeByteToFloat(byte):
    return byte / 255

def uvTransformLayers(uvLayers):
    return list(map(uvTransform, uvLayers))

def getInputFilename(xpsSettingsAux):
    global xpsSettings, xpsData
    xpsSettings = xpsSettingsAux
    xpsData = None

    blenderImportSetup()
    status = xpsImport()
    blenderImportFinalize()
    return status

def blenderImportSetup():
    objectMode()
    bpy.ops.object.select_all(action='DESELECT')

def blenderImportFinalize():
    objectMode()

def objectMode():
    current_mode = bpy.context.mode
    if bpy.context.view_layer.objects.active and current_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

def loadXpsFile(filename):
    dirpath, file = os.path.split(filename)
    basename, ext = os.path.splitext(file)
    if ext.lower() in ('.mesh', '.xps'):
        xpsData = read_bin_xps.readXpsModel(filename)
    elif ext.lower() in ('.ascii'):
        xpsData = read_ascii_xps.readXpsModel(filename)
    else:
        xpsData = None
    return xpsData

def makeMesh(meshFullName):
    mesh_da = bpy.data.meshes.new(meshFullName)
    mesh_ob = bpy.data.objects.new(mesh_da.name, mesh_da)
    print('Create mesh: {}'.format(meshFullName))
    print('New mesh = {}'.format(mesh_da.name))
    return mesh_ob

def linkToCollection(collection, obj):
    collection.objects.link(obj)

def xpsImport():
    global rootDir, xpsData

    print("------------------------------------------------------------")
    print("---------------Executing XPS Python Importer----------------")
    print("------------------------------------------------------------")
    print("Import file: ", xpsSettings.filename)

    rootDir, file = os.path.split(xpsSettings.filename)
    print('Root directory: {}'.format(rootDir))

    xpsData = loadXpsFile(xpsSettings.filename)
    if not xpsData:
        return '{NONE}'

    fname, fext = os.path.splitext(file)
    new_collection = bpy.data.collections.new(fname)
    view_layer = bpy.context.view_layer
    active_collection = view_layer.active_layer_collection.collection
    active_collection.children.link(new_collection)

    armature_ob = createArmature()
    if armature_ob:
        linkToCollection(new_collection, armature_ob)
        importBones(armature_ob)

    meshes_obs = importMeshesList(armature_ob)
    for obj in meshes_obs:
        linkToCollection(new_collection, obj)
        markSelected(obj)
        if armature_ob:
            placeOrnament(armature_ob, obj)
            placeWeapon(armature_ob, obj)

    if armature_ob:
        hideUnusedBones([armature_ob])

    if xpsSettings.importDefaultPose and armature_ob and xpsData.header and xpsData.header.pose:
        import_xnalara_pose.setXpsPose(armature_ob, xpsData.header.pose)
    

    return '{FINISHED}'

def setMinimumLenght(bone):
    default_length = MIN_BONE_LENGHT
    if bone.length == 0:
        bone.tail = bone.head - Vector((0, .001, 0))
    if bone.length < default_length:
        bone.length = default_length

def hideBonesByName(armature_objs):
    for armature in armature_objs:
        for bone in armature.data.bones:
            if bone.name.lower().startswith('unused'):
                hideBone(bone)

def hideBonesByVertexGroup(armature_objs):
    for armature in armature_objs:
        objs = [obj for obj in armature.children
                if obj.type == 'MESH' and obj.modifiers and any(
                    modif for modif in obj.modifiers if modif and modif.type == 'ARMATURE' and modif.object == armature)]
        vertexgroups = set(vg.name for obj in objs if obj.type == 'MESH' for vg in obj.vertex_groups)
        bones = armature.data.bones
        rootBones = [bone for bone in bones if not bone.parent]

        for bone in rootBones:
            recurBones(bone, vertexgroups, '')

def recurBones(bone, vertexgroups, name):
    visibleChild = False
    for childBone in bone.children:
        aux = recurBones(childBone, vertexgroups, '{} '.format(name))
        visibleChild = visibleChild or aux

    visibleChain = bone.name in vertexgroups or visibleChild
    if not visibleChain:
        hideBone(bone)
    return visibleChain

def _ensure_visibility_bones_collection(armature):
    # Blender 4.x+
    if hasattr(armature, "collections"):
        col = armature.collections.get("Visible Bones")
        if col is None:
            col = armature.collections.new("Visible Bones")
        return col

    # Blender 3.6
    return None

def hideBone(bone):
    col = _ensure_visibility_bones_collection(bone.id_data)
    if col:
        col.unassign(bone)
    else:
        pass

def showBone(bone):
    arm_data = bone.id_data

    # Blender 4.x+
    if hasattr(arm_data, "collections"):
        col = _ensure_visibility_bones_collection(arm_data)
        col.assign(bone)

    # Blender 3.6
    else:
        layer_index = 0
        bone.layers[layer_index] = True

def visibleBone(bone):
    col = _ensure_visibility_bones_collection(bone.id_data)
    if col:
        return bone.name in col.bones
    else:
        pass

def showAllBones(armature_objs):
    for armature in armature_objs:
        for bone in armature.data.bones:
            showBone(bone)

def hideBoneChain(bone):
    hideBone(bone)
    parentBone = bone.parent
    if parentBone:
        hideBoneChain(parentBone)

def showBoneChain(bone):
    showBone(bone)
    parentBone = bone.parent
    if parentBone:
        showBoneChain(parentBone)

def hideUnusedBones(armature_objs):
    hideBonesByVertexGroup(armature_objs)
    hideBonesByName(armature_objs)

def boneDictRename(filepath, armatureObj):
    boneDictDataRename, boneDictDataRestore = read_ascii_xps.readBoneDict(filepath)
    renameBonesUsingDict(armatureObj, boneDictDataRename)

def boneDictRestore(filepath, armatureObj):
    boneDictDataRename, boneDictDataRestore = read_ascii_xps.readBoneDict(filepath)
    renameBonesUsingDict(armatureObj, boneDictDataRestore)

def renameBonesUsingDict(armatureObj, boneDict):
    getbone = armatureObj.data.bones.get
    for key, value in boneDict.items():
        boneRenamed = getbone(import_xnalara_pose.renameBoneToBlender(key))
        if boneRenamed:
            boneRenamed.name = value
        else:
            boneOriginal = getbone(key)
            if boneOriginal:
                boneOriginal.name = value

def createArmature():
    bones = xpsData.bones
    armature_ob = None
    if bones:
        boneCount = len(bones)
        print('Import armature', str(boneCount), 'bones')

        armature_da = bpy.data.armatures.new("Armature")
        if xpsSettings.prettyBones:
            armature_da.display_type = 'OCTAHEDRAL'
        else:
            armature_da.display_type = 'STICK'
        armature_ob = bpy.data.objects.new("Armature", armature_da)
        armature_ob.show_in_front = True

        return armature_ob

def importBones(armature_ob):
    bones = xpsData.bones

    bpy.context.view_layer.objects.active = armature_ob
    try:
        bpy.ops.object.mode_set(mode='EDIT')

        arm_data = armature_ob.data
        editBones = arm_data.edit_bones

        newBoneName()

        for bone in bones:
            quat = mathutils.Quaternion([float(bone.quat[3]), float(bone.quat[0]), float(bone.quat[1]), float(bone.quat[2])]).to_matrix().to_4x4()
            locate = [float(bone.co[0]), float(bone.co[1]), float(bone.co[2])]

            editBone = editBones.new(bone.name)

            editBone.head, editBone.tail = (0,0,0), (0, 0.1, 0)
            editBone.matrix = mathutils.Matrix.Translation(locate) @ quat

            if xpsSettings.prettyBones and bone.name not in anchor_bones:
                # # local axes of the bone
                # x, y, z = editBone.matrix.to_3x3().col
                # # rotation matrix 30 degrees around local x axis thru head
                # R = (Matrix.Translation(editBone.head) @
                #     Matrix.Rotation(radians(-90), 4, z) @
                #     Matrix.Translation(-editBone.head)
                #     )
                # #bone.matrix = R @ bone.matrix
                # editBone.transform(R) 

                
                old_head = editBone.head.copy()
                R = Matrix.Rotation(radians(-90), 4, editBone.z_axis.normalized())   
                editBone.transform(R, roll=True) 
                offset_vec = -(editBone.head - old_head)
                editBone.head += offset_vec
                editBone.tail += offset_vec
            

            addBoneName(editBone.name)

        # Blender 4.x+
        if hasattr(arm_data, "collections"):

            bones_collection = arm_data.collections.new("Bones")
            bones_collection.is_visible = False

            visible_bones_collection = arm_data.collections.new("Visible Bones")

            for editBone in editBones:
                bones_collection.assign(editBone)
                visible_bones_collection.assign(editBone)

        # Blender 3.6
        else:
            bones_layer = 0
            visible_layer = 1

            for editBone in editBones:
                editBone.layers = [False] * 32
                editBone.layers[bones_layer] = True
                editBone.layers[visible_layer] = True

        for bone in bones:
            if bone.parentId >= 0:
                editBone = editBones[bone.id]
                editBone.parent = editBones[bone.parentId]

    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

def markSelected(ob):
    ob.select_set(state=True)

def makeUvs(mesh_da, faces, uvData, vertColors):
    for i in range(len(uvData[0])):
        mesh_da.uv_layers.new(name="UV{}".format(str(i + 1)))
    if xpsSettings.vColors:
        mesh_da.vertex_colors.new()

    for faceId, face in enumerate(faces):
        for vertId, faceVert in enumerate(face):
            loopdId = (faceId * 3) + vertId
            if xpsSettings.vColors:
                mesh_da.vertex_colors[0].data[loopdId].color = vertColors[faceVert]
            for layerIdx, uvLayer in enumerate(mesh_da.uv_layers):
                uvCoor = uvData[faceVert][layerIdx]
                uvLayer.data[loopdId].uv = Vector(uvCoor)

def importMeshesList(armature_ob):
    newMeshes = xpsData.meshes
    importedMeshes = [importMesh(armature_ob, meshInfo) for meshInfo in newMeshes]
    return [mesh for mesh in importedMeshes if mesh]

def generateVertexKey(vertex):
    if xpsSettings.joinMeshRips:
        key = str(vertex.co) + str(vertex.norm)
    else:
        key = str(vertex.id) + str(vertex.co) + str(vertex.norm)
    return key

def getVertexId(vertex, mapVertexKeys, mergedVertList):
    vertexKey = generateVertexKey(vertex)
    vertexID = mapVertexKeys.get(vertexKey)
    if vertexID is None:
        vertexID = len(mergedVertList)
        mapVertexKeys[vertexKey] = vertexID
        newVert = copy.copy(vertex)
        newVert.id = vertexID
        mergedVertList.append(newVert)
    else:
        mergedVertList[vertexID].merged = True
    return vertexID

def makeVertexDict(vertexDict, mergedVertList, uvLayers, vertColor, vertices):
    mapVertexKeys = {}
    uvLayerAppend = uvLayers.append
    vertColorAppend = vertColor.append
    vertexDictAppend = vertexDict.append

    for vertex in vertices:
        vColor = vertex.vColor
        uvLayerAppend([uvTransform(uv_item) for uv_item in vertex.uv]) 
        vertColorAppend(list(map(rangeByteToFloat, vColor)))
        vertexID = getVertexId(vertex, mapVertexKeys, mergedVertList)
        vertexDictAppend(vertexID)

def importMesh(armature_ob, meshInfo):
    useSeams = xpsSettings.markSeams
    meshFullName = meshInfo.name
    print()
    print('---*** Import mesh {} ***---'.format(meshFullName))

    uvLayerCount = meshInfo.uvCount
    print('UV layers: {}'.format(str(uvLayerCount)))

    textureCount = len(meshInfo.textures)
    print('Texture count: {}'.format(str(textureCount)))

    mesh_ob = None
    vertCount = len(meshInfo.vertices)
    if vertCount >= 3:
        vertexDict = []
        mergedVertList = []
        uvLayers = []
        vertColors = []
        makeVertexDict(vertexDict, mergedVertList, uvLayers, vertColors, meshInfo.vertices)

        vertexOrig = [[] for _ in range(len(mergedVertList))]
        for vertId, vert in enumerate(vertexDict):
            vertexOrig[vert].append(vertId)

        mergedVertices = {}
        seamEdgesDict = {}
        facesData = []
        for face in meshInfo.faces:
            v1Old, v2Old, v3Old = face
            v1New = vertexDict[v1Old]
            v2New = vertexDict[v2Old]
            v3New = vertexDict[v3Old]
            oldFace = (v1Old, v2Old, v3Old)
            facesData.append((v1New, v2New, v3New))

            if useSeams and (mergedVertList[v1New].merged or mergedVertList[v2New].merged or mergedVertList[v3New].merged):
                findMergedEdges(seamEdgesDict, vertexDict, mergedVertList, mergedVertices, oldFace)

        mergeByNormal = True
        if mergeByNormal:
            vertices = mergedVertList
            facesList = facesData
        else:
            vertices = meshInfo.vertices
            facesList = meshInfo.faces

        mesh_ob = makeMesh(meshFullName)
        mesh_da = mesh_ob.data

        coords = []
        normals = []
        for vertex in vertices:
            unitnormal = Vector(vertex.norm).normalized()
            coords.append(coordTransform(vertex.co))
            normals.append(coordTransform(unitnormal))

        faces = list(faceTransformList(facesList))
        mesh_da.from_pydata(coords, [], faces)
        mesh_da.polygons.foreach_set("use_smooth", [True] * len(mesh_da.polygons))

        if xpsSettings.markSeams:
            markSeams(mesh_da, seamEdgesDict)

        origFaces = faceTransformList(meshInfo.faces)
        makeUvs(mesh_da, origFaces, uvLayers, vertColors)

        if xpsData.header:
            flags = xpsData.header.flags
        else:
            flags = read_bin_xps.flagsDefault()

        material_creator.makeMaterial(xpsSettings, rootDir, mesh_da, meshInfo, flags)

        if armature_ob:
            setArmatureModifier(armature_ob, mesh_ob)
            setParent(armature_ob, mesh_ob)

        makeVertexGroups(mesh_ob, vertices)

        if armature_ob:
            makeBoneGroups(armature_ob, mesh_ob)

        verts_nor = xpsSettings.importNormals
        use_edges = True

        if verts_nor:
            meshCorrected = mesh_da.validate(clean_customdata=False)
            mesh_da.update(calc_edges=use_edges)
            mesh_da.normals_split_custom_set_from_vertices(normals)
        else:
            meshCorrected = mesh_da.validate()

        print("Geometry corrected:", meshCorrected)

    return mesh_ob

def markSeams(mesh_da, seamEdgesDict):
    edge_keys = {val: index for index, val in enumerate(mesh_da.edge_keys)}
    for vert1, vert_list in seamEdgesDict.items():
        for vert2 in vert_list:
            edgeIdx = edge_keys.get((vert1, vert2)) if vert1 < vert2 else edge_keys.get((vert2, vert1))
            if edgeIdx is not None:
                mesh_da.edges[edgeIdx].use_seam = True

def findMergedEdges(seamEdgesDict, vertexDict, mergedVertList, mergedVertices, oldFace):
    for mergedVert in oldFace:
        findMergedVert(seamEdgesDict, vertexDict, mergedVertList, mergedVertices, oldFace, mergedVert)

def findMergedVert(seamEdgesDict, vertexDict, mergedVertList, mergedVertices, oldFace, mergedVert):
    v1Old, v2Old, v3Old = oldFace
    vertX = vertexDict[mergedVert]
    if mergedVertList[vertX].merged:
        if mergedVertices.get(vertX) is None:
            mergedVertices[vertX] = []

        for facesList in mergedVertices[vertX]:
            i = 0
            matchV1 = False
            while not matchV1 and i < 3:
                if vertX == vertexDict[facesList[i]] and mergedVert != facesList[i]:
                    if mergedVert != v1Old:
                        checkEdgePairForSeam(i, seamEdgesDict, vertexDict, vertX, v1Old, facesList)
                    if mergedVert != v2Old:
                        checkEdgePairForSeam(i, seamEdgesDict, vertexDict, vertX, v2Old, facesList)
                    if mergedVert != v3Old:
                        checkEdgePairForSeam(i, seamEdgesDict, vertexDict, vertX, v3Old, facesList)
                    matchV1 = True
                i += 1

        mergedVertices[vertX].append((v1Old, v2Old, v3Old))

def checkEdgePairForSeam(i, seamEdgesDict, vertexDict, mergedVert, vert, facesList):
    if i != 0:
        makeSeamEdgeDict(0, seamEdgesDict, vertexDict, mergedVert, vert, facesList)
    if i != 1:
        makeSeamEdgeDict(1, seamEdgesDict, vertexDict, mergedVert, vert, facesList)
    if i != 2:
        makeSeamEdgeDict(2, seamEdgesDict, vertexDict, mergedVert, vert, facesList)

def makeSeamEdgeDict(i, seamEdgesDict, vertexDict, mergedVert, vert, facesList):
    if vertexDict[vert] == vertexDict[facesList[i]]:
        if seamEdgesDict.get(mergedVert) is None:
            seamEdgesDict[mergedVert] = []
        seamEdgesDict[mergedVert].append(vertexDict[vert])

def setArmatureModifier(armature_ob, mesh_ob):
    mod = mesh_ob.modifiers.new(type="ARMATURE", name="Armature")
    mod.use_vertex_groups = True
    mod.object = armature_ob

def setParent(armature_ob, mesh_ob):
    mesh_ob.parent = armature_ob

def makeVertexGroups(mesh_ob, vertices):
    armatures = mesh_ob.find_armature()
    for vertex in vertices:
        assignVertexGroup(vertex, armatures, mesh_ob)

def assignVertexGroup(vert, armature, mesh_ob):
    for vertBoneWeight in vert.boneWeights:
        boneIdx = vertBoneWeight.id
        vertexWeight = vertBoneWeight.weight
        if vertexWeight != 0:
            boneName = getBoneName(boneIdx)
            if boneName:
                vertGroup = mesh_ob.vertex_groups.get(boneName)
                if not vertGroup:
                    vertGroup = mesh_ob.vertex_groups.new(name=boneName)
                vertGroup.add([vert.id], vertexWeight, 'REPLACE')

def makeBoneGroups(armature_ob, mesh_ob):
    color1 = material_creator.randomColor()
    color2 = material_creator.randomColor()
    color3 = material_creator.randomColor()

    bone_pose_surface_color = color1
    bone_pose_color = color2
    bone_pose_active_color = color3

    arm_data = armature_ob.data
    poseBones = armature_ob.pose.bones
    vertexGroups = mesh_ob.vertex_groups.keys()

    # Blender 4.x+
    if hasattr(arm_data, "collections"):
        bone_collection = arm_data.collections.new(name=mesh_ob.name)
        bone_collection.is_visible = False

        for boneName in vertexGroups:
            if boneName not in poseBones:
                continue

            pose_bone = poseBones[boneName]
            bone_collection.assign(pose_bone)

            color = pose_bone.color
            color.palette = 'CUSTOM'
            custom_colors = color.custom
            custom_colors.normal = bone_pose_surface_color
            custom_colors.select = bone_pose_color
            custom_colors.active = bone_pose_active_color

    # Blender 3.6
    else:
        layer_index = 0

        bone_group = armature_ob.pose.bone_groups.new(name=mesh_ob.name)
        bone_group.color_set = 'CUSTOM'
        bone_group.colors.normal = bone_pose_surface_color
        bone_group.colors.select = bone_pose_color
        bone_group.colors.active = bone_pose_active_color

        for boneName in vertexGroups:
            if boneName not in poseBones:
                continue

            pose_bone = poseBones[boneName]

            pose_bone.bone.layers[layer_index] = True

            pose_bone.bone_group = bone_group

def placeOrnament(armature_ob, obj):
    slots = ['A','B','C','Rank']
    constraint = None
    if obj:
        match = obj.name.find("_Ornament_")
        if match > 0:
            print(f'Placing ornament: {obj.name}')

            # Get Slot
            if obj.name[-4:].lower() == "rank": # Rank slot
                slot = "Rank"
            else: # Letter slot
                slot = obj.name[-1].upper()

            if slot not in slots:
                print(f"Couldn't find ornament slot {slot}, defaulting to A")
                slot = 'A'

            # Find ornament bone
            arm_data = armature_ob.data
            for bone in arm_data.bones:
                if bone.name == (f"Ornament_Anchor_{slot}"):
                    print(f"Attaching to bone {bone.name}")
                    constraint = obj.constraints.new(type='COPY_TRANSFORMS')
                    constraint.target = armature_ob
                    constraint.subtarget = bone.name
                    return None

            # Ornament bone not found
            print(f"Couldn't find anchor point: Ornament_Anchor_{slot}")
            return None

        # Ornament object not found
        else:
            return None

def placeWeapon(armature_ob, obj):
    slot = None
    anchor_bone = None
    constraint = None
    if obj:
        match = obj.name.find("_Weapon")
        if match > 0:
            print(f'Placing weapon: {obj.name}')

            # Get Slot
            match_hand = obj.name.find("_RHand_")
            if match_hand > 0:
                anchor_bone = "RightHand_Weapon_Ref"
            else:
                match_hand = obj.name.find("_LHand_")
                if match_hand > 0:
                    anchor_bone = "LeftHand_Weapon_Ref"
                else:
                    match_hand = obj.name.find("_SHand_")
                    if match_hand > 0:
                        anchor_bone = "LeftHand_Weapon_Ref"

            # Find anchor bone
            arm_data = armature_ob.data
            for bone in arm_data.bones:
                if bone.name == anchor_bone:
                    print(f"Attaching to bone {bone.name}")
                    constraint = obj.constraints.new(type='COPY_TRANSFORMS')
                    constraint.target = armature_ob
                    constraint.subtarget = bone.name
                    return None

            # Anchor bone not found
            print(f"Couldn't find anchor point: {anchor_bone}")
            return None

        # Weapon object not found
        else:
            return None

        