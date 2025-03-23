import bpy
from bpy.types import Panel

from . import operators

class MPXGEN_PT_MainPanel(Panel):
    bl_label = "Masterpiece X Generator"
    bl_idname = "MPXGEN_PT_MainPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Masterpiece X"

    def draw(self, context):
        layout = self.layout
        
        # Check if Masterpiece X SDK is installed
        if not operators.MASTERPIECEX_INSTALLED:
            layout.label(text="Masterpiece X SDK not available")
            layout.label(text="Extensions should include wheels, you may need to restart Blender")
            layout.operator("mpxgen.install_dependencies", icon='PACKAGE', text="Check Dependencies")
            return
        
        # Check API key
        preferences = context.preferences.addons[__package__].preferences
        if not preferences.api_key:
            layout.label(text="API Key not set", icon='ERROR')
            layout.label(text="Set API Key in preferences")
            props = layout.operator(
                "preferences.addon_show",
                text="Open Preferences",
                icon='PREFERENCES'
            )
            props.module = __package__
            return
        
        # Prompt entry
        layout.label(text="Enter prompt for generation:")
        row = layout.row()
        row.prop(context.scene, "mpx_prompt", text="")
        
        # Advanced settings
        box = layout.box()
        box.label(text="Generation Settings")
        
        col = box.column(align=True)
        col.prop(context.scene, "mpx_num_steps", text="Diffusion Steps")
        col.prop(context.scene, "mpx_texture_size", text="Texture Size")
        col.prop(context.scene, "mpx_seed", text="Seed")
        
        # Generate button
        layout.separator()
        generate_op = layout.operator("mpxgen.generate_model", text="Generate 3D Model", icon='MESH_MONKEY')
        generate_op.prompt = context.scene.mpx_prompt
        generate_op.num_steps = context.scene.mpx_num_steps
        generate_op.texture_size = context.scene.mpx_texture_size
        generate_op.seed = context.scene.mpx_seed


# Registration
classes = (
    MPXGEN_PT_MainPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Register properties
    bpy.types.Scene.mpx_prompt = bpy.props.StringProperty(
        name="Prompt",
        description="Text prompt to generate the 3D model",
        default="A detailed sculpture of a lion"
    )
    
    bpy.types.Scene.mpx_num_steps = bpy.props.IntProperty(
        name="Diffusion Steps",
        description="Number of diffusion steps (higher = better quality but slower)",
        default=4,
        min=1,
        max=4
    )
    
    bpy.types.Scene.mpx_texture_size = bpy.props.IntProperty(
        name="Texture Size",
        description="Size of texture in pixels",
        default=1024,
        min=512,
        max=2048,
        step=512
    )
    
    bpy.types.Scene.mpx_seed = bpy.props.IntProperty(
        name="Seed",
        description="Random seed for generation",
        default=1,
        min=1
    )

def unregister():
    # Unregister properties
    del bpy.types.Scene.mpx_prompt
    del bpy.types.Scene.mpx_num_steps
    del bpy.types.Scene.mpx_texture_size
    del bpy.types.Scene.mpx_seed
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls) 