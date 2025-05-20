# custom pyinstaller hook for kwiver
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_dynamic_libs
import os

# the default value for linux is  "lib*.so" however kwiver plugins are of the form "kwiver*.so"
binaries = collect_dynamic_libs(
    "kwiver", search_patterns=["*.dll", "*.dylib", "*.so", "*.pyd"]
)
hiddenimports = [
    "kwiver",
    "kwiver.vital.plugins",
    "kwiver.vital.plugins.discovery",
    "kwiver.vital.tests",
]
datas = collect_data_files("kwiver")

# Destination directory within the PyInstaller bundle for external KWIVER plugins
kwiver_plugins_bundle_dest = "lib/kwiver/plugins"

kwiver_plugin_env_path = os.environ.get("KWIVER_PLUGIN_PATH")
kwiver_plugins_source_paths_to_process = []  # Stores absolute paths

if kwiver_plugin_env_path:
    print(
        f"PyInstaller hook-kwiver.py: Using KWIVER_PLUGIN_PATH='{kwiver_plugin_env_path}'"
    )
    path_segments = kwiver_plugin_env_path.split(os.pathsep)
    for segment in path_segments:
        stripped_segment = segment.strip()
        if not stripped_segment:  # Skip empty segments
            continue

        # Directly add the path without checking if it's a valid directory
        abs_segment_path = os.path.abspath(stripped_segment)
        if (
            abs_segment_path not in kwiver_plugins_source_paths_to_process
        ):  # Avoid duplicates
            kwiver_plugins_source_paths_to_process.append(abs_segment_path)
            print(
                f"PyInstaller hook-kwiver.py: Adding KWIVER plugin source directory: {abs_segment_path}"
            )
else:
    print(
        "PyInstaller hook-kwiver.py: KWIVER_PLUGIN_PATH environment variable not set or empty. No external plugins will be added via this variable."
    )

if not kwiver_plugins_source_paths_to_process:
    print(
        "PyInstaller hook-kwiver.py: No KWIVER plugin source directories were identified from KWIVER_PLUGIN_PATH. Application may not function correctly if these are required."
    )
else:
    for src_path in kwiver_plugins_source_paths_to_process:
        # Add the source directory path and the target directory name to datas.
        # PyInstaller will copy the contents of src_path into kwiver_plugins_bundle_dest within the bundle.
        datas.append((src_path, kwiver_plugins_bundle_dest))  # kwiver
        print(
            f"PyInstaller hook-kwiver.py: Added entry to copy contents from '{src_path}' to bundle destination '{kwiver_plugins_bundle_dest}'"
        )
