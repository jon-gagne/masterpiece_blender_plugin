# Installation Guide for Masterpiece X Generator Extension

This guide provides step-by-step instructions for installing the Masterpiece X Generator Extension in Blender.

## Prerequisites

1. **Blender 4.2 or higher** - Required for Extensions Platform support
2. **Masterpiece X API Key** - Obtain from [Masterpiece X](https://www.masterpiecex.com/)
3. **Internet Connection** - Required for API access

## Installation Methods

### Method 1: Using Blender Extensions Platform (Recommended)

1. Download the extension ZIP file (`masterpiece_x_generator-1.0.0.zip`)
2. Open Blender
3. Go to `Edit > Preferences > Get Extensions > Install from Disk`
4. Navigate to and select the downloaded ZIP file
5. The extension will be installed and should appear in the Extensions list
6. If not automatically enabled, click the checkbox to enable it
7. Enter your API key:
   - Find "Masterpiece X Generator" in the extensions list
   - Click the arrow to expand settings
   - Enter your API key in the appropriate field

### Method 2: Traditional Addon Installation

1. Extract the contents of the ZIP file to get the `masterpiece_x_generator` folder
2. Open Blender
3. Go to `Edit > Preferences > Add-ons`
4. Click `Install...` and navigate to the extracted `masterpiece_x_generator` folder
5. Select the folder and click `Install Add-on`
6. Find "3D View: Masterpiece X Generator" in the addon list
7. Enable it by checking the checkbox
8. Enter your API key in the preferences section of the addon

## Verifying Installation

1. In the 3D View, press `N` to open the sidebar
2. Look for the "Masterpiece X" tab
3. If the panel shows "API Key not set", make sure you've entered your API key in preferences
4. If the panel shows "Masterpiece X SDK not installed", click the "Install Dependencies" button

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

## Building from Source

If you want to build the extension from source:

1. Make sure you have Python installed
2. Run the `build_extension.bat` script (Windows) after setting the `BLENDER_PATH` environment variable
3. Use the generated ZIP file for installation 