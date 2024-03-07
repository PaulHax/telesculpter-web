import asyncio
from pathlib import Path
from tkinter import filedialog, Tk, TclError

from trame.app import get_server, asynchronous
from trame.decorators import TrameApp, change, controller, life_cycle
from trame.ui.quasar import QLayout
from trame.widgets import quasar, html, client, rca

from .assets import ASSETS
from .ui import VideoControls, FileMenu, ViewMenu, HelpMenu
from .utils import VideoAdapter

# make sure you source setup_KWIVER.sh from kwiver build directory
# before running the script to set the paths appropriately
from kwiver.vital.algo import VideoInput
from kwiver.vital.types import Timestamp
from kwiver.vital.types import tag_traits_by_tag


import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

VIDEO_ADAPTER_NAME = "active-video"

# this is for using native open file dialog
# https://stackoverflow.com/a/68230970
# def webview_file_dialog():
#     file = None
#     def open_file_dialog(w):
#         nonlocal file
#         try:
#             file = w.create_file_dialog(webview.OPEN_DIALOG)[0]
#         except TypeError:
#             pass  # user exited file dialog without picking
#         finally:
#             w.destroy()
#     #https://pywebview.flowrl.com/examples/open_file_dialog.html
#     window = webview.create_window("", hidden=True)
#     webview.start(open_file_dialog, window)
#     # file will either be a string or None
#     return file


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

        # kwiver data structures
        self.video_adapter = VideoAdapter(VIDEO_ADAPTER_NAME)
        self.video_source = VideoInput.create("ffmpeg")
        self.video_fps = 30

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

    def open_file(self, file_to_load=None):
        logger.debug("open file")
        if file_to_load is None:
            file_to_load = filedialog.askopenfile(
                title="Select video to load",
            )
            file_to_load = file_to_load.name
            # TODO not sure how to get string from TExtIO object from above
            # file_to_load = webview_file_dialog()

        logger.debug(f" => {file_to_load=}")
        self.video_source.open(file_to_load)
        self.state.video_loaded = True

        # Update state for UI
        self.state.video_n_frames = self.video_source.num_frames()
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
        elif msg == "menu:frame-num":
            self.get_number_of_frames()
        elif msg == "menu:ith-num":
            self.ith_frame()
        else:
            print(f"Desktop msg: {msg}")

    def exit(self):
        if self.ctrl.pywebview_window_call.exists():
            self.ctrl.pywebview_window_call("destroy")
        else:
            asynchronous.create_task(self.server.stop())

    def maximize(self):
        if self.ctrl.pywebview_window_call.exists():
            self.ctrl.pywebview_window_call("toggle_fullscreen")
        else:
            self.ctrl.toggle_fullscreen()

    # -------------------------------------------------------------------------
    # Menu handler
    # -------------------------------------------------------------------------

    def on_menu_file_open(self):
        self.open_file()

    def on_menu_file_export_meta(self):
        print("on_menu_file_export_meta")

    def on_menu_file_export_klv(self):
        print("on_menu_file_export_klv")

    def on_menu_file_remove_burnin(self):
        print("on_menu_file_remove_burnin")

    def on_menu_file_cancel(self):
        print("on_menu_file_cancel")

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
        while self.state.video_playing:
            await asyncio.sleep(
                1 / (self.video_fps * float(self.state.video_play_speed))
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
