import bpy

class XNAFH_PT_panel(bpy.types.Panel):
    bl_idname = "XNAFH_PT_panel"
    bl_label = ''
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "XNAFH"

    @classmethod
    def poll(cls, context):
        return (context.object is not None)

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="XNAFH")

    def draw(self, context):
        layout = self.layout

        # Material Menu
        layout.label(text="Material Colors")
        box = layout.box()
        row = box.row()
        row.prop(context.scene, "mat_color1")
        row.prop(context.scene, "mat_gloss1")

        # Palette Menu
        layout.label(text="Palette Colors")
        box = layout.box()
        row = box.row()
        row.prop(context.scene, "paint")
        row = box.row()
        row.prop(context.scene, "palette_color1")
        row = box.row()
        row.prop(context.scene, "palette_color2")
        row = box.row()
        row.prop(context.scene, "palette_color3")

        box = layout.box()
        row = box.row()
        row.prop(context.scene, "skin_color")

        box = layout.box()
        box.operator(apply_materials.bl_idname)

class apply_materials(bpy.types.Operator):
    """Applies material settings to all objects."""
    bl_idname = "object.apply_material"
    bl_label = "Apply Material"

    def execute(self, context):
        for ob in bpy.context.selected_objects:
            for ms in ob.material_slots:
                if ms.material:
                    for n in ms.material.node_tree.nodes:
                        if n.type =='GROUP' and n.node_tree == bpy.data.node_groups['For Honor Shader']:
                            n.inputs['Material Color'].default_value = context.scene.mat_color1
                            n.inputs['Material Gloss'].default_value = context.scene.mat_gloss1
                            n.inputs['Palette Color 1'].default_value = context.scene.palette_color1
                            n.inputs['Palette Color 2'].default_value = context.scene.palette_color2
                            n.inputs['Palette Color 3'].default_value = context.scene.palette_color3
                            n.inputs['Skin Color'].default_value = context.scene.skin_color
                            # n.inputs['Paint Color 2'].default_value = context.scene.palette_color2
                            # n.inputs['Paint Color 3'].default_value = context.scene.palette_color3
                            if context.scene.paint:
                                n.inputs['Paint Opacity'].default_value = 1.0
                            else:
                                n.inputs['Paint Opacity'].default_value = 0.0
        return {'FINISHED'}
    
def register():
    bpy.utils.register_class(XNAFH_PT_panel)
    bpy.utils.register_class(apply_materials)
    
    ## MATERIAL
    # Color
    bpy.types.Scene.mat_color1 = bpy.props.FloatVectorProperty(
                name = "Material Color",
                subtype = "COLOR",
                size = 4,
                min = 0.0,
                max = 1.0,
                default = (0.5,0.5,0.5,1.0))
    # Gloss
    bpy.types.Scene.mat_gloss1 = bpy.props.FloatProperty(
                name = "Gloss",
                min = -1.0,
                max = 1.0,
                default = 0.0)
    
    ## PALETTE
    bpy.types.Scene.paint = bpy.props.BoolProperty(
                name = "Enable Paint",
                default = False)
    bpy.types.Scene.palette_color1 = bpy.props.FloatVectorProperty(
                name = "Palette Color 1",
                subtype = "COLOR",
                size = 4,
                min = 0.0,
                max = 1.0,
                default = (1.0,1.0,1.0,1.0))

    bpy.types.Scene.palette_color2 = bpy.props.FloatVectorProperty(
                name = "Palette Color 2",
                subtype = "COLOR",
                size = 4,
                min = 0.0,
                max = 1.0,
                default = (1.0,1.0,1.0,1.0))

    bpy.types.Scene.palette_color3 = bpy.props.FloatVectorProperty(
                name = "Palette Color 3",
                subtype = "COLOR",
                size = 4,
                min = 0.0,
                max = 1.0,
                default = (1.0,1.0,1.0,1.0))
    ## SKIN COLOR
    bpy.types.Scene.skin_color = bpy.props.FloatVectorProperty(
                name = "Skin Color",
                subtype = "COLOR",
                size = 4,
                min = 0.0,
                max = 1.0,
                default = (0.5,0.5,0.5,1.0))