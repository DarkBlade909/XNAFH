import io
import ntpath

from . import ascii_ops

from mathutils import Vector, Euler

class SmdData:

    def __init__(self, header='', bones=[], frames=[]):
        self.header = header
        self.bones = bones
        self.frames = frames

class SmdBone:

    def __init__(self, id, name, parentId):
        self.id = id
        self.name = name
        self.parentId = parentId

class SmdFrame:

    def __init__(self, id, x, y, z, rot_x, rot_y, rot_z, pos, matrix):
        self.id = id
        self.pos = pos
        self.matrix = matrix
        self.x = x
        self.y = y
        self.z = z
        self.rot_x = rot_x
        self.rot_y = rot_y
        self.rot_z = rot_z


def readSMDHeader(file):
    while True:
        line = ascii_ops.readString(file)
        if line:
            if line.strip() == "nodes":
                return
        else:
            print("Couldn't find end of header")
            return

def readBones(file):
    bones = []
    try:
        while True:
            boneData = ascii_ops.readString(file).split(" ")
            if boneData[0] == "end":
                print("end of bones")
                break
            boneId = int(boneData[0])
            boneName = str(boneData[1][1:-1])
            if boneName is None:
                boneName = f"Bone_{boneId}"
            parentId = int(boneData[2])
            if parentId is None:
                parentId = -1
            # transform = readTransform(file)
            # coords = transform[0]
            # quat = transform[1]

            smdBone = SmdBone(boneId, boneName, parentId)
            bones.append(smdBone)
    except Exception as e:
        print(f"Error reading bones: {e}")
    return bones

def readFrames(file):
    frames = []
    frametime = 0
    while True:
        animData = ascii_ops.readString(file).strip().split()
        if animData[0] == "skeleton":
            print("Start of frames")
        elif animData[0] == "time":
            # frame
            if int(animData[1]) == frametime:
                print(f"same frame {animData[1]}")
            else:
                print(f"new frame {animData[1]}")
                return frames
        elif animData[0] == "end":
            return frames
        else:
            animBoneId = int(animData[0])
            x, y, z = float(animData[1]), float(animData[2]), float(animData[3])
            rot_x, rot_y, rot_z = float(animData[4]), float(animData[5]), float(animData[6])

            pos = Vector([float(animData[1]), float(animData[2]), float(animData[3])])
            matrix = Euler([float(animData[4]), float(animData[5]), float(animData[6])])

            animFrame = SmdFrame(animBoneId, x, y, z, rot_x, rot_y, rot_z, pos, matrix)
            frames.append(animFrame)
    print("Finished reading anims")
    return frames

def readIoStream(filename):
    try:
        with open(filename, "r", encoding='utf-8') as a_file:
            content = a_file.read()
        return io.StringIO(content)
    except UnicodeDecodeError:
        # Try with different encoding if default fails
        try:
            with open(filename, "r", encoding='utf-8') as a_file:
                content = a_file.read()
            return io.StringIO(content)
        except Exception as e:
            print(f"Error reading file {filename}: {e}")
            return io.StringIO("")
    except Exception as e:
        print(f"Error opening file {filename}: {e}")
        return io.StringIO("")


def readSMDanim(filename):
    try:
        ioStream = readIoStream(filename)
        if not ioStream:
            return SmdData(bones=[], meshes=[])
            
        print('Reading Header')
        smdHeader = readSMDHeader(ioStream)
        print('Reading Bones')
        bones = readBones(ioStream)
        print('Reading Frames')
        frames = readFrames(ioStream)
        smdAnimData = SmdData(bones=bones, frames=frames)
        return smdAnimData
    except Exception as e:
        print(f"Error reading SMD anim {filename}: {e}")
        return SmdData(bones=[], frames=[])