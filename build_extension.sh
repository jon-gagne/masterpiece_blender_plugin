#!/bin/bash
# Build script for Masterpiece X Generator Blender extension
# This script uses Blender's built-in extension build command to create the correct structure

echo "Building Masterpiece X Generator extension..."

# Reminder for file permissions
if [[ ! -x "$0" ]]; then
    echo "First-time users: This script might need executable permissions."
    echo "Run: chmod +x $(basename $0)"
    echo ""
fi

# Determine pip command to use
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    echo "Error: Neither pip3 nor pip was found. Please install Python pip."
    exit 1
fi
echo "Using pip command: $PIP_CMD"

# Check for and remove previous build outputs
if [ -f "masterpiece_x_generator-1.0.0.zip" ]; then
    rm -f "masterpiece_x_generator-1.0.0.zip"
fi
if [ -d "build" ]; then
    rm -rf "build"
fi

# Ensure wheels directory exists
if [ ! -d "wheels" ]; then
    mkdir "wheels"
fi

# Detect platform for wheel downloads (improved with multiple checks)
if [[ "$OSTYPE" == "darwin"* ]] || [[ "$(uname)" == "Darwin" ]]; then
    # macOS - platform macosx
    PLATFORM="macosx_10_9_x86_64"
    PLATFORM_SHORT="macosx"
    
    # For Apple Silicon Macs, also get arm64 packages
    if [[ "$(uname -m)" == "arm64" ]] || [[ "$(uname -p)" == "arm" ]]; then
        PLATFORM="macosx_11_0_arm64"
        PLATFORM_SHORT="macosx"
        echo "Detected Apple Silicon Mac (ARM64)"
    else
        echo "Detected Intel Mac (x86_64)"
    fi
else
    # Linux - platform manylinux
    PLATFORM="manylinux_2_17_x86_64"
    PLATFORM_SHORT="manylinux"
    echo "Detected Linux (x86_64)"
    
    # Check for ARM Linux
    if [[ "$(uname -m)" == "aarch64" ]]; then
        PLATFORM="manylinux_2_17_aarch64"
        PLATFORM_SHORT="manylinux"
        echo "Detected Linux (ARM64)"
    fi
fi

# More robust wheel detection using find
NEED_WHEELS=0
if [ $(find wheels -name "*${PLATFORM_SHORT}*.whl" 2>/dev/null | wc -l) -eq 0 ]; then
    NEED_WHEELS=1
    echo "No $PLATFORM_SHORT wheels found. Need to download."
else
    # Check for essential packages with more robust pattern matching
    if [ $(find wheels -name "*mpx_genai_sdk*.whl" 2>/dev/null | wc -l) -eq 0 ]; then NEED_WHEELS=1; fi
    if [ $(find wheels -name "*requests*.whl" 2>/dev/null | wc -l) -eq 0 ]; then NEED_WHEELS=1; fi
    if [ $(find wheels -name "*pydantic_core*${PLATFORM_SHORT}*.whl" 2>/dev/null | wc -l) -eq 0 ]; then NEED_WHEELS=1; fi
    
    if [ $NEED_WHEELS -eq 1 ]; then
        echo "Some essential wheels are missing. Need to download."
    else
        echo "$PLATFORM_SHORT wheels already exist. Skipping download."
    fi
fi

# Download required wheel packages if needed
if [ $NEED_WHEELS -eq 1 ]; then
    echo "Downloading required wheel packages for Python 3.11 ($PLATFORM_SHORT)..."
    "$PIP_CMD" download --only-binary=:all: \
        --python-version 3.11 \
        --platform "$PLATFORM" \
        --implementation cp \
        -d wheels \
        mpx_genai_sdk \
        requests \
        anyio \
        certifi \
        charset_normalizer \
        distro \
        h11 \
        httpcore \
        httpx \
        idna \
        pydantic \
        pydantic_core \
        sniffio \
        typing_extensions \
        urllib3 \
        annotated_types

    # Check if download was successful
    if [ $? -ne 0 ]; then
        echo "Failed to download wheel packages. Check your internet connection."
        echo "The build process will continue, but the extension may not work correctly."
    else
        echo "Successfully downloaded wheel packages."
    fi
fi

# Check if user has set BLENDER_PATH environment variable
echo "Checking for Blender installation..."
if [ -n "$BLENDER_PATH" ]; then
    echo "Found user-defined BLENDER_PATH: $BLENDER_PATH"
else
    echo "BLENDER_PATH environment variable not set."
    echo "Trying default Blender installations..."
    
    # Detect operating system with improved checks
    if [[ "$OSTYPE" == "darwin"* ]] || [[ "$(uname)" == "Darwin" ]]; then
        # macOS paths (properly quoted for spaces in path)
        if [ -f "/Applications/Blender 4.4.app/Contents/MacOS/Blender" ]; then
            export BLENDER_PATH="/Applications/Blender 4.4.app/Contents/MacOS/Blender"
            echo "Found Blender 4.4"
        elif [ -f "/Applications/Blender 4.3.app/Contents/MacOS/Blender" ]; then
            export BLENDER_PATH="/Applications/Blender 4.3.app/Contents/MacOS/Blender"
            echo "Found Blender 4.3"
        elif [ -f "/Applications/Blender 4.2.app/Contents/MacOS/Blender" ]; then
            export BLENDER_PATH="/Applications/Blender 4.2.app/Contents/MacOS/Blender"
            echo "Found Blender 4.2"
        elif [ -f "/Applications/Blender 4.1.app/Contents/MacOS/Blender" ]; then
            export BLENDER_PATH="/Applications/Blender 4.1.app/Contents/MacOS/Blender"
            echo "Found Blender 4.1"
        elif [ -f "/Applications/Blender 4.0.app/Contents/MacOS/Blender" ]; then
            export BLENDER_PATH="/Applications/Blender 4.0.app/Contents/MacOS/Blender"
            echo "Found Blender 4.0"
        elif [ -f "/Applications/Blender.app/Contents/MacOS/Blender" ]; then
            export BLENDER_PATH="/Applications/Blender.app/Contents/MacOS/Blender"
            echo "Found Blender (default version)"
        fi
    else
        # Linux paths
        if command -v blender &> /dev/null; then
            # Use blender from PATH if available
            export BLENDER_PATH="$(which blender)"
            echo "Found Blender in PATH: $BLENDER_PATH"
        elif [ -f "/usr/bin/blender" ]; then
            export BLENDER_PATH="/usr/bin/blender"
            echo "Found Blender in /usr/bin"
        elif [ -f "/usr/local/bin/blender" ]; then
            export BLENDER_PATH="/usr/local/bin/blender"
            echo "Found Blender in /usr/local/bin"
        elif [ -f "/opt/blender/blender" ]; then
            export BLENDER_PATH="/opt/blender/blender"
            echo "Found Blender in /opt/blender"
        elif [ -f "/opt/blender-4.4/blender" ]; then
            export BLENDER_PATH="/opt/blender-4.4/blender"
            echo "Found Blender 4.4"
        elif [ -f "/opt/blender-4.3/blender" ]; then
            export BLENDER_PATH="/opt/blender-4.3/blender"
            echo "Found Blender 4.3"
        elif [ -f "/opt/blender-4.2/blender" ]; then
            export BLENDER_PATH="/opt/blender-4.2/blender"
            echo "Found Blender 4.2"
        elif [ -f "/opt/blender-4.1/blender" ]; then
            export BLENDER_PATH="/opt/blender-4.1/blender"
            echo "Found Blender 4.1"
        elif [ -f "/opt/blender-4.0/blender" ]; then
            export BLENDER_PATH="/opt/blender-4.0/blender"
            echo "Found Blender 4.0"
        fi
    fi
    
    # Check if we found Blender
    if [ -z "$BLENDER_PATH" ]; then
        echo "No Blender installation found in default locations."
        echo "Please set the BLENDER_PATH environment variable to your Blender executable:"
        echo ""
        if [[ "$OSTYPE" == "darwin"* ]] || [[ "$(uname)" == "Darwin" ]]; then
            echo "    export BLENDER_PATH=\"/Applications/Blender.app/Contents/MacOS/Blender\""
        else
            echo "    export BLENDER_PATH=\"/path/to/your/blender\""
        fi
        echo ""
        echo "Then run this script again."
        exit 1
    fi
fi

# Build the extension using Blender's extension build command
echo "Running Blender extension build command with: \"$BLENDER_PATH\""
"$BLENDER_PATH" --command extension build

if [ -f "masterpiece_x_generator-1.0.0.zip" ]; then
    echo ""
    echo "Build successful!"
    echo "The extension file masterpiece_x_generator-1.0.0.zip has been created."
else
    echo ""
    echo "Build may have failed. Check for any errors above."
fi

echo ""
echo "Installation instructions:"
echo "1. Open Blender"
echo "2. Go to Edit > Preferences > Add-ons > Install"
echo "3. Select the masterpiece_x_generator-1.0.0.zip file"
echo "4. Enable the addon"

# Make the script executable with: chmod +x build_extension.sh 