#!/bin/bash
set -e

echo "Installing prerequisites for burn-out bundle building on Linux..."

# Check if sudo is available (we need it for package installation)
if ! command -v sudo &> /dev/null; then
    echo "Error: sudo is required but not found. Please install sudo or run as root."
    exit 1
fi

# Install system packages
echo "Installing system packages..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y \
        build-essential \
        libgl1-mesa-dev \
        libxt-dev \
        libx11-xcb-dev \
        libxcb1-dev \
        libxcb-glx0-dev \
        libexpat1-dev \
        libgtk2.0-dev \
        liblapack-dev \
        patchelf \
        curl \
        wget \
        libwebkit2gtk-4.0-dev \
        libsoup2.4-dev \
        libjavascriptcoregtk-4.0-dev \
        file \
        fuse \
        libfuse2 \
        gfortran \
        libgfortran5
elif command -v yum &> /dev/null; then
    sudo yum groupinstall -y "Development Tools"
    sudo yum install -y \
        mesa-libGL-devel \
        libXt-devel \
        libxcb-devel \
        expat-devel \
        gtk2-devel \
        lapack-devel \
        patchelf \
        curl \
        wget \
        webkit2gtk3-devel \
        libsoup-devel \
        file \
        fuse \
        fuse-libs \
        gcc-gfortran \
        libgfortran
elif command -v pacman &> /dev/null; then
    sudo pacman -S --needed \
        base-devel \
        mesa \
        libxt \
        libxcb \
        expat \
        gtk2 \
        lapack \
        patchelf \
        curl \
        wget \
        webkit2gtk \
        libsoup \
        file \
        fuse2 \
        gcc-fortran
else
    echo "Error: Unsupported package manager. Please install dependencies manually."
    exit 1
fi

# Install Rust
if ! command -v cargo &> /dev/null; then
    echo "Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

# Install Tauri CLI
if ! command -v cargo-tauri &> /dev/null; then
    echo "Installing Tauri CLI..."
    # Make sure cargo is in PATH
    if ! command -v cargo &> /dev/null; then
        source "$HOME/.cargo/env"
    fi
    cargo install tauri-cli --version "^1.0"
fi

# Verify installation
echo "Verifying installation..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found"
    exit 1
fi

if ! command -v cargo &> /dev/null; then
    echo "Error: Rust not found"
    exit 1
fi

if ! command -v patchelf &> /dev/null; then
    echo "Error: patchelf not found"
    exit 1
fi

echo "Prerequisites installation complete!"
echo "You can now run: ./build-linux-bundle.sh"
echo "Note: You may need to restart your terminal or run: source ~/.cargo/env"