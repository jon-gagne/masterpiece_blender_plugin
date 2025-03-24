@echo off
REM Build script for Masterpiece X Generator Blender extension
REM This script uses Blender's built-in extension build command to create the correct structure

echo Building Masterpiece X Generator extension...

REM Check for and remove previous build outputs
if exist masterpiece_x_generator-1.0.0.zip del /f masterpiece_x_generator-1.0.0.zip
if exist build\masterpiece_x_generator rmdir /s /q build\masterpiece_x_generator
if exist build rmdir /s /q build

REM Check if Blender exists in the standard location
set BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 4.3\blender.exe"
if not exist %BLENDER_PATH% (
    echo Blender not found at %BLENDER_PATH%
    echo Please update the script with the correct path to blender.exe
    exit /b 1
)

REM Ensure wheels directory exists
if not exist wheels mkdir wheels

REM Build the extension using Blender's extension build command
echo Running Blender extension build command...
%BLENDER_PATH% --command extension build

if exist masterpiece_x_generator-1.0.0.zip (
    echo.
    echo Build successful! 
    echo The extension file masterpiece_x_generator-1.0.0.zip has been created.
) else (
    echo.
    echo Build may have failed. Check for any errors above.
)

echo.
echo Installation instructions:
echo 1. Open Blender
echo 2. Go to Edit ^ Preferences ^ Add-ons ^ Install
echo 3. Select the masterpiece_x_generator-1.0.0.zip file
echo 4. Enable the addon

pause 