"""
UI Panels for Masterpiece X Generator
Contains the panel classes and UI layout for the addon
"""

import bpy
from bpy.types import Panel

from . import operators

class MPXGEN_PT_MainPanel(Panel):
    """Main panel for the Masterpiece X Generator addon"""
    bl_label = "Masterpiece X Generator"
    bl_idname = "MPXGEN_PT_MainPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Masterpiece X"
    
    @classmethod
    def poll(cls, context):
        """
        Determine if panel should be drawn and updates panel label
        Shows active status in panel label when generation is running
        """
        if operators.generation_status["active"]:
            cls.bl_label = f"Masterpiece X Generator ● ACTIVE"
        else:
            cls.bl_label = "Masterpiece X Generator"
        return True

    def draw(self, context):
        """Draw the panel UI elements"""
        layout = self.layout
        
        if not operators.MASTERPIECEX_INSTALLED:
            self._draw_sdk_not_available(layout)
            return
        
        preferences = context.preferences.addons[__package__].preferences
        if not preferences.api_key:
            self._draw_missing_api_key(layout, context)
            return
        
        if operators.generation_status["active"]:
            self._draw_active_generation_ui(layout)
        else:
            self._draw_generation_form(layout, context)
    
    def _draw_sdk_not_available(self, layout):
        """Draw error UI when SDK is not available"""
        layout.label(text="Masterpiece X SDK not available")
        layout.label(text="Extensions should include wheels, you may need to restart Blender")
        layout.operator("mpxgen.install_dependencies", icon='PACKAGE', text="Check Dependencies")
    
    def _draw_missing_api_key(self, layout, context):
        """Draw error UI when API key is not set"""
        layout.label(text="API Key not set", icon='ERROR')
        layout.label(text="Set API Key in preferences")
        props = layout.operator(
            "preferences.addon_show",
            text="Open Preferences",
            icon='PREFERENCES'
        )
        props.module = __package__
    
    def _draw_active_generation_ui(self, layout):
        """Draw UI during active generation process"""
        # Status header with alert color
        box = layout.box()
        row = box.row()
        row.alert = True
        row.label(text="▶ GENERATION ACTIVE ◀", icon='INFO')
        
        # Status text
        status_text = operators.generation_status["status_text"] or "Initializing..."
        layout.label(text=status_text)
        
        # Progress display
        progress_percent = int(operators.generation_status["progress"])
        layout.label(text=f"Progress: {progress_percent}%")
        
        # Custom progress bar
        if progress_percent > 0:
            progress_row = layout.row()
            for i in range(10):  # 10 segments
                segment = progress_row.row()
                if i < progress_percent // 10:
                    segment.alert = True
                segment.label(text="█")
        
        # Error display
        if operators.generation_status["error"]:
            box = layout.box()
            box.alert = True
            box.label(text=f"Error: {operators.generation_status['error']}", icon='ERROR')
        
        # Cancel button
        layout.separator()
        row = layout.row()
        row.scale_y = 1.5
        row.operator("mpxgen.cancel_generation", text="Cancel Generation", icon='X')
    
    def _draw_generation_form(self, layout, context):
        """Draw UI for setting up and starting generation"""
        # Prompt input
        layout.label(text="Enter prompt for generation:")
        row = layout.row()
        row.prop(context.scene, "mpx_prompt", text="")
        
        # Generation settings
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
    """Register panel classes and properties"""
    # Register classes, but check if they're already registered first
    for cls in classes:
        try:
            if hasattr(bpy.types, cls.__name__):
                print(f"Class {cls.__name__} is already registered, skipping.")
                continue
            
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"Could not register {cls.__name__}: {e}")
    
    # Register properties
    _register_properties()

def _register_properties():
    """Register the scene properties used by the addon"""
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
    
    # Property for UI display of progress
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
    """Unregister panel classes and properties"""
    _unregister_properties()
    
    # Unregister classes
    for cls in reversed(classes):
        try:
            if hasattr(bpy.types, cls.__name__):
                bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Could not unregister {cls.__name__}: {e}")

def _unregister_properties():
    """Unregister the scene properties used by the addon"""
    properties = [
        "mpx_prompt", 
        "mpx_num_steps", 
        "mpx_texture_size", 
        "mpx_seed", 
        "mpx_progress"
    ]
    
    for prop in properties:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop) 