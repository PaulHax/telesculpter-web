rmdir /Q /S .\build .\server.spec
rmdir /Q /S .\src-tauri\target
rmdir /Q /S .\src-tauri\server

:: CURRENT_DIR=`dirname "$0"`
:: Build bundle for tauri inside `./src-tauri/server/*` while skipping the web content.

python -m PyInstaller ^
    --clean --noconfirm ^
    --windowed ^
    --hidden-import numpy ^
    --hidden-import pkgutil ^
    --exclude-module tkinter ^
    --collect-data trame_quasar ^
    --collect-data trame_rca ^
    --collect-data trame_tauri ^
    --collect-data trame_client ^
    --collect-data burn_out ^
    --name server ^
    --distpath "./src-tauri" ^
    --additional-hooks-dir="." ^
    "burn-out.py"

:: Generate webcontent for tauri to bundle
python -m trame.tools.www --output ./src-tauri/www
::  Generate icon for application using ./app-icon.png
cargo tauri icon
:: Generate application add --debug to enable development tools
cargo tauri build
copy .\src-tauri\target\release\bundle\nsis\* .\
copy .\src-tauri\target\release\bundle\msi\* .\
