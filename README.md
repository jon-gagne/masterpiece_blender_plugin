# Masterpiece X Generator Extension for Blender

This Blender extension allows you to generate 3D models directly within Blender using Masterpiece X's GenAI API.

## Features

- Generate 3D models from text prompts
- Easy-to-use UI in Blender's sidebar
- Secure API key storage
- Configure generation parameters (texture size, steps, seed)
- Non-blocking generation process - continue using Blender while models generate
- Real-time status updates during generation

## Requirements

- Blender 4.2 or higher (for Extensions Platform)
- Internet connection
- Masterpiece X API key
- Python packages: `mpx_genai_sdk` and `requests` (included in the extension package)

## Installation

### Method 1: Using Extensions Platform (Recommended for Blender 4.2+)

1. Download the extension ZIP file (`masterpiece_x_generator-1.0.0.zip`)
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

## Building from Source

### Using Command Line

1. Make sure you have Python installed and accessible from the command line
2. Clone or download this repository
3. Navigate to the repository directory in your terminal/command prompt
4. Set the Blender executable path environment variable:

   **Windows:**
   ```
   set BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 4.3\blender.exe"
   ```
   
   **macOS:**
   ```
   export BLENDER_PATH="/Applications/Blender.app/Contents/MacOS/Blender"
   ```
   
   **Linux:**
   ```
   export BLENDER_PATH="/usr/bin/blender"
   ```

5. Build the extension:

   **Using the provided script:**
   ```
   build_extension.bat  # Windows
   ```
   
   **Or build directly with Blender:**
   ```
   "%BLENDER_PATH%" --command extension build  # Windows
   ```
   ```
   "$BLENDER_PATH" --command extension build  # macOS/Linux
   ```

6. The extension ZIP file will be created in the current directory (e.g., `masterpiece_x_generator-1.0.0.zip`)
7. Install using Method 1 above

### Manually Downloading Dependencies

The dependencies should already be in the ./wheels directory. However, if you need to manually download the wheel packages:

```
python -m pip download mpx_genai_sdk requests -d ./wheels
```

This will download all required wheels to the `wheels` directory, which the extension build will include.

## Verifying Installation

1. In the 3D View, press `N` to open the sidebar
2. Look for the "Masterpiece X" tab
3. If the panel shows "API Key not set", make sure you've entered your API key in preferences
4. If the panel shows "Masterpiece X SDK not available", make sure you've installed the extension correctly

## Usage

1. Open the Masterpiece X panel in the 3D View sidebar (press `N` to open the sidebar if it's not visible)
2. Enter your text prompt in the input field
3. Adjust the generation settings if needed:
   - **Diffusion Steps** (1-4): Higher values create better quality images but take longer
   - **Texture Size** (512-2048): Resolution of the textures (powers of 2 only)
   - **Seed**: Random seed for consistent results across generations
4. Click "Generate 3D Model"
5. Wait for the model to be generated and imported into your scene (this can take several minutes)
6. You can continue using Blender while generation is in progress

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

### Installation Issues

- **Extension Not Found**: Make sure you're using Blender 4.2+ for the Extensions Platform method
- **Add-on Not Found**: Verify that the folder structure is correct for the traditional installation
- **Dependencies Error**: The extension requires internet access to install dependencies

### API Key Issues

- Ensure your API key is correctly entered without extra spaces
- Check that your Masterpiece X account is active and has generation credits

### Runtime Issues

- If you get network errors, check your internet connection
- If generation times out, consider using fewer diffusion steps or smaller texture sizes
- If Blender crashes at the end of generation, try disabling other addons that might conflict

## License

This addon is provided under the GPL-3.0 license.

## Credits

- Masterpiece X for their GenAI API
- Uses the [Masterpiece X Python SDK](https://docs.masterpiecex.com/)
