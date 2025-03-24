"""
Operators for Masterpiece X Generator

This module contains the core functionality for generating 3D models from text prompts.
It handles the communication with the Masterpiece X API, the generation process,
and the downloading and importing of the generated models.

The generation process is split into multiple operators to make it non-blocking:
1. MPXGEN_OT_GenerateModel - Starts the generation process
2. MPXGEN_OT_PollStatus - Handles polling the API for status updates
3. MPXGEN_OT_ProcessImage - Processes the generated image
4. MPXGEN_OT_DownloadModel - Downloads and imports the model

The InstallDependencies and CancelGeneration operators handle utility functions.
"""

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
import re

# Try to import the required modules - these should be available from wheels
try:
    from mpx_genai_sdk import Masterpiecex
    import requests
    MASTERPIECEX_INSTALLED = True
except ImportError:
    MASTERPIECEX_INSTALLED = False

# Global state dictionary to track generation progress
generation_status = {
    "active": False,           # Whether generation is active
    "status_text": "",         # Current status message
    "progress": 0,             # Progress percentage (0-100)
    "current_step": "",        # Current step in the process
    "error": "",               # Error message if any
    "client": None,            # Masterpiece X client instance
    "image_request_id": None,  # ID of the text-to-image request
    "image_url": None,         # URL of the generated image
    "image_path": None,        # Local path to saved image
    "model_request_id": None,  # ID of the image-to-3D request
    "model_url": None,         # URL of the generated model
    "model_path": None,        # Local path to saved model
    "asset_request_id": None,  # ID of the asset upload
    "last_poll_time": 0,       # Last time we checked status
    "start_time": 0,           # When generation started
    "active_threads": []       # Track active background threads
}

def cleanup_resources():
    """Clean up any resources used by the addon"""
    global generation_status
    
    # Stop any active generations
    generation_status["active"] = False
    
    # Clean up any temporary files
    try:
        if generation_status.get("model_path") and os.path.exists(generation_status["model_path"]):
            try:
                os.remove(generation_status["model_path"])
            except:
                pass
        
        if generation_status.get("image_path") and os.path.exists(generation_status["image_path"]):
            try:
                os.remove(generation_status["image_path"])
            except:
                pass
    except:
        pass
    
    # Clear API client to prevent it from holding references
    generation_status["client"] = None
        
    # Reset all request IDs
    generation_status["image_request_id"] = None
    generation_status["model_request_id"] = None
    generation_status["asset_request_id"] = None
    
    # Clear URLs
    generation_status["image_url"] = None
    generation_status["model_url"] = None
    
    # Clear paths
    generation_status["image_path"] = None
    generation_status["model_path"] = None
    
    # Ensure threads are properly handled
    for thread in generation_status.get("active_threads", []):
        # We can't forcibly terminate threads, but we can ensure they're marked as daemon
        # so they'll exit when Blender does
        if thread and hasattr(thread, "daemon"):
            thread.daemon = True
    
    # Clear thread list
    generation_status["active_threads"] = []
    
    # Try to remove timers if any are active
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
                                bpy.ops.mpxgen.download_model('CANCEL', override)
                            except:
                                pass
    except:
        pass
        
    # Explicitly unload any imported external modules to release DLL files
    try:
        modules_to_unload = []
        
        # Find all modules related to our dependencies
        for module_name in list(sys.modules.keys()):
            if any(module_name.startswith(prefix) for prefix in [
                'charset_normalizer', 
                'pydantic', 
                'mpx_genai_sdk', 
                'requests', 
                'urllib3',
                'httpx',
                'idna',
                'certifi',
                'anyio',
                'httpcore',
                'sniffio',
                'distro',
                'h11',
                'typing_extensions',
                'annotated_types'
            ]):
                modules_to_unload.append(module_name)
                
        # Remove modules from sys.modules
        for module_name in modules_to_unload:
            if module_name in sys.modules:
                try:
                    # Set to None first to help with reference counting
                    sys.modules[module_name] = None
                    del sys.modules[module_name]
                except:
                    pass
    except:
        pass

def force_ui_update():
    """
    Force Blender to update the UI in all 3D View areas.
    
    This ensures that status changes are immediately visible to the user
    even when Blender is busy with other operations. It tries multiple
    approaches to ensure at least one works.
    """
    # Primary method - update all View3D areas
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    # Make sidebar visible
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            space.show_region_ui = True
                    
                    # Redraw UI and panels
                    for region in area.regions:
                        region.tag_redraw()
                    area.tag_redraw()
    except Exception:
        # Fallback method
        try:
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
        except Exception:
            pass
            
    # Force immediate redraw
    try:
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
    except Exception:
        pass


class MPXGEN_OT_InstallDependencies(bpy.types.Operator):
    """
    Check if the Masterpiece X SDK and dependencies are properly installed
    
    This operator attempts to import the required modules and updates
    the addon status accordingly. It serves as a dependency verification
    tool rather than an actual installer since the dependencies are
    included as wheels in the extension package.
    """
    bl_idname = "mpxgen.install_dependencies"
    bl_label = "Check Dependencies"
    bl_description = "Check if Masterpiece X dependencies are properly installed"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        """Try to import required modules and update status"""
        try:
            # Refresh the module cache
            import importlib
            importlib.invalidate_caches()
            
            # Try to import the required modules
            from mpx_genai_sdk import Masterpiecex
            import requests
            
            # Update the global flag if successful
            global MASTERPIECEX_INSTALLED
            MASTERPIECEX_INSTALLED = True
            
            self.report({'INFO'}, "Masterpiece X SDK is installed and ready to use")
            
            # Force UI update to reflect new status
            force_ui_update()
            
            return {'FINISHED'}
            
        except ImportError as e:
            self.report({'ERROR'}, f"Could not import required modules: {e}")
            self.report({'INFO'}, "Please restart Blender to load the included wheel packages")
            return {'CANCELLED'}


class MPXGEN_OT_CancelGeneration(bpy.types.Operator):
    """
    Cancel an active generation process
    
    This operator stops the current generation process by updating the
    global generation status. The polling operator will detect this change
    and terminate its operation.
    """
    bl_idname = "mpxgen.cancel_generation"
    bl_label = "Cancel Generation"
    bl_description = "Cancel the current model generation process"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        """Cancel the generation process by updating the global status"""
        global generation_status
        
        if not generation_status["active"]:
            self.report({'INFO'}, "No active generation to cancel")
            return {'CANCELLED'}
            
        # Update status to indicate cancellation
        generation_status["active"] = False
        generation_status["status_text"] = "Generation cancelled"
        generation_status["progress"] = 0
        generation_status["current_step"] = ""
        
        # Clean up any running background threads
        for thread in generation_status["active_threads"]:
            if thread.is_alive():
                # Can't forcibly terminate threads in Python, but we can
                # set a flag for them to check and exit cleanly
                pass
                
        # Clear the threads list
        generation_status["active_threads"] = []
        
        self.report({'INFO'}, "Generation process cancelled")
        
        # Force UI update to reflect cancellation
        force_ui_update()
                
        return {'FINISHED'}


class MPXGEN_OT_PollStatus(bpy.types.Operator):
    """
    Modal operator that polls the API for generation status updates
    
    This operator runs in the background while Blender remains responsive.
    It periodically checks the status of ongoing generation tasks and
    updates the UI accordingly. When tasks complete or fail, it initiates
    the appropriate next steps.
    """
    bl_idname = "mpxgen.poll_status"
    bl_label = "Poll Generation Status"
    bl_description = "Check the status of the current generation process"
    bl_options = {'REGISTER', 'INTERNAL', 'BLOCKING'}
    
    _timer = None
    _last_expand_time = 0
    
    def modal(self, context, event):
        """
        Modal function called on every timer event
        
        This checks the generation status, updates the UI, and determines
        when to move to the next step or terminate.
        """
        global generation_status
        
        # Check if we're still actively generating
        if not generation_status["active"]:
            self.cancel(context)
            return {'CANCELLED'}
            
        # Handle timer events
        if event.type == 'TIMER':
            # Ensure UI is updated on every tick
            force_ui_update()
            
            current_time = time.time()
            
            # Only poll API every few seconds to avoid rate limits
            if current_time - generation_status["last_poll_time"] >= 3:
                generation_status["last_poll_time"] = current_time
                
                # Update status text with elapsed time
                elapsed_time = int(current_time - generation_status["start_time"])
                minutes = elapsed_time // 60
                seconds = elapsed_time % 60
                time_str = f"{minutes}m {seconds}s"
                
                # Keep the current status text but add the elapsed time
                if "Generating" in generation_status["status_text"]:
                    generation_status["status_text"] = f"{generation_status['status_text'].split('(')[0]} ({time_str})"
                
                # Process according to current step
                try:
                    client = generation_status["client"]
                    current_step = generation_status["current_step"]
                    
                    if current_step == "image" and generation_status["image_request_id"]:
                        self._check_image_status(client)
                    elif current_step == "model" and generation_status["model_request_id"]:
                        self._check_model_status(client)
                except Exception as e:
                    self._handle_error(f"Error in polling: {e}")
                    return {'CANCELLED'}
        
        return {'PASS_THROUGH'}
    
    def _check_image_status(self, client):
        """Check status of the text-to-image generation"""
        try:
            status_response = client.status.retrieve(generation_status["image_request_id"])
            
            if status_response.status == "complete":
                generation_status["progress"] = 35
                generation_status["status_text"] = "Image generated successfully!"
                generation_status["current_step"] = "process_image"
                
                # Move to processing the image
                bpy.ops.mpxgen.process_image()
                
            elif status_response.status == "failed":
                self._handle_error("Image generation failed")
                
        except Exception as e:
            self._handle_error(f"Error checking image status: {e}")
    
    def _check_model_status(self, client):
        """Check status of the image-to-3D generation"""
        try:
            status_response = client.status.retrieve(generation_status["model_request_id"])
            
            # Update progress based on API response if available
            if hasattr(status_response, 'progress') and status_response.progress is not None:
                # Scale progress from the API (0-1) to our range based on where we are in the workflow
                try:
                    # Log original progress value for debugging
                    print(f"API progress value: {status_response.progress} (type: {type(status_response.progress)})")
                    
                    if generation_status["asset_request_id"] and not generation_status["image_request_id"]:
                        # Direct image-to-3D workflow (45-80% of our progress bar)
                        api_progress = min(1.0, float(status_response.progress))  # Ensure it's between 0 and 1
                        generation_status["progress"] = min(80, 45 + int(api_progress * 35))
                    else:
                        # Text-to-image-to-3D workflow (60-80% of our progress bar)
                        api_progress = min(1.0, float(status_response.progress))  # Ensure it's between 0 and 1
                        generation_status["progress"] = min(80, 60 + int(api_progress * 20))
                    
                    print(f"Converted to progress: {generation_status['progress']}%")
                except Exception as e:
                    print(f"Error processing progress value: {e}")
                    # Fall back to a safe default progress
                    if generation_status["asset_request_id"] and not generation_status["image_request_id"]:
                        generation_status["progress"] = 60  # Middle of direct image-to-3D progress range
                    else:
                        generation_status["progress"] = 70  # Middle of text-to-image-to-3D progress range
            
            if status_response.status == "complete":
                generation_status["progress"] = 80
                generation_status["status_text"] = "3D model generated successfully!"
                generation_status["current_step"] = "download_model"
                
                # Check if there's a model to download
                if (hasattr(status_response, 'outputs') and 
                    hasattr(status_response.outputs, 'glb') and 
                    status_response.outputs.glb):
                    
                    generation_status["model_url"] = status_response.outputs.glb
                    bpy.ops.mpxgen.download_model()
                else:
                    self._handle_error("No GLB model was generated")
                
            elif status_response.status == "failed":
                self._handle_error("3D model generation failed")
                
        except Exception as e:
            self._handle_error(f"Error checking model status: {e}")
    
    def _handle_error(self, error_msg):
        """Handle errors during polling"""
        generation_status["error"] = error_msg
        generation_status["active"] = False
        self.report({'ERROR'}, error_msg)
        self.cancel(bpy.context)
    
    def execute(self, context):
        """Start the modal timer and register with window manager"""
        wm = context.window_manager
        # Start timer for periodic checks
        self._timer = wm.event_timer_add(0.5, window=context.window)
        wm.modal_handler_add(self)
        
        # Initialize expand time tracking
        self._last_expand_time = 0
        
        # Ensure UI is updated immediately
        force_ui_update()
                    
        return {'RUNNING_MODAL'}
    
    def cancel(self, context):
        """Stop the timer and clean up"""
        # Remove the timer
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
            self._timer = None
        
        # Update UI one last time
        force_ui_update()
                
        return {'CANCELLED'}


class MPXGEN_OT_ProcessImage(bpy.types.Operator):
    """
    Process the generated image and start 3D model generation
    
    This operator is called automatically when the text-to-image generation
    is complete. It downloads the generated image, uploads it to the API,
    and initiates the 3D model generation process.
    """
    bl_idname = "mpxgen.process_image"
    bl_label = "Process Generated Image"
    bl_description = "Process the generated image and initiate 3D model generation"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    def execute(self, context):
        """Process the generated image and start 3D model generation"""
        global generation_status
        
        try:
            # Verify we have an image request ID
            if not generation_status["image_request_id"]:
                self._handle_error("No image request ID available")
                return {'CANCELLED'}
                
            client = generation_status["client"]
            
            # Get the generated image details
            status_response = client.status.retrieve(generation_status["image_request_id"])
            
            # Check if image generation was successful
            if not (hasattr(status_response, 'outputs') and 
                    hasattr(status_response.outputs, 'images') and 
                    status_response.outputs.images):
                self._handle_error("No images were generated")
                return {'CANCELLED'}
                
            # Get the image URL
            image_url = status_response.outputs.images[0]
            generation_status["image_url"] = image_url
            
            # Download the image
            self._download_image(image_url)
            
            # Create and upload the asset
            self._upload_image_as_asset(context)
            
            # Generate 3D model from image
            self._start_model_generation(context)
            
            # Update UI
            force_ui_update()
            return {'FINISHED'}
            
        except Exception as e:
            self._handle_error(f"Error in processing image: {e}")
            return {'CANCELLED'}
    
    def _download_image(self, image_url):
        """Download the generated image"""
        generation_status["status_text"] = "Downloading generated image..."
        generation_status["progress"] = 40
        force_ui_update()
        
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Save image to temporary file
            tmp_dir = tempfile.gettempdir()
            image_path = os.path.join(tmp_dir, "mpx_generated_image.png")
            with open(image_path, "wb") as f:
                f.write(response.content)
            
            generation_status["image_path"] = image_path
            
        except Exception as e:
            raise RuntimeError(f"Failed to download image: {e}")
    
    def _upload_image_as_asset(self, context):
        """Create an asset and upload the image"""
        generation_status["status_text"] = "Uploading image for 3D conversion..."
        generation_status["progress"] = 50
        force_ui_update()
        
        try:
            client = generation_status["client"]
            image_path = generation_status["image_path"]
            
            # Get API key from preferences
            preferences = context.preferences.addons.get("bl_ext.user_default.masterpiece_x_generator")
            if preferences and preferences.preferences:
                api_key = preferences.preferences.api_key
            else:
                raise RuntimeError("API key not found in preferences")
            
            # Create asset
            asset_response = client.assets.create(
                description="Generated image from Blender",
                name="blender_gen_image.png",
                type="image/png",
            )
            
            if not (hasattr(asset_response, 'asset_url') and 
                    hasattr(asset_response, 'request_id')):
                raise RuntimeError("Invalid asset response from API")
                
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
            
            if upload_response.status_code != 200:
                raise RuntimeError(f"Failed to upload image: {upload_response.text}")
                
        except Exception as e:
            raise RuntimeError(f"Failed to upload image as asset: {e}")
    
    def _start_model_generation(self, context):
        """Initiate 3D model generation from the uploaded image"""
        generation_status["status_text"] = "Starting 3D model generation..."
        generation_status["progress"] = 60
        force_ui_update()
        
        try:
            client = generation_status["client"]
            
            # Initiate 3D model generation
            imageto3d_request = client.functions.imageto3d(
                image_request_id=generation_status["asset_request_id"],
                seed=context.scene.mpx_seed,
                texture_size=context.scene.mpx_texture_size
            )
            
            # Update status
            generation_status["model_request_id"] = imageto3d_request.request_id
            generation_status["current_step"] = "model"
            generation_status["status_text"] = "Generating 3D model..."
            
        except Exception as e:
            raise RuntimeError(f"Failed to start 3D model generation: {e}")
    
    def _handle_error(self, error_msg):
        """Handle errors during image processing"""
        generation_status["error"] = error_msg
        generation_status["active"] = False
        self.report({'ERROR'}, error_msg)
        force_ui_update()


class MPXGEN_OT_DownloadModel(bpy.types.Operator):
    """Download and import the generated 3D model"""
    bl_idname = "mpxgen.download_model"
    bl_label = "Download Model"
    bl_description = "Download and import the generated 3D model"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    _timer = None
    _thread = None
    _download_completed = False
    _model_downloaded = False
    _download_error = None
    _glb_path = None
    
    def execute(self, context):
        global generation_status
        
        try:
            if generation_status["model_url"]:
                generation_status["status_text"] = "Downloading 3D model..."
                generation_status["progress"] = 85
                
                # Force UI update
                force_ui_update()
                
                # Set initial state for download thread
                self._download_completed = False
                self._model_downloaded = False
                self._download_error = None
                
                # Start a background thread for downloading
                self._thread = threading.Thread(
                    target=self._download_model_thread,
                    args=(generation_status["model_url"],)
                )
                self._thread.daemon = True  # Thread will die when Blender exits
                self._thread.start()
                
                # Add to active threads list for potential cleanup
                generation_status["active_threads"].append(self._thread)
                
                # Start the timer to check for completion
                wm = context.window_manager
                self._timer = wm.event_timer_add(0.5, window=context.window)
                wm.modal_handler_add(self)
                
                return {'RUNNING_MODAL'}
            else:
                generation_status["error"] = "No model URL available"
                generation_status["active"] = False
                self.report({'ERROR'}, generation_status["error"])
                
                # Force UI update
                force_ui_update()
                            
                return {'CANCELLED'}
            
        except Exception as e:
            generation_status["error"] = f"Error in downloading model: {str(e)}"
            generation_status["active"] = False
            self.report({'ERROR'}, generation_status["error"])
            
            # Force UI update
            force_ui_update()
                        
            return {'CANCELLED'}
    
    def _download_model_thread(self, model_url):
        """Background thread function to download the model"""
        try:
            # Download the model
            model_response = requests.get(model_url, timeout=60)
            model_response.raise_for_status()
            
            # Save to temporary file
            tmp_dir = tempfile.gettempdir()
            glb_path = os.path.join(tmp_dir, "mpx_generated_model.glb")
            with open(glb_path, "wb") as model_file:
                model_file.write(model_response.content)
            
            # Set success flags and path for modal callback
            self._glb_path = glb_path
            self._model_downloaded = True
            generation_status["model_path"] = glb_path
            
        except Exception as e:
            self._download_error = str(e)
        
        finally:
            # Signal completion to modal operator
            self._download_completed = True
            
    def modal(self, context, event):
        """Handle modal events and check download status"""
        if event.type == 'TIMER':
            # Check if download is finished
            if self._download_completed:
                # Remove thread from active threads list
                if self._thread in generation_status["active_threads"]:
                    generation_status["active_threads"].remove(self._thread)
                
                # Check for error
                if self._download_error:
                    generation_status["error"] = f"Error downloading model: {self._download_error}"
                    generation_status["active"] = False
                    self.report({'ERROR'}, generation_status["error"])
                    
                    # Force UI update
                    force_ui_update()
                    
                    # Remove timer
                    wm = context.window_manager
                    wm.event_timer_remove(self._timer)
                    
                    return {'CANCELLED'}
                
                # Check for success
                elif self._model_downloaded and self._glb_path:
                    generation_status["status_text"] = "Importing 3D model..."
                    generation_status["progress"] = 90
                    
                    # Force UI update
                    force_ui_update()
                    
                    # Import the model in the main thread for safety
                    try:
                        # Check if GLTF importer is available
                        if hasattr(bpy.ops.import_scene, 'gltf'):
                            bpy.ops.import_scene.gltf(filepath=self._glb_path)
                            
                            # Mark generation as complete and stop polling
                            generation_status["status_text"] = "Model imported successfully!"
                            generation_status["progress"] = 100
                            # Set active to false immediately to stop polling
                            generation_status["active"] = False
                            
                            # Force UI update
                            force_ui_update()
                            
                            # Remove timer
                            wm = context.window_manager
                            wm.event_timer_remove(self._timer)
                            
                            self.report({'INFO'}, "Model generated and imported successfully!")
                            return {'FINISHED'}
                            
                        else:
                            generation_status["error"] = "GLTF importer is not available. Please enable the 'Import-Export: glTF 2.0 format' addon."
                            generation_status["active"] = False
                            self.report({'ERROR'}, generation_status["error"])
                            
                            # Force UI update
                            force_ui_update()
                            
                            # Remove timer
                            wm = context.window_manager
                            wm.event_timer_remove(self._timer)
                            
                            return {'CANCELLED'}
                    except Exception as e:
                        generation_status["error"] = f"Error importing model: {str(e)}"
                        generation_status["active"] = False
                        self.report({'ERROR'}, generation_status["error"])
                        
                        # Force UI update
                        force_ui_update()
                        
                        # Remove timer
                        wm = context.window_manager
                        wm.event_timer_remove(self._timer)
                        
                        return {'CANCELLED'}
            
        return {'PASS_THROUGH'}


class MPXGEN_OT_GenerateModel(bpy.types.Operator):
    """
    Start the process of generating a 3D model from text or image
    
    This operator initiates the model generation process by:
    1. Validating input parameters
    2. Setting up the generation environment
    3. Starting the text-to-image or image-to-3D request
    4. Launching the background polling process
    
    The actual generation happens asynchronously using the polling operator.
    """
    bl_idname = "mpxgen.generate_model"
    bl_label = "Generate Model"
    bl_description = "Generate a 3D model from text prompt or image using Masterpiece X"
    bl_options = {'REGISTER', 'INTERNAL'}

    # Input parameters
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
    
    from_image: BoolProperty(
        name="From Image",
        description="Generate 3D model from an image instead of text",
        default=False
    )
    
    image_path: StringProperty(
        name="Image Path",
        description="Path to the image file to use for generation",
        default=""
    )

    def execute(self, context):
        """Set up and start the generation process"""
        # Verify dependencies are installed
        if not MASTERPIECEX_INSTALLED:
            self.report({'ERROR'}, "Masterpiece X SDK is not available. Please restart Blender to load the packages.")
            return {'CANCELLED'}

        # Verify API key is set
        preferences = context.preferences.addons.get("bl_ext.user_default.masterpiece_x_generator")
        if not preferences or not preferences.preferences or not preferences.preferences.api_key:
            self.report({'ERROR'}, "Please enter your Masterpiece X API key in the addon preferences")
            return {'CANCELLED'}
        
        api_key = preferences.preferences.api_key

        # Verify input parameters based on generation method
        if self.from_image:
            if not self.image_path or not os.path.exists(self.image_path):
                self.report({'ERROR'}, "Please select a valid image file")
                return {'CANCELLED'}
        else:
            # Text-based generation requires a prompt
            if not self.prompt:
                self.report({'ERROR'}, "Please enter a prompt to generate a model")
                return {'CANCELLED'}
            
        # Check if generation is already in progress
        global generation_status
        if generation_status["active"]:
            self.report({'WARNING'}, "A generation is already in progress. Please wait or cancel it.")
            return {'CANCELLED'}
        
        # Initialize generation status
        self._reset_generation_status()
        generation_status["active"] = True
        generation_status["status_text"] = "Initializing..."
        generation_status["progress"] = 5
        
        # Force immediate UI update
        force_ui_update()
        
        try:
            # Initialize the Masterpiece X client
            os.environ["MPX_SDK_BEARER_TOKEN"] = api_key
            client = Masterpiecex()
            generation_status["client"] = client
            
            if self.from_image:
                # Image-to-3D workflow
                self._start_image_based_generation(context)
            else:
                # Text-to-image workflow
                self._start_text_based_generation(context)
            
            return {'FINISHED'}
            
        except Exception as e:
            # Handle initialization errors
            self._handle_error(f"Error initiating generation: {e}")
            return {'CANCELLED'}
    
    def _start_text_based_generation(self, context):
        """Start text-to-image generation workflow"""
        client = generation_status["client"]
        
        # Update status
        generation_status["status_text"] = "Starting image generation..."
        generation_status["progress"] = 10
        generation_status["current_step"] = "image"
        
        # Force UI update with new status
        force_ui_update()
        
        try:
            # Initiate text-to-image generation
            text_to_image_request = client.components.text2image(
                prompt=self.prompt,
                num_images=1,
                num_steps=self.num_steps,
                lora_id="mpx_game"
            )
            
            # Store request ID and update status
            generation_status["image_request_id"] = text_to_image_request.request_id
            generation_status["status_text"] = "Generating image from text..."
            generation_status["progress"] = 15
            
            # Update UI and start the polling operator
            force_ui_update()
            bpy.ops.mpxgen.poll_status()
        
        except Exception as e:
            raise RuntimeError(f"Failed to start text-to-image generation: {e}")
    
    def _start_image_based_generation(self, context):
        """Start image-to-3D generation workflow"""
        client = generation_status["client"]
        
        # Update status
        generation_status["status_text"] = "Preparing to upload image..."
        generation_status["progress"] = 10
        
        # Force UI update
        force_ui_update()
        
        try:
            # Get image filename and mime type
            image_filename = os.path.basename(self.image_path)
            mime_type = self._get_mime_type_from_extension(self.image_path)
            
            # Sanitize filename for API - Masterpiece X only allows alphanumeric, underscore and period
            # First ensure the filename is lowercase
            sanitized_filename = image_filename.lower()
            # Replace any spaces with underscores
            sanitized_filename = sanitized_filename.replace(' ', '_')
            # Now filter out any non-alphanumeric, non-underscore, non-period characters
            sanitized_filename = re.sub(r'[^a-z0-9_.]', '', sanitized_filename)
            # Ensure filename is not empty and starts with a letter or number
            if not sanitized_filename or not sanitized_filename[0].isalnum():
                sanitized_filename = f"mpx_{int(time.time())}.{sanitized_filename.split('.')[-1]}"
            
            # Create asset for image upload
            generation_status["status_text"] = "Creating asset for image upload..."
            generation_status["progress"] = 15
            force_ui_update()
            
            asset_response = client.assets.create(
                description=f"Image uploaded from Blender: {image_filename}",
                name=sanitized_filename,
                type=mime_type,
            )
            
            if not (hasattr(asset_response, 'asset_url') and 
                    hasattr(asset_response, 'request_id')):
                raise RuntimeError("Invalid asset response from API")
                
            generation_status["asset_request_id"] = asset_response.request_id
            
            # Upload the image
            generation_status["status_text"] = "Uploading image..."
            generation_status["progress"] = 25
            force_ui_update()
            
            # Get API key from preferences
            preferences = context.preferences.addons.get("bl_ext.user_default.masterpiece_x_generator")
            if preferences and preferences.preferences:
                api_key = preferences.preferences.api_key
            else:
                raise RuntimeError("API key not found in preferences")
            
            # Set headers for upload
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': mime_type,
            }
            
            # Upload the image file
            with open(self.image_path, 'rb') as image_file:
                try:
                    upload_response = requests.put(
                        asset_response.asset_url, 
                        data=image_file.read(), 
                        headers=headers,
                        timeout=60
                    )
                    
                    if upload_response.status_code != 200:
                        error_message = f"Failed to upload image: {upload_response.text}"
                        if "Invalid asset name" in upload_response.text:
                            error_message += " Please use an image with a simpler filename (letters, numbers, underscores only)."
                        raise RuntimeError(error_message)
                except requests.exceptions.RequestException as e:
                    raise RuntimeError(f"Network error while uploading image: {str(e)}")
            
            # Start 3D model generation from the uploaded image
            generation_status["status_text"] = "Starting 3D model generation..."
            generation_status["progress"] = 40
            force_ui_update()
            
            # Use the asset request ID to generate the 3D model
            try:
                imageto3d_request = client.functions.imageto3d(
                    image_request_id=generation_status["asset_request_id"],
                    seed=self.seed,
                    texture_size=self.texture_size
                )
                
                # Update status to move to model generation step
                generation_status["model_request_id"] = imageto3d_request.request_id
                generation_status["current_step"] = "model"
                generation_status["status_text"] = "Generating 3D model from image..."
                generation_status["progress"] = 45
                
                # Force UI update and start the polling operator
                force_ui_update()
                bpy.ops.mpxgen.poll_status()
                
            except Exception as e:
                error_msg = str(e)
                if "Invalid asset" in error_msg:
                    raise RuntimeError(f"API rejected the image: {error_msg}. Try a different image or format.")
                else:
                    raise RuntimeError(f"Failed to start 3D model generation: {error_msg}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to process image: {e}")
    
    def _get_mime_type_from_extension(self, filepath):
        """Determine MIME type from file extension"""
        extension = os.path.splitext(filepath)[1].lower()
        
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
        }
        
        return mime_types.get(extension, 'image/png')
    
    def _reset_generation_status(self):
        """Reset the global generation status dictionary"""
        global generation_status
        generation_status.update({
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
            "last_poll_time": time.time(),
            "start_time": time.time(),
            "active_threads": []
        })
    
    def _handle_error(self, error_msg):
        """Handle errors during generation setup"""
        generation_status["active"] = False
        generation_status["error"] = error_msg
        self.report({'ERROR'}, error_msg)
        force_ui_update()


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
            print(f"Could not register {cls.__name__}: {str(e)}")

def unregister():
    # Cancel any active polling operation
    global generation_status
    generation_status["active"] = False
    
    # Clean up any running threads
    for thread in generation_status["active_threads"]:
        if thread.is_alive():
            # Can't forcibly terminate threads in Python, but we've set them as daemon
            # so they'll terminate when Blender exits
            pass
    
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