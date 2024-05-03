import os
import asyncio
import logging
from pathlib import Path
from tkinter import filedialog, Tk, TclError

from trame.app import get_server, asynchronous
from trame.decorators import TrameApp, change, controller, life_cycle
from trame.ui.quasar import QLayout
from trame.widgets import quasar, html, client, rca

from .assets import ASSETS, KWIVER_CONFIG
from .ui import VideoControls, FileMenu, ViewMenu, HelpMenu
from .utils import VideoAdapter
from .video_importer import VideoImporter


import kwiver
import platform

if platform.system() == "Windows":
    BASE_PATH = str(Path(str(kwiver.__path__[0])))
    PLUGIN_PATH = Path(BASE_PATH + "\\lib\\kwiver\\plugins").resolve()
    os.environ["KWIVER_PLUGIN_PATH"] = str(PLUGIN_PATH)
    os.environ["PATH"] = (
        str(Path(BASE_PATH + "\\bin").resolve()) + os.pathsep + os.environ["PATH"]
    )
    os.environ["PATH"] = (
        str(Path(BASE_PATH + "..\kwiver.libs").resolve())
        + os.pathsep
        + os.environ["PATH"]
    )

from kwiver.vital.algo import VideoInput
from kwiver.vital.types import Timestamp
from kwiver.vital.config import read_config_file
from kwiver.vital.types import tag_traits_by_tag
from kwiver.vital import plugin_management
from kwiver.vital.config import read_config_file

vpm = plugin_management.plugin_manager_instance()
vpm.load_all_plugins()


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

VIDEO_ADAPTER_NAME = "active-video"

SUPPORTED_VIDEO_FORMATS = (
    ("MPEG Video", "*.mpeg"),
    ("MPG Video", "*.mpg"),
    ("MP4 Video", "*.mp4"),
    ("AVI Video", "*.avi"),
    ("Windows Media Video", "*.wmv"),
    ("QuickTime Video", "*.mov"),
    ("MPEG Transport Stream", "*.ts"),
    ("Image List", "*.txt"),
)


def pick_video_reader_config(path):
    if Path(path).suffix == ".txt":
        return KWIVER_CONFIG["gui_image_list_reader"]
    else:
        return KWIVER_CONFIG["gui_image_video_reader"]


@TrameApp()
class BurnOutApp:
    def __init__(self, server=None):
        self.server = get_server(server, client_type="vue3")
        self.web_only = False
        if self.server.hot_reload:
            self.server.controller.on_server_reload.add(self._build_ui)

        # Set state variable
        self.state.trame__title = "Burn Out"
        self.state.trame__favicon = ASSETS.favicon
        self.state.video_loaded = False
        self.state.ui_meta = []
        self.state.video_play_speed_label = ""

        # kwiver data structures
        self.video_adapter = VideoAdapter(VIDEO_ADAPTER_NAME)
        self.video_source = None
        self.video_fps = 30
        self.video_importer = VideoImporter()

        # Tk: native file dialog
        try:
            self.tk_root = Tk()
            self.tk_root.withdraw()
            self.tk_root.wm_attributes("-topmost", 1)
        except TclError:
            self.web_only = True

        self.server.cli.add_argument(
            "--data",
            help="Path to video",
            dest="data",
            default=None,
        )

        # Generate UI
        self._build_ui()

    # -------------------------------------------------------------------------
    # trame helpers
    # -------------------------------------------------------------------------

    @property
    def state(self):
        return self.server.state

    @property
    def ctrl(self):
        return self.server.controller

    @property
    def cli_args(self):
        args, _ = self.server.cli.parse_known_args()
        return args

    @life_cycle.server_ready
    def on_server_ready(self, **kwargs):
        # Load video if provided
        if self.cli_args.data:
            file_to_load = str(Path(self.cli_args.data).resolve())
            print("Load file", file_to_load)
            self.open_file(file_to_load)

        # Connect our video adapter
        self.ctrl.rc_area_register(self.video_adapter)

    @life_cycle.client_connected
    def on_client_connected(self, **kwargs):
        if self.state.video_loaded:
            # Force push image
            self.on_video_current_frame(1, True)

    # -------------------------------------------------------------------------
    # Desktop app helpers
    # -------------------------------------------------------------------------

    def save_metadata(self):
        logger.debug("menu:save_metadata")
        filename = filedialog.asksaveasfilename(
            filetypes=(
                ("Comma-Separated Values", "*.csv"),
                ("JavaScript Object Notation", "*.json"),
            ),
            defaultextension=".csv",
            title="Save Metadata",
        )
        if filename:
            self.video_importer.write(filename, KWIVER_CONFIG["gui_metadata_writer"])

    def save_klv(self):
        logger.debug("menu:save_klv")
        filename = filedialog.asksaveasfilename(
            filetypes=(("JavaScript Object Notation", "*.json"),),
            defaultextension=".json",
            title="Save KLV",
        )
        if filename:
            self.video_importer.write(filename, KWIVER_CONFIG["gui_klv_writer"])

    def open_file(self, file_to_load=None):
        logger.debug("open file")
        if file_to_load is None:
            file_to_load = filedialog.askopenfile(
                title="Select video to load",
                filetypes=(
                    (
                        "All supported Video Files",
                        " ".join(ext for _, ext in SUPPORTED_VIDEO_FORMATS),
                    ),
                    ("All files", "*.*"),
                    *SUPPORTED_VIDEO_FORMATS,
                ),
            )
            if file_to_load is None:
                return
            file_to_load = file_to_load.name

        logger.debug(f" => {file_to_load=}")
        if self.video_source:
            self.video_source.close()
            self.state.video_loaded = False
            self.video_adapter.clear()
        # start extractting metadata in separate process
        self.video_importer.run(file_to_load, pick_video_reader_config(file_to_load))

        with self.state as state:
            self.video_source = VideoInput.set_nested_algo_configuration(
                "video_reader", read_config_file(pick_video_reader_config(file_to_load))
            )
            self.video_source.open(file_to_load)
            state.video_loaded = True

            # Update state for UI
            state.video_current_frame = 1
            state.video_n_frames = self.video_source.num_frames()
            video_fps = self.video_source.frame_rate()
            if video_fps != -1.0:
                print(f"{video_fps=}")
                self.video_fps = video_fps

    @controller.set("on_desktop_msg")
    def desktop_msg(self, msg):
        logger.debug(f"{msg=}")
        if msg == "menu:open-video":
            self.open_file()
        elif msg == "menu:exit":
            self.exit()
        elif msg == "closing":
            self.video_importer.close()
        else:
            print(f"Desktop msg: {msg}")

    def exit(self):
        if self.ctrl.pywebview_window_call.exists():
            self.ctrl.pywebview_window_call("destroy")
        else:
            asynchronous.create_task(self.server.stop())
        self.video_importer.close()

    def maximize(self):
        if self.ctrl.pywebview_window_call.exists():
            self.ctrl.pywebview_window_call("toggle_fullscreen")
        else:
            self.ctrl.toggle_fullscreen()

    def cancel(self):
        self.video_importer.cancel()

    # -------------------------------------------------------------------------
    # Menu handler
    # -------------------------------------------------------------------------

    def on_menu_file_open(self):
        self.open_file()

    def on_menu_file_export_meta(self):
        self.save_metadata()

    def on_menu_file_export_klv(self):
        self.save_klv()

    def on_menu_file_remove_burnin(self):
        print("on_menu_file_remove_burnin")

    def on_menu_file_cancel(self):
        self.cancel()

    def on_menu_file_quit(self):
        self.exit()

    def on_menu_view_play(self):
        self.state.video_playing = not self.state.video_playing

    def on_menu_view_loop(self):
        self.state.video_play_loop = not self.state.video_play_loop

    def on_menu_view_reset(self):
        print("on_menu_view_reset")

    def on_menu_view_toggle_meta(self):
        self.state.show_view_metadata = not self.state.show_view_metadata
        if self.state.show_view_metadata:
            self.state.split_meta = 20
        else:
            self.state.split_meta = 0

    def on_menu_view_toggle_log(self):
        self.state.show_view_log = not self.state.show_view_log
        if self.state.show_view_log:
            self.state.split_log = 70
        else:
            self.state.split_log = 100

    def on_menu_help_manual(self):
        print("on_menu_help_manual")

    def on_menu_help_about(self):
        print("on_menu_help_about")

    # -------------------------------------------------------------------------
    # Async tasks
    # -------------------------------------------------------------------------

    async def _play(self):
        def speed_to_fps(speed):
            # see https://gitlab.kitware.com/kwiver/burnout/-/blob/master/gui/MainWindow.cxx?ref_type=heads#L1043
            return 2.0 ** (speed * 0.1)

        while self.state.video_playing:
            fps = speed_to_fps(self.state.video_play_speed)
            # self.state.video_play_speed_label = f"{round(fps)} fps" enable once we match the reported fps
            await asyncio.sleep(
                # 1 / (self.video_fps * tranform_play_speed(self.state.video_play_speed))
                1
                / fps
            )
            with self.state:
                if self.state.video_current_frame < self.state.video_n_frames:
                    self.state.video_current_frame += 1
                elif self.state.video_play_loop:
                    self.state.video_current_frame = 1
                else:
                    self.state.video_playing = False

    # -------------------------------------------------------------------------
    # Reactive state
    # -------------------------------------------------------------------------

    @change("video_current_frame", "video_loaded")
    def on_video_current_frame(self, video_current_frame, video_loaded, **kwargs):
        if not video_loaded:
            return

        video_current_frame = int(video_current_frame)
        ts = Timestamp()

        self.video_source.seek_frame(ts, video_current_frame)
        self.video_adapter.update_frame(self.video_source.frame_image())
        self.metadata = self.video_source.frame_metadata()
        self.state.ui_meta = [
            dict(name=tag_traits_by_tag(key).name(), value=value.as_string())
            for key, value in self.metadata[0]
        ]

    @change("video_playing")
    def on_video_playing(self, video_playing, **kwargs):
        if video_playing:
            asynchronous.create_task(self._play())

    # -------------------------------------------------------------------------
    # GUI
    # -------------------------------------------------------------------------

    def _build_ui(self, *args, **kwargs):
        with QLayout(self.server, view="hHh lpR fFf") as layout:
            client.Style("html { overflow: hidden; }")
            self.ctrl.toggle_fullscreen = client.JSEval(
                exec="""
                if (!window.document.fullscreenElement) {
                  window.document.documentElement.requestFullscreen();
                } else if (window.document.exitFullscreen) {
                  window.document.exitFullscreen();
                }
            """
            ).exec
            with quasar.QHeader():
                if self.web_only:
                    with quasar.QBar(classes="pywebview-drag-region"):
                        # html.Div("File", classes="cursor-pointer")
                        # html.Div("View", classes="cursor-pointer")
                        # html.Div("Help", classes="cursor-pointer")
                        # quasar.QSpace()
                        html.Img(src=ASSETS.logo, style="height: 20px")
                        quasar.QSpace()
                        if self.server.hot_reload:
                            quasar.QBtn(
                                dense=True,
                                flat=True,
                                icon="published_with_changes",
                                click=self.ctrl.on_server_reload,
                            )
                        quasar.QBtn(
                            dense=True,
                            flat=True,
                            icon="crop_square",
                            click=self.maximize,
                        )
                        quasar.QBtn(
                            dense=True, flat=True, icon="close", click=self.exit
                        )
                with quasar.QBar(
                    classes="bg-blue-grey-2 text-grey-10 q-pa-sm q-pl-md row items-center"
                ):
                    FileMenu(
                        self.on_menu_file_open,
                        self.on_menu_file_export_meta,
                        self.on_menu_file_export_klv,
                        self.on_menu_file_remove_burnin,
                        self.on_menu_file_cancel,
                        self.on_menu_file_quit,
                    )
                    ViewMenu(
                        self.on_menu_view_play,
                        self.on_menu_view_loop,
                        self.on_menu_view_reset,
                        self.on_menu_view_toggle_meta,
                        self.on_menu_view_toggle_log,
                    )
                    HelpMenu(
                        self.on_menu_help_manual,
                        self.on_menu_help_about,
                    )

            with quasar.QPageContainer():
                with quasar.QPage():
                    with quasar.QSplitter(
                        v_model=("split_log", 100),
                        horizontal=True,
                        style="position: absolute; top: 0; left: 0; bottom: 0; right: 0;",
                        limits=([50, 100],),
                        separator_style="opacity: 0;",
                    ):
                        with html.Template(raw_attrs=["v-slot:before"]):
                            with quasar.QSplitter(
                                v_model=("split_meta", 0),
                                style="position: absolute; top: 0; left: 0; bottom: 0; right: 0;",
                                limits=([0, 50],),
                                separator_style="opacity: 0;",
                            ):
                                with html.Template(raw_attrs=["v-slot:before"]):
                                    with quasar.QCard(
                                        flat=True,
                                        bordered=True,
                                        v_show=("show_view_metadata", False),
                                        classes="absolute column justify-between content-stretch",
                                        style="top: 0.1rem; left: 0.1rem; bottom: 0.1rem; right: 0.1rem;",
                                    ):
                                        quasar.QTable(
                                            style="width: 100%; height: 100%;",
                                            dense=True,
                                            flat=True,
                                            bordered=True,
                                            hide_header=True,
                                            hide_bottom=True,
                                            separator="cell",
                                            rowsPerPage=(10000,),
                                            rows=("ui_meta", []),
                                            columns=(
                                                "ui_cols",
                                                [
                                                    dict(
                                                        name="name",
                                                        label="Key",
                                                        field="name",
                                                        classes="text-weight-medium",
                                                    ),
                                                    dict(
                                                        name="value",
                                                        label="Value",
                                                        field="value",
                                                        classes="ellipsis",
                                                        headerStyle="width: 45%",
                                                        align="left",
                                                    ),
                                                ],
                                            ),
                                            row_key="name",
                                        )

                                with html.Template(raw_attrs=["v-slot:after"]):
                                    with quasar.QCard(
                                        flat=True,
                                        bordered=True,
                                        classes="absolute column justify-between content-stretch",
                                        style="top: 0.1rem; left: 0.1rem; bottom: 0.1rem; right: 0.1rem;",
                                    ):
                                        with html.Div(
                                            classes="col justify-center items-center q-pa-xs"
                                        ):
                                            rca.RawImageDisplayArea(
                                                name=VIDEO_ADAPTER_NAME,
                                                style="object-fit: contain;",
                                                classes="fit",
                                            )
                                        VideoControls(classes="q-px-md")

                        with html.Template(raw_attrs=["v-slot:after"]):
                            with quasar.QCard(
                                flat=True,
                                bordered=True,
                                v_show=("show_view_log", False),
                                classes="absolute column justify-between content-stretch",
                                style="top: 0.1rem; left: 0.1rem; bottom: 0.1rem; right: 0.1rem;",
                            ):
                                html.Div("log")
            self.ui = layout
