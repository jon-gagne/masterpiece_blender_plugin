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
    for cls in classes:
        bpy.utils.register_class(cls)
    
    operators.register()
    panels.register()

def unregister():
    operators.unregister()
    panels.unregister()
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register() 