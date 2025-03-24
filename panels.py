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
        
        # Use hardcoded module name to match the bl_idname in preferences
        preferences = context.preferences.addons.get("bl_ext.user_default.masterpiece_x_generator")
        if not preferences or not preferences.preferences or not preferences.preferences.api_key:
            self._draw_missing_api_key(layout, context)
            return
        
        if operators.generation_status["active"]:
            self._draw_active_generation_ui(layout)
        else:
            # Generation method tabs
            row = layout.row()
            row.prop(context.scene, "mpx_generation_method", expand=True)
            
            # Display appropriate form based on selected method
            if context.scene.mpx_generation_method == 'TEXT':
                self._draw_text_generation_form(layout, context)
            else:
                self._draw_image_generation_form(layout, context)
    
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
        props.module = "bl_ext.user_default.masterpiece_x_generator"
    
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
    
    def _draw_text_generation_form(self, layout, context):
        """Draw UI for text-based generation"""
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
        generate_op.from_image = False

    def _draw_image_generation_form(self, layout, context):
        """Draw UI for image-based generation"""
        # Image selection
        box = layout.box()
        box.label(text="Image Source", icon='IMAGE_DATA')
        
        if context.scene.mpx_image_path:
            # Show selected image path and preview if possible
            box.label(text=f"Selected: {bpy.path.basename(context.scene.mpx_image_path)}")
            
            # Try to display a preview of the image
            try:
                if bpy.data.images.get("MPX_Preview_Image"):
                    # Remove old preview to refresh
                    bpy.data.images.remove(bpy.data.images["MPX_Preview_Image"])
                
                # Load the image and give it a specific name for tracking
                preview_img = bpy.data.images.load(context.scene.mpx_image_path)
                preview_img.name = "MPX_Preview_Image"
                
                # Create a preview box with reasonable size
                preview_box = box.box()
                preview_box.template_image(preview_img, "MPX_Preview_Image", preview_img.name, compact=False)
            except Exception:
                # If preview fails, just show the path without error
                pass
            
            row = box.row()
            row.operator("mpxgen.select_image", text="Change Image", icon='FILE_FOLDER')
            row.operator("mpxgen.clear_image", text="Clear", icon='X')
        else:
            # No image selected yet
            box.label(text="No image selected")
            box.operator("mpxgen.select_image", text="Select Image", icon='FILE_FOLDER')
        
        # Image guidelines
        info_box = layout.box()
        info_box.label(text="Image Guidelines:", icon='INFO')
        col = info_box.column()
        col.scale_y = 0.7
        col.label(text="• Object should be centered in view")
        col.label(text="• Use diffuse lighting with minimal shadows")
        col.label(text="• Solid blank background is recommended")
        col.label(text="• Filenames should only use letters, numbers, and underscores")
        col.label(text="• Supported formats: PNG, JPG, JPEG, BMP, WEBP")
        
        # Generation settings
        box = layout.box()
        box.label(text="Generation Settings")
        
        col = box.column(align=True)
        col.prop(context.scene, "mpx_texture_size", text="Texture Size")
        col.prop(context.scene, "mpx_seed", text="Seed")
        
        # Generate button (disabled if no image is selected)
        layout.separator()
        row = layout.row()
        row.scale_y = 1.5
        
        if context.scene.mpx_image_path:
            generate_op = row.operator("mpxgen.generate_model", text="Generate 3D Model", icon='MESH_MONKEY')
            generate_op.texture_size = context.scene.mpx_texture_size
            generate_op.seed = context.scene.mpx_seed
            generate_op.from_image = True
            generate_op.image_path = context.scene.mpx_image_path
        else:
            row.enabled = False
            row.operator("mpxgen.generate_model", text="Select an Image First", icon='MESH_MONKEY')


class MPXGEN_OT_SelectImage(bpy.types.Operator):
    """Select an image for 3D model generation"""
    bl_idname = "mpxgen.select_image"
    bl_label = "Select Image"
    bl_description = "Select an image file to use for 3D model generation"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    filepath: bpy.props.StringProperty(
        name="File Path", 
        description="Path to the image file",
        default="", 
        subtype='FILE_PATH'
    )
    
    filter_glob: bpy.props.StringProperty(
        default="*.jpg;*.jpeg;*.png;*.bmp;*.webp",
        options={'HIDDEN'}
    )
    
    def execute(self, context):
        if self.filepath:
            # Check for potential filename issues
            import re
            import os
            
            filename = os.path.basename(self.filepath)
            if not re.match(r'^[a-zA-Z0-9_.]+$', filename):
                self.report({'WARNING'}, f"Image filename '{filename}' contains special characters. This may cause issues with the API.")
                
            context.scene.mpx_image_path = self.filepath
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class MPXGEN_OT_ClearImage(bpy.types.Operator):
    """Clear the selected image"""
    bl_idname = "mpxgen.clear_image"
    bl_label = "Clear Image"
    bl_description = "Clear the selected image"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    def execute(self, context):
        # Clear the image path
        context.scene.mpx_image_path = ""
        
        # Remove the preview image if it exists
        if bpy.data.images.get("MPX_Preview_Image"):
            bpy.data.images.remove(bpy.data.images["MPX_Preview_Image"])
            
        return {'FINISHED'}


# Registration
classes = (
    MPXGEN_PT_MainPanel,
    MPXGEN_OT_SelectImage,
    MPXGEN_OT_ClearImage,
)

def register():
    """Register panel classes and properties"""
    # Register classes, properly handling existing registrations
    for cls in classes:
        try:
            # First try to unregister if it's already registered
            if hasattr(bpy.types, cls.__name__):
                try:
                    bpy.utils.unregister_class(cls)
                    print(f"Unregistered existing {cls.__name__} before re-registration")
                except:
                    pass
            
            # Now register the class
            bpy.utils.register_class(cls)
            print(f"Successfully registered {cls.__name__}")
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
            default="A lion running"
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
    
    # Generation method selection
    if not hasattr(bpy.types.Scene, "mpx_generation_method"):
        bpy.types.Scene.mpx_generation_method = bpy.props.EnumProperty(
            name="Generation Method",
            description="Method to use for generating 3D models",
            items=[
                ('TEXT', "From Text", "Generate 3D model from text description"),
                ('IMAGE', "From Image", "Generate 3D model from an image")
            ],
            default='TEXT'
        )
    
    # Image path for image-based generation
    if not hasattr(bpy.types.Scene, "mpx_image_path"):
        bpy.types.Scene.mpx_image_path = bpy.props.StringProperty(
            name="Image Path",
            description="Path to image file for 3D model generation",
            default="",
            subtype='FILE_PATH'
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
        "mpx_progress",
        "mpx_generation_method",
        "mpx_image_path"
    ]
    
    for prop in properties:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop) 