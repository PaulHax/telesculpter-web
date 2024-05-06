# custom pyinstaller hook for kwiver
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_dynamic_libs

# the default value for linux is  "lib*.so" however wkiver plugins are of the form "kwiver*.so"
binaries = collect_dynamic_libs("kwiver", search_patterns=["*.dll", "*.dylib", "*.so"])
hiddenimports = ["kwiver", "kwiver.vital.plugins", "kwiver.vital.plugins.discovery"]
datas = collect_data_files("kwiver")
