# Desktop

This relies on [pyinstaller](https://pyinstaller.org/en/stable/) and tauri (https://tauri.app/) to bundle your trame application into a standalone desktop application.
The files under `src-tauri` were created using as a template [this](https://github.com/Kitware/trame-tauri/tree/c27d437d4d1f1840ecf4373ce5fe726f1e7dd707/examples/01_tauri_ws/src-tauri) example.

## Building the bundle
1. Create a new virtual environment and install  the burnout application
```bash
python3 -m venv .venv
source .venv/bin/activate
# or for git bash on windows
source .venv/Scripts/activate

pip install -U pip
pip install  ../../
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
.\compile_sidecar.exe
cd ..\..\
```

4. Install tauri-cli(required only once)
```
cargo install tauri-cli
```

5. Run the build script
```bash
./create_linux_tauri.sh
# or for git bash on windows
./create_exe_tauri_bash.sh
```
on windows
```cmd
.\create_exe_tauri.bat
```

This creates installers that can be uploaded to a gitlab release. On windows, both .exe and .msi installers are created.
