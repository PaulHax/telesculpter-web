#!/bin/bash

rm -rf build server.spec
rm -rf ./src-tauri/target
rm -rf ./src-tauri/server

CURRENT_DIR=`dirname "$0"`
# Build bundle for tauri inside `./src-tauri/server/*` while skipping the web content.
python -m PyInstaller \
    --clean --noconfirm \
    --hidden-import numpy \
    --hidden-import pkgutil \
    --exclude-module tkinter \
    --collect-data burn_out \
    --name server \
    --distpath src-tauri \
    --additional-hooks-dir="$CURRENT_DIR" \
    "$CURRENT_DIR/burn-out.py"
# fix rpath in a couple of libraries before bundling. These were found by looking into the errors of cargo tauri build --verbose
patchelf --set-rpath  '$ORIGIN' ./src-tauri/server/_internal/numpy.libs/libopenblasp*
patchelf --set-rpath  '$ORIGIN' ./src-tauri/server/_internal/numpy.libs/libgfortran*

# Generate webcontent for tauri to bundle
python -m trame.tools.www --output ./src-tauri/www
# Generate icon for application using ./app-icon.png
cargo tauri icon
# Generate application, add --debug to add debugging tools in the application (i.e right click web tools)
cargo tauri build --verbose

mv ./src-tauri/target/release/bundle/appimage/burnout_*.AppImage .
