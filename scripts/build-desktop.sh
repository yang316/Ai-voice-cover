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

# 1. Install Node.js dependencies
echo "[1/5] Installing Node.js dependencies..."
npm install

# 2. Build Python sidecar for current platform
echo "[2/5] Building Python sidecar..."
source .venv/bin/activate

pip install pyinstaller --quiet

SIDECAr_NAME="ai-voice-cover-server"
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    SIDECAr_NAME="${SIDECAr_NAME}.exe"
fi

pyinstaller \
    --onefile \
    --name "$SIDECAr_NAME" \
    --add-data "backend:backend" \
    --add-data "frontend:frontend" \
    --hidden-import "uvicorn.logging" \
    --hidden-import "uvicorn.loops" \
    --hidden-import "uvicorn.loops.auto" \
    --hidden-import "uvicorn.protocols" \
    --hidden-import "uvicorn.protocols.http" \
    --hidden-import "uvicorn.protocols.http.auto" \
    --hidden-import "uvicorn.protocols.websockets" \
    --hidden-import "uvicorn.protocols.websockets.auto" \
    --hidden-import "uvicorn.lifespan" \
    --hidden-import "uvicorn.lifespan.on" \
    scripts/sidecar-launcher.py

# Copy sidecar to Tauri expected location
mkdir -p src-tauri/sidecar
TARGET_TRIPLE=$(rustc -vV | grep host | cut -d\' \' -f2)

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    cp dist/$SIDECAr_NAME "src-tauri/sidecar/${SIDECAr_NAME}-${TARGET_TRIPLE}"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    cp dist/$SIDECAr_NAME "src-tauri/sidecar/${SIDECAr_NAME}-${TARGET_TRIPLE}"
fi

echo "[3/5] Sidecar built: src-tauri/sidecar/"

# 3. Generate app icons
echo "[4/5] Generating icons..."
if [ ! -f src-tauri/icons/icon.png ]; then
    echo "  Warning: Place a 1024x1024 icon at src-tauri/icons/icon.png"
    echo "  Then run: npx @tauri-apps/cli icon src-tauri/icons/icon.png"
fi

# 4. Build Tauri app
echo "[5/5] Building Tauri app..."
npx tauri build

echo ""
echo "========================================="
echo "  Build complete!"
echo "  Output: src-tauri/target/release/bundle/"
echo "========================================="
