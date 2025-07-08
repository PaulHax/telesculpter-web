param(
    [switch]$KeepVenv = $false,
    [switch]$SkipSidecar = $false
)

$ErrorActionPreference = "Stop"

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Resolve-Path "$ScriptDir/../../.."
$CacheDir = "$ScriptDir/cache"
$VenvDir = "$ScriptDir/.build-venv"

# KWIVER wheel configuration
$WheelUrl = "https://data.kitware.com/api/v1/item/686be762132a72f109c1bb9e/download"
$WheelFilename = "kwiver-2.1.0-cp38-cp38-win_amd64.whl"

Write-Host "Starting BurnOut Windows bundle build..."

# Check prerequisites
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Python is not installed or not in PATH"
    exit 1
}

# Check Python version (KWIVER wheel requires Python 3.8)
$PythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($PythonVersion -ne "3.8") {
    Write-Host "Warning: KWIVER wheel is built for Python 3.8, but you have Python $PythonVersion"
    Write-Host "This may cause installation issues."
}

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Rust/Cargo is not installed. Run install-prerequisites-windows.ps1 first."
    exit 1
}

if (-not (Get-Command cargo-tauri -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Tauri CLI is not installed. Run install-prerequisites-windows.ps1 first."
    exit 1
}


# Check for Visual Studio Build Tools (for sidecar compilation)
if (-not $SkipSidecar -and -not (Get-Command cl -ErrorAction SilentlyContinue)) {
    Write-Host "Warning: Visual Studio Build Tools not found. Skipping sidecar compilation."
    $SkipSidecar = $true
}

# Download KWIVER wheel
if (-not (Test-Path $CacheDir)) {
    New-Item -ItemType Directory -Path $CacheDir | Out-Null
}

$WheelPath = "$CacheDir/$WheelFilename"
if (-not (Test-Path $WheelPath)) {
    Write-Host "Downloading KWIVER wheel..."
    Invoke-WebRequest -Uri $WheelUrl -OutFile $WheelPath
}

# Setup virtual environment
Write-Host "Setting up virtual environment..."
if (Test-Path $VenvDir) {
    Remove-Item -Recurse -Force $VenvDir
}

python -m venv $VenvDir
. "$VenvDir/Scripts/Activate.ps1"

python -m pip install --upgrade pip
pip install $WheelPath
pip install "$ProjectRoot/app"
pip install pyinstaller

# Compile sidecar if possible
if (-not $SkipSidecar) {
    Write-Host "Compiling sidecar executable..."
    Push-Location "$ScriptDir/src-tauri/sidecar"
    try {
        & "./compile_sidecar.bat"
    }
    catch {
        Write-Host "Warning: Failed to compile sidecar"
    }
    finally {
        Pop-Location
    }
}

# Clean previous builds
Push-Location $ScriptDir
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "server.spec") { Remove-Item -Force "server.spec" }
if (Test-Path "src-tauri/target") { Remove-Item -Recurse -Force "src-tauri/target" }
if (Test-Path "src-tauri/server") { Remove-Item -Recurse -Force "src-tauri/server" }
Get-ChildItem -Filter "*.exe" | Remove-Item -Force
Get-ChildItem -Filter "*.msi" | Remove-Item -Force

# Build PyInstaller bundle
Write-Host "Building PyInstaller bundle..."
$env:KWIVER_PLUGIN_PATH = "$VenvDir/Lib/site-packages/kwiver/lib/kwiver/plugins"

python -m PyInstaller `
    --clean --noconfirm `
    --windowed `
    --hidden-import numpy `
    --hidden-import pkgutil `
    --exclude-module tkinter `
    --collect-data burn_out `
    --name server `
    --distpath src-tauri `
    --additional-hooks-dir="$ScriptDir" `
    "$ScriptDir/burn-out.py"

# Generate web content and build Tauri bundle
Write-Host "Generating web content..."
python -m trame.tools.www --output ./src-tauri/www

Write-Host "Building Tauri installers..."
cargo tauri icon
cargo tauri build

# Move installers to current directory
$NsisPath = "./src-tauri/target/release/bundle/nsis"
$MsiPath = "./src-tauri/target/release/bundle/msi"

if (Test-Path $NsisPath) {
    Get-ChildItem -Path $NsisPath -Filter "*.exe" | Copy-Item -Destination .
}

if (Test-Path $MsiPath) {
    Get-ChildItem -Path $MsiPath -Filter "*.msi" | Copy-Item -Destination .
}

Pop-Location

Write-Host "Build completed successfully!"
$Installers = Get-ChildItem -Path $ScriptDir -Include "*.exe", "*.msi" -File
foreach ($Installer in $Installers) {
    Write-Host "Created: $($Installer.Name)"
}

# Cleanup
deactivate
if (-not $KeepVenv) {
    Remove-Item -Recurse -Force $VenvDir
}
