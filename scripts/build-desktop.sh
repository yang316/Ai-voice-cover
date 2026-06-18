#!/bin/bash
# Build AI Voice Cover Desktop App
# Usage: ./scripts/build-desktop.sh [linux|mac|windows|all]
set -e

PLATFORM=${1:-all}
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$APP_DIR"

echo "========================================="
echo "  AI Voice Cover - Desktop Build"
echo "========================================="

# 1. Build Vue frontend
echo "[1/5] Building Vue frontend..."
cd frontend-vue
npm ci
npm run build
cd "$APP_DIR"

# 2. Install root Node.js deps
echo "[2/5] Installing Node.js dependencies..."
npm install

# 3. Prepare sidecar directory
echo "[3/5] Preparing sidecar..."
SIDECAr_DIR="src-tauri/sidecar"
rm -rf "$SIDECAr_DIR"
mkdir -p "$SIDECAr_DIR"

# Copy launcher and requirements
cp scripts/sidecar-launcher.py "$SIDECAr_DIR/"
cp scripts/requirements.txt "$SIDECAr_DIR/"
cp scripts/requirements-ml.txt "$SIDECAr_DIR/"

# Copy backend source
cp -r backend "$SIDECAr_DIR/backend"

# Copy frontend dist (for backend static file serving)
mkdir -p "$SIDECAr_DIR/frontend-vue"
cp -r frontend-vue/dist "$SIDECAr_DIR/frontend-vue/dist"

# Download embedded Python (Windows only)
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "  Downloading embedded Python for Windows..."
    PYTHON_VERSION="3.11.9"
    PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-embed-amd64.zip"
    PYTHON_DIR="$SIDECAr_DIR/python"
    mkdir -p "$PYTHON_DIR"

    if [ ! -f "$PYTHON_DIR/python.exe" ]; then
        curl -L -o /tmp/python-embed.zip "$PYTHON_URL"
        unzip -q -o /tmp/python-embed.zip -d "$PYTHON_DIR"
        rm /tmp/python-embed.zip

        # Enable pip in embedded Python:
        # Uncomment import site in python311._pth
        sed -i 's/#import site/import site/' "$PYTHON_DIR/python311._pth"
        # Ensure Lib\site-packages is always on sys.path (._pth entries don't
        # require the dir to exist yet), so first-run pip installs are importable.
        grep -qxF 'Lib\site-packages' "$PYTHON_DIR/python311._pth" || \
            printf 'Lib\\site-packages\n' >> "$PYTHON_DIR/python311._pth"

        echo "  Embedded Python $PYTHON_VERSION downloaded"
    else
        echo "  Embedded Python already exists"
    fi
fi

echo "  Sidecar prepared: $SIDECAr_DIR/"

# 4. Generate app icons
echo "[4/5] Checking icons..."
if [ ! -f src-tauri/icons/icon.png ]; then
    echo "  Warning: Place a 1024x1024 icon at src-tauri/icons/icon.png"
    echo "  Then run: npx @tauri-apps/cli icon src-tauri/icons/icon.png"
fi

# 5. Build Tauri app
echo "[5/5] Building Tauri app..."
npx tauri build

echo ""
echo "========================================="
echo "  Build complete!"
echo "  Output: src-tauri/target/release/bundle/"
echo "========================================="
