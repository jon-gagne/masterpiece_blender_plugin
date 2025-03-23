# Masterpiece X Generator Extension for Blender

This Blender extension allows you to generate 3D models directly within Blender using Masterpiece X's GenAI API.

## Features

- Generate 3D models from text prompts
- Easy-to-use UI in Blender's sidebar
- Secure API key storage
- Configure generation parameters (texture size, steps, seed)

## Requirements

- Blender 4.2 or higher (for Extensions Platform)
- Internet connection
- Masterpiece X API key
- Python packages: `mpx_genai_sdk` and `requests` (included in the extension package)

## Installation

### Method 1: Using Extensions Platform (Recommended for Blender 4.2+)

1. Download the extension ZIP file
2. In Blender, go to `Edit > Preferences > Get Extensions > Install from Disk`
3. Select the downloaded ZIP file
4. Enable the extension if not automatically enabled
5. Enter your Masterpiece X API key in the addon preferences
   - You can get an API key by signing up at [Masterpiece X](https://www.masterpiecex.com/)

### Method 2: Traditional Addon Installation

1. Extract the ZIP file to get the `masterpiece_x_generator` folder
2. In Blender, go to `Edit > Preferences > Add-ons`
3. Click `Install...` and select the `masterpiece_x_generator` folder
4. Enable the addon by checking the box next to "3D View: Masterpiece X Generator"
5. Enter your API key in the addon preferences

## Usage

1. Open the Masterpiece X panel in the 3D View sidebar (press `N` to open the sidebar if it's not visible)
2. Enter your text prompt in the input field
3. Adjust the generation settings if needed:
   - **Diffusion Steps** (1-4): Higher values create better quality images but take longer
   - **Texture Size** (512-2048): Resolution of the textures (powers of 2 only)
   - **Seed**: Random seed for consistent results across generations
4. Click "Generate 3D Model"
5. Wait for the model to be generated and imported into your scene (this can take several minutes)

## Generation Process

This addon follows these steps to generate a 3D model:
1. Converts your text prompt into a reference image
2. Uploads the image to Masterpiece X
3. Uses the image to generate a 3D model
4. Downloads and imports the model into your Blender scene

## Permissions

This extension requires the following permissions:
- **Network access**: To connect to the Masterpiece X API
- **File access**: To save and load generated models and temporary files

## Troubleshooting

- **API Key Issues**: Ensure your API key is correctly entered in the addon preferences
- **Installation Errors**: Make sure you have an internet connection for installing dependencies
- **Import Errors**: The addon requires the GLB import feature in Blender, which should be available by default
- **Generation Timeout**: The generation process can take several minutes. Be patient and check the status bar for updates

## License

This addon is provided under the GPL-3.0 license.

## Credits

- Masterpiece X for their GenAI API
- Uses the [Masterpiece X Python SDK](https://docs.masterpiecex.com/) "# masterpiece_blender_plugin" 
