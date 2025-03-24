# Masterpiece X Generator for Blender

A Blender add-on for generating 3D models from text descriptions or images using Masterpiece X's GenAI API.

## Features

- **Text-to-3D Generation**: Create 3D models directly from text descriptions
- **Image-to-3D Generation**: Upload an image to generate a 3D model
- **Non-blocking Interface**: Continue working in Blender during generation
- **Direct Import**: Models are automatically imported into your Blender scene
- **Custom Parameters**: Control texture size, seed, and other generation settings

## Installation

### Requirements

- Blender 4.0 or newer (tested with Blender 4.3)
- Internet connection
- Masterpiece X API key

### Installation Steps

1. Download the latest release (`masterpiece_x_generator-1.0.0.zip`)
2. In Blender, go to Edit > Preferences > Add-ons > Install
3. Select the downloaded zip file
4. Enable the add-on from the list
5. Enter your Masterpiece X API key in the addon preferences

## Usage

### Generating from Text

1. Open the Masterpiece X panel in the 3D View sidebar (press N)
2. Select "From Text" tab
3. Enter your text prompt
4. Adjust parameters if needed
5. Click "Generate 3D Model"

### Generating from Image

1. Open the Masterpiece X panel in the 3D View sidebar
2. Select "From Image" tab
3. Click "Select Image" and choose an image file (PNG, JPG, WEBP, BMP)
4. Adjust parameters if needed
5. Click "Generate 3D Model"

## Image Guidelines

For best results when generating from images:
- Center the object in the image
- Use diffuse lighting with minimal shadows
- Use a solid background with high contrast to the object
- Avoid complex scenes with multiple objects
- Simple filenames work best (use only letters, numbers, underscores)

## Building from Source

1. Clone this repository
2. Run `build_extension.bat` (requires Blender 4.3 installed at the default location)
3. The built extension (`masterpiece_x_generator-1.0.0.zip`) will be created

## Troubleshooting

### Installation Issues

- If installation fails, try restarting Blender
- Check the Blender console for error messages

### Generation Issues

- Ensure you have a valid API key entered in preferences
- For image generation, ensure your image meets the guidelines

### Uninstallation Issues

If you encounter errors during uninstallation:
1. Completely close Blender
2. Restart Blender 
3. Try disabling and removing the add-on again
4. If problems persist, see manual cleanup instructions in the troubleshooting section

## License

GPL-3.0
