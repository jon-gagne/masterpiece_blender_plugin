bl_info = {
    "name": "Masterpiece X Generator",
    "author": "Your Name",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Masterpiece X",
    "description": "Generate 3D models using Masterpiece X's GenAI API",
    "warning": "",
    "doc_url": "",
    "category": "3D View",
}

import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import AddonPreferences

import os
import sys
import importlib

# Import addon modules
from . import operators
from . import panels

# Reload modules when addon is reloaded
modules = (
    operators,
    panels,
)

def reload_modules():
    for module in modules:
        importlib.reload(module)

class MasterpieceXPreferences(AddonPreferences):
    bl_idname = __name__

    api_key: StringProperty(
        name="API Key",
        description="Enter your Masterpiece X API key",
        default="",
        subtype='PASSWORD'
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "api_key")

classes = (
    MasterpieceXPreferences,
)

def register():
    # Reload modules when addon is reloaded
    try:
        reload_modules()
    except:
        pass
        
    # Register preferences class
    for cls in classes:
        try:
            # Check if the class is already registered
            if hasattr(bpy.types, cls.__name__):
                # Skip registration for this class
                print(f"Class {cls.__name__} is already registered, skipping.")
                continue
                
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"Could not register {cls.__name__}: {str(e)}")
    
    # Register operators and panels
    try:
        operators.register()
    except Exception as e:
        print(f"Error registering operators: {str(e)}")
        
    try:
        panels.register()
    except Exception as e:
        print(f"Error registering panels: {str(e)}")

def unregister():
    # Tell users about potential issues with files
    try:
        print("Note: Some files may be in use and cannot be removed during uninstall.")
        print("If you see permission errors, it's normal and won't affect functionality.")
    except:
        pass
    
    # Unregister operators and panels
    try:
        operators.unregister()
    except Exception as e:
        print(f"Error unregistering operators: {str(e)}")
        
    try:
        panels.unregister()
    except Exception as e:
        print(f"Error unregistering panels: {str(e)}")
    
    # Unregister preference class
    for cls in reversed(classes):
        try:
            if hasattr(bpy.types, cls.__name__):
                bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Could not unregister {cls.__name__}: {str(e)}")

if __name__ == "__main__":
    register() 