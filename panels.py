import bpy
from bpy.types import Panel

from . import operators

class MPXGEN_PT_MainPanel(Panel):
    bl_label = "Masterpiece X Generator"
    bl_idname = "MPXGEN_PT_MainPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Masterpiece X"
    # Change the option to a valid one
    # DEFAULT_OPEN is not valid, the valid options are: DEFAULT_CLOSED, HIDE_HEADER, INSTANCED, HEADER_LAYOUT_EXPAND
    
    # Modify the label to show generation status
    @classmethod
    def poll(cls, context):
        # Add status information to the panel header if generation is active
        if operators.generation_status["active"]:
            cls.bl_label = f"Masterpiece X Generator ● ACTIVE"
        else:
            cls.bl_label = "Masterpiece X Generator"
        return True

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
        
        # Check if generation is active
        if operators.generation_status["active"]:
            # DON'T update progress value in scene - this is not allowed in draw method!
            # Instead use the value directly from generation_status
            
            # Status display - Make it VERY visible with a red box 
            box = layout.box()
            row = box.row()
            row.alert = True  # Makes the box red/highlighted
            row.label(text="▶ GENERATION ACTIVE ◀", icon='INFO')
            
            # Always show status text, even if empty
            status_text = operators.generation_status["status_text"] or "Initializing..."
            layout.label(text=status_text)
            
            # Always show progress percentage
            progress_percent = int(operators.generation_status["progress"])
            layout.label(text=f"Progress: {progress_percent}%")
            
            # Show a fake progress bar using row percentage
            if progress_percent > 0:
                row = layout.row()
                progress_row = layout.row()
                # Create a visual representation of the progress bar
                for i in range(10):  # 10 segments
                    segment = progress_row.row()
                    if i < progress_percent // 10:
                        segment.alert = True  # Highlight completed segments
                    segment.label(text="█")
            
            # Display any error
            if operators.generation_status["error"]:
                box = layout.box()
                box.alert = True
                box.label(text=f"Error: {operators.generation_status['error']}", icon='ERROR')
            
            # Always show cancel button with strong visibility
            layout.separator()
            row = layout.row()
            row.scale_y = 1.5  # Make button larger
            row.operator("mpxgen.cancel_generation", text="Cancel Generation", icon='X')
        else:
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
    # Register classes, but check if they're already registered first
    for cls in classes:
        try:
            # Check if the class is already registered
            if hasattr(bpy.types, cls.__name__):
                # Skip registration for this class
                print(f"Class {cls.__name__} is already registered, skipping.")
                continue
            
            # Register the class
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"Could not register {cls.__name__}: {str(e)}")
    
    # Register properties
    if not hasattr(bpy.types.Scene, "mpx_prompt"):
        bpy.types.Scene.mpx_prompt = bpy.props.StringProperty(
            name="Prompt",
            description="Text prompt to generate the 3D model",
            default="A detailed sculpture of a lion"
        )
    
    if not hasattr(bpy.types.Scene, "mpx_num_steps"):
        bpy.types.Scene.mpx_num_steps = bpy.props.IntProperty(
            name="Diffusion Steps",
            description="Number of diffusion steps (higher = better quality but slower)",
            default=4,
            min=1,
            max=4
        )
    
    if not hasattr(bpy.types.Scene, "mpx_texture_size"):
        bpy.types.Scene.mpx_texture_size = bpy.props.IntProperty(
            name="Texture Size",
            description="Size of texture in pixels",
            default=1024,
            min=512,
            max=2048,
            step=512
        )
    
    if not hasattr(bpy.types.Scene, "mpx_seed"):
        bpy.types.Scene.mpx_seed = bpy.props.IntProperty(
            name="Seed",
            description="Random seed for generation",
            default=1,
            min=1
        )
    
    # Add progress property for UI display
    if not hasattr(bpy.types.Scene, "mpx_progress"):
        bpy.types.Scene.mpx_progress = bpy.props.FloatProperty(
            name="Generation Progress",
            description="Current progress of the model generation",
            default=0.0,
            min=0.0,
            max=1.0,
            subtype='PERCENTAGE',
            options={'SKIP_SAVE'}
        )

def unregister():
    # Unregister properties
    if hasattr(bpy.types.Scene, "mpx_prompt"):
        del bpy.types.Scene.mpx_prompt
    
    if hasattr(bpy.types.Scene, "mpx_num_steps"):
        del bpy.types.Scene.mpx_num_steps
    
    if hasattr(bpy.types.Scene, "mpx_texture_size"):
        del bpy.types.Scene.mpx_texture_size
    
    if hasattr(bpy.types.Scene, "mpx_seed"):
        del bpy.types.Scene.mpx_seed
    
    if hasattr(bpy.types.Scene, "mpx_progress"):
        del bpy.types.Scene.mpx_progress
    
    # Unregister classes
    for cls in reversed(classes):
        try:
            if hasattr(bpy.types, cls.__name__):
                bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Could not unregister {cls.__name__}: {str(e)}") 