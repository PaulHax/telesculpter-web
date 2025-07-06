import multiprocessing
import os
import sys

from burn_out.app.main import main


def _setup_kwiver_env_for_bundle():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # sys._MEIPASS is the path to the temporary directory where the app is unpacked
        bundle_dir = sys._MEIPASS  # e.g., src-tauri/server/_internal

        kwiver_plugins_path = os.path.join(bundle_dir, "lib", "kwiver", "plugins")
        os.environ["KWIVER_PLUGIN_PATH"] = kwiver_plugins_path

        kwiver_config_path = os.path.join(bundle_dir, "kwiver_config")
        os.environ["KWIVER_CONFIG_PATH"] = kwiver_config_path

        os.environ["KWIVER_PYTHON_PLUGIN_PATH"] = ""

        print(
            f"Frozen app. KWIVER_PLUGIN_PATH set to: {os.environ.get('KWIVER_PLUGIN_PATH')}"
        )
        print(
            f"Frozen app. KWIVER_CONFIG_PATH set to: {os.environ.get('KWIVER_CONFIG_PATH')}"
        )


_setup_kwiver_env_for_bundle()

# redirect stdout/stderr to avoid issues when running on windows without a console
# see https://pyinstaller.org/en/latest/common-issues-and-pitfalls.html#sys-stdin-sys-stdout-and-sys-stderr-in-noconsole-windowed-applications-windows-only
if sys.platform == "win32":  # Only apply this on Windows
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
