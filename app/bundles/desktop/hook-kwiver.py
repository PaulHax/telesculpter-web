# custom pyinstaller hook for kwiver
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_dynamic_libs

# the default value for linux is  "lib*.so" however kwiver plugins are of the form "kwiver*.so"
binaries = collect_dynamic_libs(
    "kwiver", search_patterns=["*.dll", "*.dylib", "*.so", "*.pyd"]
)
print(
    f"PyInstaller hook-kwiver.py: Found {len(binaries)} KWIVER binaries before filtering"
)
# Filter out GUI applets that cause X11 dependency issues
binaries = [(src, dest) for src, dest in binaries if "vital_applets" not in src]
print(
    f"PyInstaller hook-kwiver.py: Found {len(binaries)} KWIVER binaries after filtering"
)
hiddenimports = [
    "kwiver",
    "kwiver.vital.plugins",
    "kwiver.vital.plugins.discovery",
    "kwiver.vital.tests",
]
datas = collect_data_files("kwiver")
