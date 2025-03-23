import bpy
import os
import sys
import tempfile
import json
import time
import subprocess
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty
from pathlib import Path
from io import BytesIO

# Try to import the required modules - these should be available from wheels
try:
    from mpx_genai_sdk import Masterpiecex
    import requests
    MASTERPIECEX_INSTALLED = True
except ImportError:
    MASTERPIECEX_INSTALLED = False


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
            
            # Force refresh of the UI
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
                    
            return {'FINISHED'}
        except ImportError as e:
            self.report({'ERROR'}, f"Could not import required modules: {str(e)}")
            self.report({'INFO'}, "Please restart Blender to load the included wheel packages")
            return {'CANCELLED'}


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

        # Ensure progress bar is reset if we exit early
        progress_started = False
        
        try:
            # Initialize the Masterpiece X client using environment variable as per documentation
            os.environ["MPX_SDK_BEARER_TOKEN"] = api_key
            client = Masterpiecex()
            
            self.report({'INFO'}, "Generating image from text prompt...")
            bpy.context.window_manager.progress_begin(0, 100)
            progress_started = True
            bpy.context.window_manager.progress_update(10)
            
            # Step 1: Generate image from text
            try:
                text_to_image_request = client.components.text2image(
                    prompt=self.prompt,
                    num_images=1,
                    num_steps=self.num_steps,
                    lora_id="mpx_game"
                )
            except Exception as e:
                self.report({'ERROR'}, f"Failed to initiate text to image generation: {str(e)}")
                if progress_started:
                    bpy.context.window_manager.progress_end()
                return {'CANCELLED'}
            
            # Poll for completion
            self.report({'INFO'}, "Waiting for image generation to complete...")
            bpy.context.window_manager.progress_update(30)
            
            try:
                text_to_image_response = self.retrieve_request_status(client, text_to_image_request.request_id)
            except Exception as e:
                self.report({'ERROR'}, f"Error while waiting for image generation: {str(e)}")
                if progress_started:
                    bpy.context.window_manager.progress_end()
                return {'CANCELLED'}
            
            # Check response structure carefully
            if not hasattr(text_to_image_response, 'outputs') or not hasattr(text_to_image_response.outputs, 'images') or not text_to_image_response.outputs.images:
                self.report({'ERROR'}, "Unexpected API response structure. No images were generated.")
                if progress_started:
                    bpy.context.window_manager.progress_end()
                return {'CANCELLED'}
                
            image_url = text_to_image_response.outputs.images[0]
            
            # Step 2: Download the generated image
            self.report({'INFO'}, "Downloading generated image...")
            bpy.context.window_manager.progress_update(40)
            
            # Download image with error checking
            try:
                response = requests.get(image_url, timeout=30)
                response.raise_for_status()  # Raise exception for 4XX/5XX status codes
                image_data = response.content
            except requests.exceptions.RequestException as e:
                self.report({'ERROR'}, f"Failed to download image: {str(e)}")
                if progress_started:
                    bpy.context.window_manager.progress_end()
                return {'CANCELLED'}
            
            # Create a temporary file to save the image
            try:
                tmp_dir = tempfile.gettempdir()
                image_path = os.path.join(tmp_dir, "mpx_generated_image.png")
                with open(image_path, "wb") as f:
                    f.write(image_data)
            except (IOError, OSError) as e:
                self.report({'ERROR'}, f"Failed to save temporary image: {str(e)}")
                if progress_started:
                    bpy.context.window_manager.progress_end()
                return {'CANCELLED'}
            
            # Step 3: Create an asset and upload the image
            self.report({'INFO'}, "Uploading image for 3D conversion...")
            bpy.context.window_manager.progress_update(50)
            
            try:
                asset_response = client.assets.create(
                    description="Generated image from Blender",
                    name="blender_gen_image.png",
                    type="image/png",
                )
            except Exception as e:
                self.report({'ERROR'}, f"Failed to create asset: {str(e)}")
                if progress_started:
                    bpy.context.window_manager.progress_end()
                return {'CANCELLED'}
            
            if not hasattr(asset_response, 'asset_url') or not hasattr(asset_response, 'request_id'):
                self.report({'ERROR'}, "Invalid asset response from API")
                if progress_started:
                    bpy.context.window_manager.progress_end()
                return {'CANCELLED'}
            
            # Upload the image
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'image/png',
            }
            
            try:
                with open(image_path, 'rb') as image_file:
                    upload_response = requests.put(
                        asset_response.asset_url, 
                        data=image_file.read(), 
                        headers=headers,
                        timeout=60  # 60 second timeout
                    )
                
                if upload_response.status_code != 200:
                    self.report({'ERROR'}, f"Failed to upload image: {upload_response.text}")
                    if progress_started:
                        bpy.context.window_manager.progress_end()
                    return {'CANCELLED'}
            except Exception as e:
                self.report({'ERROR'}, f"Error during image upload: {str(e)}")
                if progress_started:
                    bpy.context.window_manager.progress_end()
                return {'CANCELLED'}
            
            # Step 4: Generate 3D model from image
            self.report({'INFO'}, "Generating 3D model from image...")
            bpy.context.window_manager.progress_update(60)
            
            try:
                imageto3d_request = client.functions.imageto3d(
                    image_request_id=asset_response.request_id,
                    seed=self.seed,
                    texture_size=self.texture_size
                )
            except Exception as e:
                self.report({'ERROR'}, f"Failed to initiate 3D model generation: {str(e)}")
                if progress_started:
                    bpy.context.window_manager.progress_end()
                return {'CANCELLED'}
            
            # Poll for completion
            self.report({'INFO'}, "Waiting for 3D model generation to complete...")
            bpy.context.window_manager.progress_update(70)
            
            try:
                imageto3d_response = self.retrieve_request_status(client, imageto3d_request.request_id)
            except Exception as e:
                self.report({'ERROR'}, f"Error while waiting for 3D model generation: {str(e)}")
                if progress_started:
                    bpy.context.window_manager.progress_end()
                return {'CANCELLED'}
            
            # Step 5: Download the GLB model
            self.report({'INFO'}, "Downloading 3D model...")
            bpy.context.window_manager.progress_update(80)
            
            if not hasattr(imageto3d_response, 'outputs') or not hasattr(imageto3d_response.outputs, 'glb') or not imageto3d_response.outputs.glb:
                self.report({'ERROR'}, "No GLB model was generated")
                if progress_started:
                    bpy.context.window_manager.progress_end()
                return {'CANCELLED'}
            
            glb_url = imageto3d_response.outputs.glb
            
            try:
                model_response = requests.get(glb_url, timeout=60)
                model_response.raise_for_status()
            except requests.exceptions.RequestException as e:
                self.report({'ERROR'}, f"Failed to download 3D model: {str(e)}")
                if progress_started:
                    bpy.context.window_manager.progress_end()
                return {'CANCELLED'}
            
            try:
                glb_path = os.path.join(tmp_dir, "mpx_generated_model.glb")
                with open(glb_path, "wb") as model_file:
                    model_file.write(model_response.content)
            except (IOError, OSError) as e:
                self.report({'ERROR'}, f"Failed to save 3D model: {str(e)}")
                if progress_started:
                    bpy.context.window_manager.progress_end()
                return {'CANCELLED'}
            
            # Step 6: Import the model into Blender
            self.report({'INFO'}, "Importing 3D model into Blender...")
            bpy.context.window_manager.progress_update(90)
            
            # Check if the GLTF importer is available
            if not hasattr(bpy.ops.import_scene, 'gltf'):
                self.report({'ERROR'}, "GLTF importer is not available. Please enable the 'Import-Export: glTF 2.0 format' addon.")
                if progress_started:
                    bpy.context.window_manager.progress_end()
                return {'CANCELLED'}
            
            try:
                bpy.ops.import_scene.gltf(filepath=glb_path)
            except Exception as e:
                self.report({'ERROR'}, f"Failed to import model: {str(e)}")
                if progress_started:
                    bpy.context.window_manager.progress_end()
                return {'CANCELLED'}
            
            if progress_started:
                bpy.context.window_manager.progress_end()
                
            self.report({'INFO'}, "Model generated and imported successfully!")
            
            return {'FINISHED'}
            
        except Exception as e:
            if progress_started:
                bpy.context.window_manager.progress_end()
            self.report({'ERROR'}, f"Error generating model: {str(e)}")
            return {'CANCELLED'}
    
    def retrieve_request_status(self, client, request_id, max_attempts=120):
        """Poll the API until the request is complete or timeout is reached"""
        status_response = client.status.retrieve(request_id)
        
        # Wait until the object has been generated (status = 'complete')
        # or max polling time reached (10 minutes at 5 seconds per poll)
        attempt = 0
        while status_response.status not in ["complete", "failed"] and attempt < max_attempts:
            time.sleep(5)  # Check every 5 seconds
            status_response = client.status.retrieve(request_id)
            attempt += 1
            
        if attempt >= max_attempts:
            self.report({'ERROR'}, "Request timed out after 10 minutes")
            raise Exception("Request timed out")
            
        if status_response.status == "failed":
            self.report({'ERROR'}, "The request failed")
            raise Exception("The request failed")
            
        return status_response


# Registration
classes = (
    MPXGEN_OT_InstallDependencies,
    MPXGEN_OT_GenerateModel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls) 