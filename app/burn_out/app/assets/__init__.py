from pathlib import Path
from trame.assets.local import LocalFileManager

ASSETS = LocalFileManager(str(Path(__file__).parent.resolve()))
ASSETS.url("logo", "logo.png")
ASSETS.url("favicon", "favicon.png")
