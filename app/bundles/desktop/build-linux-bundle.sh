#!/bin/bash
set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CACHE_DIR="$SCRIPT_DIR/cache"
VENV_DIR="$SCRIPT_DIR/.build-venv"

# KWIVER wheel configuration
WHEEL_URL="https://data.kitware.com/api/v1/item/686be6a0132a72f109c1bb9b/download"
WHEEL_FILENAME="kwiver-2.1.0-cp38-cp38-manylinux_2_28_x86_64.whl"

echo "Starting BurnOut Linux bundle build..."

# Check prerequisites
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

if ! command -v patchelf &> /dev/null; then
    echo "Error: patchelf is not installed. Install with: sudo apt-get install patchelf"
    exit 1
fi

if ! command -v cargo &> /dev/null; then
    echo "Error: Rust/Cargo is not installed"
    exit 1
fi

if ! command -v cargo-tauri &> /dev/null; then
    echo "Installing Tauri CLI..."
    cargo install tauri-cli --version "^1.0"
fi

# Download KWIVER wheel
mkdir -p "$CACHE_DIR"
WHEEL_PATH="$CACHE_DIR/$WHEEL_FILENAME"

if [[ ! -f "$WHEEL_PATH" ]]; then
    echo "Downloading KWIVER wheel..."
    wget -O "$WHEEL_PATH" "$WHEEL_URL"
fi

# Setup virtual environment
echo "Setting up virtual environment..."
rm -rf "$VENV_DIR"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Install in proper order: KWIVER wheel first (brings numpy), then our app, then pyinstaller.  Seems to fix lib gfortran fortran.so pyinstall bundling issues.  Seems to fix lib fortran.so pyinstall bundling issues.
pip install --upgrade pip
pip install "$WHEEL_PATH"
pip install "$PROJECT_ROOT/app"
pip install pyinstaller

# Clean previous builds
cd "$SCRIPT_DIR"
rm -rf build server.spec ./src-tauri/target ./src-tauri/server ./*.AppImage
rm -rf "$PROJECT_ROOT/app"/*.egg-info "$PROJECT_ROOT/app/build"

# Build PyInstaller bundle
echo "Building PyInstaller bundle..."
export KWIVER_PLUGIN_PATH="$VENV_DIR/lib/python3.8/site-packages/kwiver/lib/kwiver/plugins"

python -m PyInstaller \
    --clean --noconfirm \
    --hidden-import numpy \
    --hidden-import pkgutil \
    --exclude-module tkinter \
    --collect-data burn_out \
    --name server \
    --distpath src-tauri \
    --additional-hooks-dir="$SCRIPT_DIR" \
    "$SCRIPT_DIR/burn-out.py"

# Fix rpath in libraries (exactly like legacy script that worked)
echo "Fixing library rpaths..."
patchelf --set-rpath '$ORIGIN' ./src-tauri/server/_internal/numpy.libs/libopenblasp* 2>/dev/null || true
patchelf --set-rpath '$ORIGIN' ./src-tauri/server/_internal/numpy.libs/libopenblas64* 2>/dev/null || true
patchelf --set-rpath '$ORIGIN' ./src-tauri/server/_internal/numpy.libs/libgfortran* 2>/dev/null || true
# Fix OpenGL libraries that are causing the AppImage bundling to fail
patchelf --set-rpath '$ORIGIN' ./src-tauri/server/_internal/kwiver.libs/libGLX* 2>/dev/null || true
patchelf --set-rpath '$ORIGIN' ./src-tauri/server/_internal/kwiver.libs/libOpenGL* 2>/dev/null || true
patchelf --set-rpath '$ORIGIN' ./src-tauri/server/_internal/kwiver.libs/libGLdispatch* 2>/dev/null || true
# Fix X11 libraries that are causing the AppImage bundling to fail
patchelf --set-rpath '$ORIGIN' ./src-tauri/server/_internal/libXcursor* 2>/dev/null || true
patchelf --set-rpath '$ORIGIN' ./src-tauri/server/_internal/libXfixes* 2>/dev/null || true
# Fix webp image processing libraries
patchelf --set-rpath '$ORIGIN' ./src-tauri/server/_internal/libwebp* 2>/dev/null || true
patchelf --set-rpath '$ORIGIN' ./src-tauri/server/_internal/libsharpyuv* 2>/dev/null || true
# KWIVER plugin rpath fixes removed - collect_dynamic_libs() now handles everything without duplicates

# Generate web content and build Tauri bundle
echo "Generating web content..."
python -m trame.tools.www --output ./src-tauri/www

echo "Building Tauri AppImage..."
cargo tauri icon
cargo tauri build

# Move AppImage to current directory
mv ./src-tauri/target/release/bundle/appimage/burnout_*.AppImage .

echo "Build completed successfully!"
echo "AppImage created: $(ls -1 *.AppImage | head -1)"

# Cleanup
if [[ "$1" != "--keep-venv" ]]; then
    rm -rf "$VENV_DIR"
fi