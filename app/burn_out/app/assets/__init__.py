from pathlib import Path
from trame.assets.local import LocalFileManager

ASSETS = LocalFileManager(str(Path(__file__).parent.resolve()))
ASSETS.url("logo", "logo.png")
ASSETS.url("favicon", "favicon.png")
KWIVER_CONFIG_DIR = Path(__file__).with_name("config").resolve()
KWIVER_CONFIG = {f.stem: str(f) for f in KWIVER_CONFIG_DIR.glob("*.conf")}
