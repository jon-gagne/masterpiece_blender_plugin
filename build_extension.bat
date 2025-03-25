@echo off
REM Build script for Masterpiece X Generator Blender extension
REM This script uses Blender's built-in extension build command to create the correct structure

echo Building Masterpiece X Generator extension...

REM Check for and remove previous build outputs
if exist masterpiece_x_generator-1.0.0.zip del /f masterpiece_x_generator-1.0.0.zip
if exist build\masterpiece_x_generator rmdir /s /q build\masterpiece_x_generator
if exist build rmdir /s /q build

REM Ensure wheels directory exists
if not exist wheels mkdir wheels

REM Check if we already have Windows wheels
set NEED_WHEELS=0
if not exist "wheels\*win_amd64*.whl" (
    set NEED_WHEELS=1
    echo No Windows wheels found. Need to download.
) else (
    REM Check for essential packages
    if not exist "wheels\*mpx_genai_sdk*.whl" set NEED_WHEELS=1
    if not exist "wheels\*requests*.whl" set NEED_WHEELS=1
    if not exist "wheels\*pydantic_core*win_amd64*.whl" set NEED_WHEELS=1
    
    if %NEED_WHEELS%==1 (
        echo Some essential wheels are missing. Need to download.
    ) else (
        echo Windows wheels already exist. Skipping download.
    )
)

REM Download required wheel packages for Python 3.11 if needed
if %NEED_WHEELS%==1 (
    echo Downloading required wheel packages for Python 3.11...
    pip download --only-binary=:all: ^
        --python-version 3.11 ^
        --platform win_amd64 ^
        --implementation cp ^
        -d wheels ^
        mpx_genai_sdk ^
        requests ^
        anyio ^
        certifi ^
        charset_normalizer ^
        distro ^
        h11 ^
        httpcore ^
        httpx ^
        idna ^
        pydantic ^
        pydantic_core ^
        sniffio ^
        typing_extensions ^
        urllib3 ^
        annotated_types

    REM Check if download was successful
    if errorlevel 1 (
        echo Failed to download wheel packages. Check your internet connection.
        echo The build process will continue, but the extension may not work correctly.
    ) else (
        echo Successfully downloaded wheel packages.
    )
)

REM Check if user has set BLENDER_PATH environment variable
echo Checking for Blender installation...
if defined BLENDER_PATH (
    echo Found user-defined BLENDER_PATH: %BLENDER_PATH%
) else (
    echo BLENDER_PATH environment variable not set.
    echo Trying default Blender installations...
    
    REM Try Blender 4.4
    if exist "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe" (
        set BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
        echo Found Blender 4.4
    ) else if exist "C:\Program Files\Blender Foundation\Blender 4.3\blender.exe" (
        set BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 4.3\blender.exe"
        echo Found Blender 4.3
    ) else if exist "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe" (
        set BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
        echo Found Blender 4.2
    ) else if exist "C:\Program Files\Blender Foundation\Blender 4.1\blender.exe" (
        set BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 4.1\blender.exe"
        echo Found Blender 4.1
    ) else if exist "C:\Program Files\Blender Foundation\Blender 4.0\blender.exe" (
        set BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 4.0\blender.exe"
        echo Found Blender 4.0
    ) else (
        echo No Blender installation found in default locations.
        echo Please set the BLENDER_PATH environment variable to your Blender executable:
        echo.
        echo     set BLENDER_PATH="C:\Path\to\your\blender.exe"
        echo.
        echo Then run this script again.
        pause
        exit /b 1
    )
)

REM Build the extension using Blender's extension build command
echo Running Blender extension build command with: %BLENDER_PATH%
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