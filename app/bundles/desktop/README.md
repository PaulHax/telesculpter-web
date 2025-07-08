# Desktop Bundle Building

This directory contains automated scripts for building BurnOut desktop bundles using PyInstaller and Tauri. The system uses prebuilt KWIVER wheels from GitLab, eliminating the need to compile KWIVER from source.

## Quick Start

### Option 1: Automated Build (Recommended)

**Linux:**

```bash
# Install prerequisites (run once)
./install-prerequisites-linux.sh

# Build the bundle
./build-linux-bundle.sh
```

**Windows:**

```powershell
# Install prerequisites (run once, as Administrator)
# Note: If you have Visual Studio Build Tools installed, run from
# "Developer Command Prompt" or "Developer PowerShell" for proper detection
.\install-prerequisites-windows.ps1

# Build the bundle
# Note: Run from "Developer Command Prompt" if you have VS Build Tools installed
.\build-windows-bundle.ps1
```

### Option 2: Manual Setup (Legacy)

<details>
<summary>Click to expand manual setup instructions</summary>

1. Create a new virtual environment and install the burnout application

```bash
python3 -m venv .venv
source .venv/bin/activate
# or for git bash on windows
source .venv/Scripts/activate

pip install -U pip
pip install  ../../

bash deps/install_kwiver.sh
source deps/kwiver/build/setup_KWIVER.sh
```

on Windows

```cmd
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install  ..\..\
#TODO make it part of burnout requirements
# retrieve from https://gitlab.kitware.com/kwiver/kwiver/-/packages/442 or the latest package available.
pip install kwiver-2.0.0-cp38-cp38-win_amd64.whl
```

2. Add pyinstaller and additional packages required for bundling.

```bash
pip install -r ./requirements.txt
```

3. Since Tauri is written in Rust, let's get setup with its dev environment.
   (This is required only the first time)

```bash
# Install rust.
# Also works in git bash on windows, but add ~/.cargo/bin to the path manually.
curl --proto '=https' --tlsv1.2 https://sh.rustup.rs -sSf | sh

# Enable rust within shell
. "$HOME/.cargo/env"
# or for git bash on windows
export PATH=$PATH:"/c/Users/$USERNAME/.cargo/bin"
```

on windows (powershell)

```powershell
# Install rust
curl.exe -o rustup-init.exe https://static.rust-lang.org/rustup/dist/i686-pc-windows-gnu/rustup-init.exe
.\rustup-init.exe

# Enable rust within the shell
$env:PATH="C:\Users\$env:USERNAME\.cargo\bin;$env:PATH"
```

On windows you also need to compile the C++ server launcher.

```cmd
cd .\src-tauri\sidecar
.\compile_sidecar.bat
cd ..\..\
```

4. Install tauri-cli(required only once)

```
cargo install tauri-cli --version "^1.0"
```

5. Run the build script

```bash
# after running source deps/kwiver/build/setup_kwiver.sh
./create_linux_tauri.sh
# or for git bash on windows
./create_exe_tauri_bash.sh
```

on windows

```cmd
.\create_exe_tauri.bat
```

This creates installers that can be uploaded to a gitlab release. On windows, both .exe and .msi installers are created.

</details>
