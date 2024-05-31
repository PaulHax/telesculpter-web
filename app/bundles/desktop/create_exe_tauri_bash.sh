#!/bin/bash

rm -rf build server.spec
rm -rf ./src-tauri/target
rm -rf ./src-tauri/server

CURRENT_DIR=$(pwd)
# Build bundle for tauri inside `./src-tauri/server/*` while skipping the web content.
python -m PyInstaller \
    --clean --noconfirm \
    --windowed \
    --hidden-import numpy \
    --hidden-import pkgutil \
    --exclude-module tkinter \
    --collect-data burn_out \
    --name server \
    --distpath src-tauri \
    --additional-hooks-dir="$CURRENT_DIR" \
    "$CURRENT_DIR/burn-out.py"

# Generate webcontent for tauri to bundle
python -m trame.tools.www --output ./src-tauri/www
# Generate icon for application using ./app-icon.png
cargo tauri icon
# Generate application, add --debug to add debugging tools in the application (i.e right click web tools)
cargo tauri build --verbose

mv ./src-tauri/target/release/bundle/nsis/* ./
mv ./src-tauri/target/release/bundle/msi/* ./
