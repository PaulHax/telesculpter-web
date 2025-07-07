param(
    [switch]$SkipRust = $false,
    [switch]$SkipVSTools = $false
)

$ErrorActionPreference = "Stop"

Write-Host "Installing prerequisites for BurnOut bundle building on Windows..."

# Check if running as administrator
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Error: This script must be run as Administrator"
    exit 1
}

# Install Chocolatey if not present
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Chocolatey..."
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    
    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# Install Python 3.8
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Python 3.8..."
    choco install python38 -y
    
    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
} else {
    $version = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    if ($version -ne "3.8") {
        Write-Host "Warning: Python $version detected. KWIVER wheel requires Python 3.8"
    }
}

# Install Rust
if (-not $SkipRust -and -not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Rust..."
    
    # Download and install rustup
    $rustupUrl = "https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe"
    $rustupPath = "$env:TEMP\rustup-init.exe"
    
    Invoke-WebRequest -Uri $rustupUrl -OutFile $rustupPath
    Start-Process -FilePath $rustupPath -ArgumentList "-y" -Wait
    
    # Add Rust to PATH
    $cargoPath = "$env:USERPROFILE\.cargo\bin"
    $env:Path += ";$cargoPath"
}

# Install Visual Studio Build Tools
if (-not $SkipVSTools -and -not (Get-Command cl -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Visual Studio Build Tools (this may take a while)..."
    choco install visualstudio2022buildtools -y --params "--add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.VC.CMake.Project"
}

# Install Tauri CLI
if (-not (Get-Command cargo-tauri -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Tauri CLI..."
    if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
        Write-Host "Error: Rust/Cargo not found. Please install Rust first."
        exit 1
    }
    cargo install tauri-cli --version "^1.0"
}

# Verify installation
Write-Host "Verifying installation..."
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Python not found"
    exit 1
}

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Rust not found"
    exit 1
}

if (-not (Get-Command cargo-tauri -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Tauri CLI not found"
    exit 1
}

if (-not (Get-Command cl -ErrorAction SilentlyContinue)) {
    Write-Host "Warning: Visual Studio Build Tools not found (optional for sidecar compilation)"
}

Write-Host "Prerequisites installation complete!"
Write-Host "You can now run: .\build-windows-bundle.ps1"
Write-Host "Note: You may need to restart your terminal/PowerShell session for all changes to take effect"