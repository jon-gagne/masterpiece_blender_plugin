@echo off
echo Building Masterpiece X Generator Extension...

REM Download required wheel packages
pip download mpx_genai_sdk requests -d ./wheels

REM Rename wheel files if needed (example only)
REM This script assumes the wheel files have specific names as referenced in manifest

REM Check if Blender executable path is set
if "%BLENDER_PATH%"=="" (
    echo BLENDER_PATH environment variable not set
    echo Usage: set BLENDER_PATH=C:\Path\to\blender.exe before running
    exit /b 1
)

REM Build the extension using Blender's command line
"%BLENDER_PATH%" --command extension build

echo Build complete! The extension ZIP should be in the current directory.
pause 