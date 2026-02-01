import bpy


class _FHPanels():
    """All XPS panel inherit from this."""

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'XPS'
    bl_context = 'objectmode'


class FHToolsObjectPanel(_FHPanels, bpy.types.Panel):
    bl_idname = 'XPS_PT_FH_tools_object'
    bl_label = 'FH Tools'

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        col.label(text='Import:')
        # c = col.column()
        r = col.row(align=True)
        r1c1 = r.column(align=True)
        r1c1.operator("xps_tools.import_model", text='Model', icon='NONE')
        r1c2 = r.column(align=True)
        r1c2.operator('xps_tools.import_pose', text='Pose')


class FHToolsBonesPanel(_FHPanels, bpy.types.Panel):
    bl_idname = 'XPS_PT_FH_tools_bones'
    bl_label = 'FH Bones'

    @classmethod
    def poll(cls, context):
        return bool(
            next(
                (obj for obj in context.selected_objects if obj.type == 'ARMATURE'),
                None))

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        # col.separator()
        col = layout.column()

        col.label(text='Hide Bones:')
        c = col.column(align=True)
        r = c.row(align=True)
        r.operator('xps_tools.bones_hide_by_name', text='Unused')
        r.operator('xps_tools.bones_hide_by_vertex_group', text='Vertex Group')
        r = c.row(align=True)
        r.operator('xps_tools.bones_show_all', text='Show All')

        # col.separator()
        col = layout.column()

        col.label(text='BoneDict:')
        c = col.column(align=True)
        r = c.row(align=True)
        r.operator('xps_tools.bones_dictionary_generate', text='Generate BoneDict')
        r = c.row(align=True)
        r.operator('xps_tools.bones_dictionary_rename', text='Rename Bones')
        r = c.row(align=True)
        r.operator('xps_tools.bones_dictionary_restore_name', text='Restore Names')

        # col.separator()
        col = layout.column()

        col.label(text='Rename Bones:')
        c = col.column(align=True)
        r = c.row(align=True)
        r.operator('xps_tools.bones_rename_to_blender', text='XPS to Blender')
        r = c.row(align=True)
        r.operator('xps_tools.bones_rename_to_xps', text='Blender To XPS')

        col = layout.column()

        col.label(text='Connect Bones:')
        c = col.column(align=True)
        r = c.row(align=True)
        r.operator(
            'xps_tools.bones_connect',
            text='Connect All').connectBones = True
        r = c.row(align=True)
        r.operator(
            'xps_tools.bones_connect',
            text='Disconnect All').connectBones = False
        col.label(text='New Rest Pose:')
        c = col.column(align=True)
        r = c.row(align=True)
        r.operator(
            'xps_tools.new_rest_pose',
            text='New Rest Pose')


class FHToolsAnimPanel(_FHPanels, bpy.types.Panel):
    bl_idname = 'XPS_PT_FH_tools_anim'
    bl_label = 'FH Anim'

    @classmethod
    def poll(cls, context):
        return bool(
            next(
                (obj for obj in context.selected_objects if obj.type == 'ARMATURE'),
                None))

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        # col.separator()
        col = layout.column()

        col.label(text='Import:')
        c = col.column(align=True)
        r = c.row(align=True)
        r.operator(
            'xps_tools.import_poses_to_keyframes',
            text='Poses to Keyframes')
def register():
    bpy.utils.register_class(FHToolsObjectPanel)
    bpy.utils.register_class(FHToolsBonesPanel)
    bpy.utils.register_class(FHToolsAnimPanel)

def unregister():
    bpy.utils.unregister_class(FHToolsObjectPanel)
    bpy.utils.unregister_class(FHToolsBonesPanel)
    bpy.utils.unregister_class(FHToolsAnimPanel)