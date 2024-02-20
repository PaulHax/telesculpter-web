import asyncio
from pathlib import Path
from tkinter import filedialog, Tk, TclError

from trame.app import get_server, asynchronous
from trame.decorators import TrameApp, change, controller, life_cycle
from trame.ui.quasar import QLayout
from trame.widgets import quasar, html, client, rca

from .assets import ASSETS
from .ui import VideoControls
from .utils import VideoAdapter

# make sure you source setup_KWIVER.sh from kwiver build directory
# before running the script to set the paths appropriately
from kwiver.vital.algo import VideoInput
from kwiver.vital.types import Timestamp


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
            file_to_load = file_to_load.read()
            # TODO not sure how to get string from TExtIO object from above
            # file_to_load = webview_file_dialog()

        logger.debug(f" => {file_to_load=}")
        self.video_source.open(file_to_load)
        self.state.video_loaded = True

        # Update state for UI
        self.state.video_n_frames = self.video_source.num_frames()

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

            with quasar.QPageContainer():
                with quasar.QPage():
                    with quasar.QCard(
                        classes="absolute column justify-between content-stretch",
                        style="top: 1rem; left: 1rem; bottom: 1rem; right: 1rem;",
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

            self.ui = layout
