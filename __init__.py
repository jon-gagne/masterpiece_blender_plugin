"""
Masterpiece X Generator - Blender Add-on
Generate 3D models from text prompts using Masterpiece X's GenAI API
"""

bl_info = {
    "name": "Masterpiece X Generator",
    "author": "Jonathan Gagne",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Masterpiece X",
    "description": "Generate 3D models using Masterpiece X's GenAI API",
    "warning": "",
    "doc_url": "",
    "category": "3D View",
}

import bpy
from bpy.props import StringProperty
from bpy.types import AddonPreferences
import importlib
import os

# Import addon modules with direct imports - Blender's extension build uses a flat structure
from . import operators
from . import panels

# Modules that need reloading on addon restart
modules = (
    operators,
    panels,
)

def reload_modules():
    """Reload addon modules when the addon is restarted"""
    for module in modules:
        importlib.reload(module)

class MasterpieceXPreferences(AddonPreferences):
    """Addon preferences for storing API key"""
    bl_idname = "bl_ext.user_default.masterpiece_x_generator"  # Full module path for Blender 4.3 extensions

    api_key: StringProperty(
        name="API Key",
        description="Enter your Masterpiece X API key",
        default="",
        subtype='PASSWORD'
    )

    def draw(self, context):
        """Draw the preferences panel"""
        layout = self.layout
        layout.label(text="Masterpiece X API Key")
        layout.prop(self, "api_key")
        layout.label(text="Get your API key from Masterpiece X website")
        layout.operator("wm.url_open", text="Visit Masterpiece X", icon='URL').url = "https://www.masterpiecex.com/"

classes = (
    MasterpieceXPreferences,
)

def register():
    """Register the addon and its classes"""
    # Reload modules when addon is reloaded
    try:
        reload_modules()
    except Exception as e:
        print(f"Failed to reload modules: {e}")
        
    # Register preferences class
    for cls in classes:
        try:
            # First try to unregister if it's already registered to prevent double registration
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
    
    # Register operators and panels
    try:
        operators.register()
    except Exception as e:
        print(f"Error registering operators: {e}")
        
    try:
        panels.register()
    except Exception as e:
        print(f"Error registering panels: {e}")

def unregister():
    """Unregister the addon and its classes"""
    # First perform critical cleanup before any unregistration
    try:
        print("Cleaning up resources...")
        from . import operators
        operators.cleanup_resources()
        
        # Import necessary modules for cleanup
        import sys
        import gc
    except Exception as e:
        print(f"Error importing modules for cleanup: {e}")
    
    # Clear any environment variables set by the addon
    try:
        if "MPX_SDK_BEARER_TOKEN" in os.environ:
            del os.environ["MPX_SDK_BEARER_TOKEN"]
    except Exception as e:
        print(f"Error clearing environment variables: {e}")
            
    # Clear any Blender data created by the addon
    try:
        # Clear any preview images
        if "MPX_Preview_Image" in bpy.data.images:
            bpy.data.images.remove(bpy.data.images["MPX_Preview_Image"])
    except Exception as e:
        print(f"Error clearing Blender data: {e}")
        
    # Unregister operators and panels with proper exception handling
    try:
        operators.unregister()
    except Exception as e:
        print(f"Error unregistering operators: {e}")
        
    try:
        panels.unregister()
    except Exception as e:
        print(f"Error unregistering panels: {e}")
    
    # Unregister preference class
    for cls in reversed(classes):
        try:
            if hasattr(bpy.types, cls.__name__):
                bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Could not unregister {cls.__name__}: {e}")
    
    # Reference cleanup for better unloading
    try:
        # Force multiple garbage collection passes
        print("Running garbage collection to release module references...")
        for _ in range(3):
            gc.collect()
        
        # Clear module references
        modules_to_clear = ["operators", "panels"]
        for module_name in modules_to_clear:
            if module_name in globals():
                globals()[module_name] = None
        
        # Run garbage collection again after clearing references
        gc.collect()
    except Exception as e:
        print(f"Error in reference cleanup: {e}")
        
    print("Masterpiece X Generator unregistered successfully")
    
    # For debugging - print warning about waiting for shutdown
    print("Note: Some files may only be fully released when Blender is closed")

if __name__ == "__main__":
    register() 