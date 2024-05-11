# Desktop

This relies on [pyinstaller](https://pyinstaller.org/en/stable/) and tauri (https://tauri.app/) to bundle your trame application into a standalone desktop application.
The files under `src-tauri` were created using as a template [this](https://github.com/Kitware/trame-tauri/tree/c27d437d4d1f1840ecf4373ce5fe726f1e7dd707/examples/01_tauri_ws/src-tauri) example.

## Building the bundle
1. Create a new virtual environment and install  the burnout application
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install  ../
```
2. Add pyinstaller and additional packages required for bundling.
```bash
pip install -r ./requirements.txt
```
or
```bash
pip install -r ./requirements_linux.txt
```

3. Since Tauri is written in Rust, let's get setup with its dev environment.

```bash
# Install rust
curl --proto '=https' --tlsv1.2 https://sh.rustup.rs -sSf | sh

# Enable rust within shell
. "$HOME/.cargo/env"

# Install tauri-cli
cargo install tauri-cli
```

4. Run the build script
```bash
./create_linux_tauri.sh
```
