import bpy
import os
import sys
import tempfile
import json
import time
import subprocess
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty, FloatProperty
from pathlib import Path
from io import BytesIO
import threading

# Try to import the required modules - these should be available from wheels
try:
    from mpx_genai_sdk import Masterpiecex
    import requests
    MASTERPIECEX_INSTALLED = True
except ImportError:
    MASTERPIECEX_INSTALLED = False

# Global variables to track generation status
generation_status = {
    "active": False,
    "status_text": "",
    "progress": 0,
    "current_step": "",
    "error": "",
    "client": None,
    "image_request_id": None,
    "image_url": None,
    "image_path": None,
    "model_request_id": None,
    "model_url": None,
    "model_path": None,
    "asset_request_id": None,
    "last_poll_time": 0,
    "start_time": 0
}

# Helper function to force UI updates across all Blender windows
def force_ui_update():
    # Update all View3D areas
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    # Force the sidebar to be open
                    try:
                        for space in area.spaces:
                            if space.type == 'VIEW_3D':
                                # Make sure the sidebar is visible
                                space.show_region_ui = True
                    except:
                        pass
                    
                    # Force redraw of all UI regions
                    for region in area.regions:
                        region.tag_redraw()
                    
                    # Tag the whole area
                    area.tag_redraw()
    except:
        # Fallback if the above fails
        try:
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
        except:
            pass
            
    # Try to force a redraw (safely)
    try:
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
    except:
        pass


class MPXGEN_OT_InstallDependencies(bpy.types.Operator):
    """Check if required dependencies are available"""
    bl_idname = "mpxgen.install_dependencies"
    bl_label = "Check Dependencies"
    bl_description = "Check if Masterpiece X dependencies are available"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        # Try importing the modules again
        try:
            import importlib
            importlib.invalidate_caches()
            
            # Try to import the required modules
            from mpx_genai_sdk import Masterpiecex
            import requests
            
            # Update the global flag
            global MASTERPIECEX_INSTALLED
            MASTERPIECEX_INSTALLED = True
            
            self.report({'INFO'}, "Masterpiece X SDK is installed and ready to use")
            
            # Force UI update
            force_ui_update()
                    
            return {'FINISHED'}
        except ImportError as e:
            self.report({'ERROR'}, f"Could not import required modules: {str(e)}")
            self.report({'INFO'}, "Please restart Blender to load the included wheel packages")
            return {'CANCELLED'}


class MPXGEN_OT_CancelGeneration(bpy.types.Operator):
    """Cancel the current generation process"""
    bl_idname = "mpxgen.cancel_generation"
    bl_label = "Cancel Generation"
    bl_description = "Cancel the current model generation process"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global generation_status
        generation_status["active"] = False
        generation_status["status_text"] = "Generation cancelled"
        generation_status["progress"] = 0
        generation_status["current_step"] = ""
        
        # Force UI update
        force_ui_update()
                
        return {'FINISHED'}


class MPXGEN_OT_PollStatus(bpy.types.Operator):
    """Poll the API for generation status"""
    bl_idname = "mpxgen.poll_status"
    bl_label = "Poll Generation Status"
    bl_description = "Check the status of the current generation process"
    bl_options = {'REGISTER', 'INTERNAL', 'BLOCKING'}
    
    _timer = None
    _last_expand_time = 0
    
    def modal(self, context, event):
        global generation_status
        
        # Check if we're still actively generating
        if not generation_status["active"]:
            self.cancel(context)
            return {'CANCELLED'}
            
        # Execute only when timer triggers
        if event.type == 'TIMER':
            current_time = time.time()
            
            # Force UI update on every timer tick
            force_ui_update()
            
            try:
                # Only poll every 3 seconds to avoid hammering the API
                if current_time - generation_status["last_poll_time"] >= 3:
                    generation_status["last_poll_time"] = current_time
                    elapsed_time = int(current_time - generation_status["start_time"])
                    minutes = elapsed_time // 60
                    seconds = elapsed_time % 60
                    time_str = f"{minutes}m {seconds}s"
                    
                    # Update status text with elapsed time
                    generation_status["status_text"] = f"Generating... ({time_str})"
                    
                    client = generation_status["client"]
                    
                    # Check if we're in the image generation phase
                    if generation_status["current_step"] == "image" and generation_status["image_request_id"]:
                        try:
                            status_response = client.status.retrieve(generation_status["image_request_id"])
                            
                            if status_response.status == "complete":
                                generation_status["progress"] = 35
                                generation_status["status_text"] = "Image generated successfully!"
                                generation_status["current_step"] = "process_image"
                                
                                # Force UI update before starting next step
                                force_ui_update()
                                
                                # Process the generated image - separate operator will handle this
                                bpy.ops.mpxgen.process_image()
                                
                            elif status_response.status == "failed":
                                generation_status["error"] = "Image generation failed"
                                generation_status["active"] = False
                                self.report({'ERROR'}, "Image generation failed")
                                self.cancel(context)
                                return {'CANCELLED'}
                                
                        except Exception as e:
                            generation_status["error"] = f"Error checking image status: {str(e)}"
                            self.report({'ERROR'}, generation_status["error"])
                            generation_status["active"] = False
                            self.cancel(context)
                            return {'CANCELLED'}
                    
                    # Check if we're in the 3D model generation phase
                    elif generation_status["current_step"] == "model" and generation_status["model_request_id"]:
                        try:
                            status_response = client.status.retrieve(generation_status["model_request_id"])
                            
                            if status_response.status == "complete":
                                generation_status["progress"] = 80
                                generation_status["status_text"] = "3D model generated successfully!"
                                generation_status["current_step"] = "download_model"
                                
                                # Force UI update before starting next step
                                force_ui_update()
                                
                                # Has GLB output
                                if hasattr(status_response, 'outputs') and hasattr(status_response.outputs, 'glb') and status_response.outputs.glb:
                                    generation_status["model_url"] = status_response.outputs.glb
                                    
                                    # Download and import model - separate operator will handle this
                                    bpy.ops.mpxgen.download_model()
                                else:
                                    generation_status["error"] = "No GLB model was generated"
                                    generation_status["active"] = False
                                    self.report({'ERROR'}, "No GLB model was generated")
                                    self.cancel(context)
                                    return {'CANCELLED'}
                                
                            elif status_response.status == "failed":
                                generation_status["error"] = "3D model generation failed"
                                generation_status["active"] = False
                                self.report({'ERROR'}, "3D model generation failed")
                                self.cancel(context)
                                return {'CANCELLED'}
                                
                        except Exception as e:
                            generation_status["error"] = f"Error checking model status: {str(e)}"
                            self.report({'ERROR'}, generation_status["error"])
                            generation_status["active"] = False
                            self.cancel(context)
                            return {'CANCELLED'}
                
            except Exception as e:
                generation_status["error"] = f"Error in polling: {str(e)}"
                self.report({'ERROR'}, generation_status["error"])
                generation_status["active"] = False
                self.cancel(context)
                return {'CANCELLED'}
        
        return {'PASS_THROUGH'}
    
    def execute(self, context):
        wm = context.window_manager
        # Start the timer, runs every 0.5 seconds
        self._timer = wm.event_timer_add(0.5, window=context.window)
        wm.modal_handler_add(self)
        
        # Initialize last expand time
        self._last_expand_time = 0
        
        # Force UI update
        force_ui_update()
                    
        return {'RUNNING_MODAL'}
    
    def cancel(self, context):
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
            self._timer = None
        
        # Force UI update
        force_ui_update()
                
        return {'CANCELLED'}


class MPXGEN_OT_ProcessImage(bpy.types.Operator):
    """Process the generated image and start 3D model generation"""
    bl_idname = "mpxgen.process_image"
    bl_label = "Process Generated Image"
    bl_description = "Process the generated image and initiate 3D model generation"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    def execute(self, context):
        global generation_status
        
        try:
            client = generation_status["client"]
            
            # Handle the image output
            if generation_status["image_request_id"]:
                status_response = client.status.retrieve(generation_status["image_request_id"])
                
                if hasattr(status_response, 'outputs') and hasattr(status_response.outputs, 'images') and status_response.outputs.images:
                    image_url = status_response.outputs.images[0]
                    generation_status["image_url"] = image_url
                    
                    # Download the image
                    generation_status["status_text"] = "Downloading generated image..."
                    generation_status["progress"] = 40
                    
                    # Force UI update
                    force_ui_update()
                    
                    try:
                        response = requests.get(image_url, timeout=30)
                        response.raise_for_status()
                        image_data = response.content
                        
                        # Save to temporary file
                        tmp_dir = tempfile.gettempdir()
                        image_path = os.path.join(tmp_dir, "mpx_generated_image.png")
                        with open(image_path, "wb") as f:
                            f.write(image_data)
                        
                        generation_status["image_path"] = image_path
                        
                        # Create an asset and upload the image
                        generation_status["status_text"] = "Uploading image for 3D conversion..."
                        generation_status["progress"] = 50
                        
                        # Force UI update
                        force_ui_update()
                        
                        # Get API key from addon preferences
                        preferences = context.preferences.addons[__package__].preferences
                        api_key = preferences.api_key
                        
                        asset_response = client.assets.create(
                            description="Generated image from Blender",
                            name="blender_gen_image.png",
                            type="image/png",
                        )
                        
                        if hasattr(asset_response, 'asset_url') and hasattr(asset_response, 'request_id'):
                            generation_status["asset_request_id"] = asset_response.request_id
                            
                            # Upload the image
                            headers = {
                                'Authorization': f'Bearer {api_key}',
                                'Content-Type': 'image/png',
                            }
                            
                            with open(image_path, 'rb') as image_file:
                                upload_response = requests.put(
                                    asset_response.asset_url, 
                                    data=image_file.read(), 
                                    headers=headers,
                                    timeout=60
                                )
                            
                            if upload_response.status_code == 200:
                                # Generate 3D model from image
                                generation_status["status_text"] = "Starting 3D model generation..."
                                generation_status["progress"] = 60
                                
                                # Force UI update
                                force_ui_update()
                                
                                # Get parameters from scene properties
                                imageto3d_request = client.functions.imageto3d(
                                    image_request_id=asset_response.request_id,
                                    seed=context.scene.mpx_seed,
                                    texture_size=context.scene.mpx_texture_size
                                )
                                
                                generation_status["model_request_id"] = imageto3d_request.request_id
                                generation_status["current_step"] = "model"
                                generation_status["status_text"] = "Generating 3D model..."
                                
                                # Force UI update
                                force_ui_update()
                                
                            else:
                                generation_status["error"] = f"Failed to upload image: {upload_response.text}"
                                generation_status["active"] = False
                                self.report({'ERROR'}, generation_status["error"])
                                
                                # Force UI update
                                force_ui_update()
                                            
                                return {'CANCELLED'}
                        else:
                            generation_status["error"] = "Invalid asset response from API"
                            generation_status["active"] = False
                            self.report({'ERROR'}, generation_status["error"])
                            
                            # Force UI update
                            force_ui_update()
                                        
                            return {'CANCELLED'}
                        
                    except Exception as e:
                        generation_status["error"] = f"Error processing image: {str(e)}"
                        generation_status["active"] = False
                        self.report({'ERROR'}, generation_status["error"])
                        
                        # Force UI update
                        force_ui_update()
                                    
                        return {'CANCELLED'}
                else:
                    generation_status["error"] = "No images were generated"
                    generation_status["active"] = False
                    self.report({'ERROR'}, generation_status["error"])
                    
                    # Force UI update
                    force_ui_update()
                                
                    return {'CANCELLED'}
            
            # Force UI update
            force_ui_update()
                    
            return {'FINISHED'}
            
        except Exception as e:
            generation_status["error"] = f"Error in processing image: {str(e)}"
            generation_status["active"] = False
            self.report({'ERROR'}, generation_status["error"])
            
            # Force UI update
            force_ui_update()
                        
            return {'CANCELLED'}


class MPXGEN_OT_DownloadModel(bpy.types.Operator):
    """Download and import the generated 3D model"""
    bl_idname = "mpxgen.download_model"
    bl_label = "Download Model"
    bl_description = "Download and import the generated 3D model"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    _timer = None
    
    def execute(self, context):
        global generation_status
        
        try:
            if generation_status["model_url"]:
                generation_status["status_text"] = "Downloading 3D model..."
                generation_status["progress"] = 85
                
                # Force UI update
                force_ui_update()
                
                # Download the model
                try:
                    model_response = requests.get(generation_status["model_url"], timeout=60)
                    model_response.raise_for_status()
                    
                    # Save to temporary file
                    tmp_dir = tempfile.gettempdir()
                    glb_path = os.path.join(tmp_dir, "mpx_generated_model.glb")
                    with open(glb_path, "wb") as model_file:
                        model_file.write(model_response.content)
                    
                    generation_status["model_path"] = glb_path
                    
                    # Import the model
                    generation_status["status_text"] = "Importing 3D model..."
                    generation_status["progress"] = 90
                    
                    # Force UI update
                    force_ui_update()
                    
                    # Check if GLTF importer is available
                    if hasattr(bpy.ops.import_scene, 'gltf'):
                        bpy.ops.import_scene.gltf(filepath=glb_path)
                        
                        generation_status["status_text"] = "Model imported successfully!"
                        generation_status["progress"] = 100
                        
                        # Force UI update
                        force_ui_update()
                        
                        # Reset status after a short delay instead of using a timer
                        # Start a timer to reset the status
                        wm = context.window_manager
                        self._timer = wm.event_timer_add(3.0, window=context.window)
                        wm.modal_handler_add(self)
                        
                        self.report({'INFO'}, "Model generated and imported successfully!")
                        return {'RUNNING_MODAL'}
                        
                    else:
                        generation_status["error"] = "GLTF importer is not available. Please enable the 'Import-Export: glTF 2.0 format' addon."
                        generation_status["active"] = False
                        self.report({'ERROR'}, generation_status["error"])
                        
                        # Force UI update
                        force_ui_update()
                                    
                        return {'CANCELLED'}
                    
                except Exception as e:
                    generation_status["error"] = f"Error downloading or importing model: {str(e)}"
                    generation_status["active"] = False
                    self.report({'ERROR'}, generation_status["error"])
                    
                    # Force UI update
                    force_ui_update()
                                
                    return {'CANCELLED'}
            else:
                generation_status["error"] = "No model URL available"
                generation_status["active"] = False
                self.report({'ERROR'}, generation_status["error"])
                
                # Force UI update
                force_ui_update()
                            
                return {'CANCELLED'}
            
            # Force UI update
            force_ui_update()
                    
            return {'FINISHED'}
            
        except Exception as e:
            generation_status["error"] = f"Error in downloading model: {str(e)}"
            generation_status["active"] = False
            self.report({'ERROR'}, generation_status["error"])
            
            # Force UI update
            force_ui_update()
                        
            return {'CANCELLED'}
            
    def modal(self, context, event):
        # This handles the timer for resetting status
        if event.type == 'TIMER':
            # Reset status
            global generation_status
            generation_status["active"] = False
            generation_status["status_text"] = ""
            generation_status["progress"] = 0
            generation_status["current_step"] = ""
            
            # Force UI update
            force_ui_update()
            
            # Remove timer
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
            
            return {'FINISHED'}
            
        return {'PASS_THROUGH'}


class MPXGEN_OT_GenerateModel(bpy.types.Operator):
    """Generate a 3D model from text using Masterpiece X"""
    bl_idname = "mpxgen.generate_model"
    bl_label = "Generate Model"
    bl_description = "Generate a 3D model from text prompt using Masterpiece X"
    bl_options = {'REGISTER', 'INTERNAL'}

    prompt: StringProperty(
        name="Prompt",
        description="Text prompt to generate the 3D model",
        default="",
    )
    
    num_steps: IntProperty(
        name="Diffusion Steps",
        description="Number of diffusion steps (higher = better quality but slower)",
        default=4,
        min=1,
        max=4
    )
    
    texture_size: IntProperty(
        name="Texture Size",
        description="Size of texture in pixels",
        default=1024,
        min=512,
        max=2048,
        step=512
    )
    
    seed: IntProperty(
        name="Seed",
        description="Random seed for generation",
        default=1,
        min=1
    )

    def execute(self, context):
        if not MASTERPIECEX_INSTALLED:
            self.report({'ERROR'}, "Masterpiece X SDK is not available. Please restart Blender to load the packages.")
            return {'CANCELLED'}

        # Get the API key from addon preferences
        preferences = context.preferences.addons[__package__].preferences
        api_key = preferences.api_key

        if not api_key:
            self.report({'ERROR'}, "Please enter your Masterpiece X API key in the addon preferences")
            return {'CANCELLED'}

        if not self.prompt:
            self.report({'ERROR'}, "Please enter a prompt to generate a model")
            return {'CANCELLED'}
            
        # Check if a generation is already in progress
        global generation_status
        if generation_status["active"]:
            self.report({'WARNING'}, "A generation is already in progress. Please wait or cancel it.")
            return {'CANCELLED'}
        
        # Reset generation status
        generation_status["active"] = True
        generation_status["status_text"] = "Initializing..."
        generation_status["progress"] = 5
        generation_status["current_step"] = ""
        generation_status["error"] = ""
        generation_status["client"] = None
        generation_status["image_request_id"] = None
        generation_status["image_url"] = None
        generation_status["image_path"] = None
        generation_status["model_request_id"] = None
        generation_status["model_url"] = None
        generation_status["model_path"] = None
        generation_status["asset_request_id"] = None
        generation_status["last_poll_time"] = time.time()
        generation_status["start_time"] = time.time()
        
        # Force UI update
        force_ui_update()
        
        try:
            # Initialize the Masterpiece X client
            os.environ["MPX_SDK_BEARER_TOKEN"] = api_key
            client = Masterpiecex()
            generation_status["client"] = client
            
            # Step 1: Start text-to-image generation
            generation_status["status_text"] = "Starting image generation..."
            generation_status["progress"] = 10
            generation_status["current_step"] = "image"
            
            # Force UI update again with updated status
            force_ui_update()
            
            text_to_image_request = client.components.text2image(
                prompt=self.prompt,
                num_images=1,
                num_steps=self.num_steps,
                lora_id="mpx_game"
            )
            
            generation_status["image_request_id"] = text_to_image_request.request_id
            generation_status["status_text"] = "Generating image from text..."
            generation_status["progress"] = 15
            
            # Force UI update again
            force_ui_update()
            
            # Start the polling operator
            bpy.ops.mpxgen.poll_status()
                    
            return {'FINISHED'}
            
        except Exception as e:
            generation_status["active"] = False
            generation_status["error"] = str(e)
            self.report({'ERROR'}, f"Error initiating generation: {str(e)}")
            return {'CANCELLED'}


# Registration
classes = (
    MPXGEN_OT_InstallDependencies,
    MPXGEN_OT_GenerateModel,
    MPXGEN_OT_PollStatus,
    MPXGEN_OT_ProcessImage,
    MPXGEN_OT_DownloadModel,
    MPXGEN_OT_CancelGeneration,
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

def unregister():
    # Cancel any active polling operation
    global generation_status
    generation_status["active"] = False
    
    # Make sure the timer is removed if active
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    for region in area.regions:
                        if region.type == 'WINDOW':
                            override = {'window': window, 'screen': window.screen, 'area': area, 'region': region}
                            try:
                                # Try to cancel any active poll operation
                                bpy.ops.mpxgen.poll_status('CANCEL', override)
                            except:
                                pass
    except:
        # In case window_manager is not available
        pass
    
    # Unregister classes
    for cls in reversed(classes):
        try:
            if hasattr(bpy.types, cls.__name__):
                bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Could not unregister {cls.__name__}: {str(e)}") 