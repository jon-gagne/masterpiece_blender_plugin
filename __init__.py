"""
Masterpiece X Generator - Blender Add-on
Generate 3D models from text prompts using Masterpiece X's GenAI API
"""

bl_info = {
    "name": "Masterpiece X Generator",
    "author": "Jonathan Gagne",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
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

# Import addon modules
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
    bl_idname = __name__

    api_key: StringProperty(
        name="API Key",
        description="Enter your Masterpiece X API key",
        default="",
        subtype='PASSWORD'
    )

    def draw(self, context):
        """Draw the preferences panel"""
        layout = self.layout
        layout.prop(self, "api_key")

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
            # Check if the class is already registered
            if hasattr(bpy.types, cls.__name__):
                print(f"Class {cls.__name__} is already registered, skipping.")
                continue
                
            bpy.utils.register_class(cls)
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
    # Unregister operators and panels
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

if __name__ == "__main__":
    register() 