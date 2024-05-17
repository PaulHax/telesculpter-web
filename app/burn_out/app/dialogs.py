from typing import Optional


class BurnoutDialog:
    """Abstract interface for the dialogs used in Burnout"""

    async def open_video(self) -> Optional[str]:
        raise NotImplementedError

    async def save_metadata(self) -> Optional[str]:
        raise NotImplementedError

    async def save_klv(self) -> Optional[str]:
        raise NotImplementedError

    @property
    def open_handler(self):
        pass

    @property
    def save_handler(self):
        pass

    @open_handler.setter
    def open_handler(self, handler):
        pass

    @save_handler.setter
    def save_handler(self, handler):
        pass


class TauriDialog(BurnoutDialog):
    """BurnoutDialog that utilize native toolkits via Tauri
    Note: This work only when the application is bundled by"""

    def __init__(self) -> None:
        self.SUPPORTED_VIDEO_FORMATS = (
            {"name": "MPEG Video (mpeg)", "extensions": ["mpeg"]},
            {"name": "MPG Video (mpg)", "extensions": ["mpg"]},
            {"name": "MP4 Video (mp4)", "extensions": ["mp4"]},
            {"name": "AVI Video (avi)", "extensions": ["avi"]},
            {"name": "Windows Media Video (wmv)", "extensions": ["wmv"]},
            {"name": "QuickTime Video (mov)", "extensions": ["mov"]},
            {"name": "MPEG Transport Stream (ts)", "extensions": ["ts"]},
            {"name": "Image List (txt)", "extensions": ["txt"]},
        )
        self._open_handler = None
        self._save_handler = None

    @property
    def open_handler(self):
        return self._open_handler

    @open_handler.setter
    def open_handler(self, handler):
        self._open_handler = handler

    @property
    def save_handler(self):
        return self._save_handler

    @save_handler.setter
    def save_handler(self, handler):
        self._save_handler = handler

    async def open_video(self) -> str:
        title = "Select video to load"
        filters = [
            {
                "name": "All supported Video Files",
                "extensions": [
                    item["extensions"][0] for item in self.SUPPORTED_VIDEO_FORMATS
                ],
            },
            {"name": "All files", "extensions": ["*"]},
            *self.SUPPORTED_VIDEO_FORMATS,
        ]
        return await self.open_handler(title, filters=filters)

    async def save_metadata(self) -> str:
        title = "Save Metadata"
        filters = [
            {"name": "Comma-Separated Values (csv)", "extensions": ["csv"]},
            {"name": "JavaScript Object Notation (json)", "extensions": ["json"]},
        ]
        return await self.save_handler(title=title, filters=filters)

    async def save_klv(self) -> str:
        title = "Save KLV"
        filters = [
            {"name": "JavaScript Object Notation (json)", "extensions": ["json"]},
        ]
        return await self.save_handler(title=title, filters=filters)


class TclTKDialog(BurnoutDialog):
    """BurnoutDialog that utilizes Tcl/Tk toolkit.  Usable inside and outside
    the bundles. Usefaull for debugging without recreating bundle."""

    def __init__(self):
        from tkinter import Tk

        self.tk_root = Tk()
        self.tk_root.withdraw()
        self.tk_root.wm_attributes("-topmost", 1)
        self.SUPPORTED_VIDEO_FORMATS = (
            ("MPEG Video", "*.mpeg"),
            ("MPG Video", "*.mpg"),
            ("MP4 Video", "*.mp4"),
            ("AVI Video", "*.avi"),
            ("Windows Media Video", "*.wmv"),
            ("QuickTime Video", "*.mov"),
            ("MPEG Transport Stream", "*.ts"),
            ("Image List", "*.txt"),
        )

    async def open_video(self) -> str:
        from tkinter import filedialog

        filename = filedialog.askopenfilename(
            title="Select video to load",
            filetypes=(
                (
                    "All supported Video Files",
                    " ".join(ext for _, ext in self.SUPPORTED_VIDEO_FORMATS),
                ),
                ("All files", "*.*"),
                *self.SUPPORTED_VIDEO_FORMATS,
            ),
        )
        if len(filename) == 0:
            return None
        else:
            return filename

    async def save_metadata(self) -> str:
        from tkinter import filedialog

        filename = filedialog.asksaveasfilename(
            filetypes=(
                ("Comma-Separated Values", "*.csv"),
                ("JavaScript Object Notation", "*.json"),
            ),
            defaultextension=".csv",
            title="Save Metadata",
        )
        if len(filename) == 0:
            return None
        else:
            return filename

    async def save_klv(self) -> str:
        from tkinter import filedialog

        filename = filedialog.asksaveasfilename(
            filetypes=(("JavaScript Object Notation", "*.json"),),
            defaultextension=".json",
            title="Save KLV",
        )
        if len(filename) == 0:
            return None
        else:
            return filename
