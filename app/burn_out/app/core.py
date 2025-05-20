import asyncio
import logging
from io import StringIO
from pathlib import Path

from trame.app import get_server, asynchronous
from trame.decorators import TrameApp, change, life_cycle
from trame.ui.quasar import QLayout
from trame.widgets import quasar, html, client, rca, tauri

from .assets import ASSETS, KWIVER_CONFIG
from .ui import VideoControls, FileMenu, ViewMenu, HelpMenu, AboutDialog
from .utils import VideoAdapter
from .video_importer import VideoImporter
from .dialogs import TclTKDialog, TauriDialog

from kwiver.vital.algo import VideoInput
from kwiver.vital.types import Timestamp
from kwiver.vital.config import read_config_file
from kwiver.vital.types import tag_traits_by_tag
from kwiver.vital import plugin_management
from kwiver.vital import vital_logging

vpm = plugin_management.plugin_manager_instance()
vpm.load_all_plugins()


#  anything written to objects of this class will be also appended to
#  log_stream state variable
class RedirectedStringIO(StringIO):
    def __init__(self, state, *args):
        super().__init__(*args)
        self.state = state
        # don't buffer
        self.write_through = True

    def write(self, msg):
        self.state.log_stream += msg
        v = super().write(msg)
        return v


logger = vital_logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


VIDEO_ADAPTER_NAME = "active-video"


def pick_video_reader_config(path):
    if Path(path).suffix == ".txt":
        return KWIVER_CONFIG["gui_image_list_reader"]
    else:
        return KWIVER_CONFIG["gui_image_video_reader"]


@TrameApp()
class BurnOutApp:
    def __init__(self, server=None):
        self.server = get_server(server, client_type="vue3")
        self.use_tk = False
        if self.server.hot_reload:
            self.server.controller.on_server_reload.add(self._build_ui)

        # Set state variable
        self.state.trame__title = "Burn Out"
        self.state.trame__favicon = ASSETS.favicon
        self.state.video_loaded = False
        self.state.ui_meta = []
        self.state.video_play_speed_label = ""
        self.state.log_stream = ""
        self.iostream = RedirectedStringIO(self.state)
        logging.basicConfig(stream=self.iostream)

        # kwiver data structures
        self.video_adapter = VideoAdapter(
            VIDEO_ADAPTER_NAME, on_streamer_set=self._on_video_adapter_ready
        )
        self.video_source = None
        self.video_fps = 30
        self.video_previous_frame_index = -1
        self.video_importer = VideoImporter()

        self.server.cli.add_argument(
            "--use-tk",
            help="Use tcl/tk for file pickers. Useful if working with the web version",
            action="store_true",
        )

        self.server.cli.add_argument(
            "--data",
            help="Path to video",
            dest="data",
            default=None,
        )

        if self.cli_args.use_tk:
            self.dialog = TclTKDialog()
        else:
            self.dialog = TauriDialog()

        # Generate UI
        self._build_ui()

    def _on_video_adapter_ready(self):
        self.state.video_adapter_ready = True

    # -------------------------------------------------------------------------
    # tauri helpers
    # -------------------------------------------------------------------------

    @life_cycle.server_ready
    def _tauri_ready(self, **_):
        logger.debug("_ready")
        print(f"tauri-server-port={self.server.port}", flush=True)

    @life_cycle.client_connected
    def _tauri_show(self, **_):
        print("tauri-client-ready", flush=True)

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
            logger.debug("Load file %s", file_to_load)
            self.open_file(file_to_load)

        # Connect our video adapter
        self.ctrl.rc_area_register(self.video_adapter)

    @life_cycle.client_connected
    def on_client_connected(self, **kwargs):
        if self.state.video_loaded:
            # Force push image
            self.on_video_current_frame(1, True)

    @life_cycle.client_exited
    def on_client_exited(self, **kwargs):
        # make sure we terminate the secondary process
        self.video_importer.close()

    @life_cycle.server_exited
    def on_server_exited(self, **kwargs):
        # make sure we terminate the secondary process
        self.video_importer.close()

    # -------------------------------------------------------------------------
    # Desktop app helpers
    # -------------------------------------------------------------------------

    def save_metadata(self, filename=None):
        if filename:
            self.video_importer.write(filename, KWIVER_CONFIG["gui_metadata_writer"])

    def save_klv(self, filename=None):
        if filename:
            self.video_importer.write(filename, KWIVER_CONFIG["gui_klv_writer"])

    def open_file(self, file_to_load=None):
        if file_to_load is None:
            return
        logger.debug("open file")
        logger.debug(f" => {file_to_load=}")
        if self.video_source:
            self.video_source.close()
            self.state.video_loaded = False
            self.video_adapter.clear()
            self.video_previous_frame_index = -1
        # start extracting metadata in separate process
        self.video_importer.run(file_to_load, pick_video_reader_config(file_to_load))

        with self.state as state:
            self.video_source = VideoInput.set_nested_algo_configuration(
                "video_reader",
                read_config_file(pick_video_reader_config(file_to_load)),
                None,
            )
            self.video_source.open(file_to_load)
            state.video_loaded = True

            # Update state for UI
            state.video_current_frame = 1
            state.video_n_frames = self.video_source.num_frames()
            video_fps = self.video_source.frame_rate()
            if video_fps != -1.0:
                self.video_fps = video_fps

    def exit(self):
        asynchronous.create_task(self.server.stop())
        self.video_importer.close()

    def cancel(self):
        self.video_importer.cancel()

    # -------------------------------------------------------------------------
    # Menu handler
    # -------------------------------------------------------------------------
    async def dialog_open_video(self):
        file_path = await self.dialog.open_video()
        self.open_file(file_path)

    async def dialog_save_metadata(self):
        file_path = await self.dialog.save_metadata()
        self.save_metadata(file_path)

    async def dialog_save_klv(self):
        file_path = await self.dialog.save_klv()
        self.save_klv(file_path)

    def on_menu_file_open(self):
        logger.debug("menu:file_open")
        asynchronous.create_task(self.dialog_open_video())

    def on_menu_file_export_meta(self):
        logger.debug("menu:export_metadata")
        asynchronous.create_task(self.dialog_save_metadata())

    def on_menu_file_export_klv(self):
        logger.debug("menu:export_klv")
        asynchronous.create_task(self.dialog_save_klv())

    def on_menu_file_remove_burnin(self):
        logger.debug("on_menu_file_remove_burnin")

    def on_menu_file_cancel(self):
        self.cancel()

    def on_menu_file_quit(self):
        self.exit()

    def on_menu_view_play(self):
        self.state.video_playing = not self.state.video_playing

    def on_menu_view_loop(self):
        self.state.video_play_loop = not self.state.video_play_loop

    def on_menu_view_reset(self):
        logger.debug("on_menu_view_reset")

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
        logger.debug("on_menu_help_manual")

    def on_menu_help_about(self):
        self.state.show_about_dialog = True

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
            with self.state:
                if self.state.video_current_frame < self.state.video_n_frames:
                    self.state.video_current_frame += 1
                elif self.state.video_play_loop:
                    self.state.video_current_frame = 1
                else:
                    self.state.video_playing = False
            await asyncio.sleep(1.0 / fps)

    # -------------------------------------------------------------------------
    # Reactive state
    # -------------------------------------------------------------------------

    @change("video_current_frame", "video_loaded", "video_adapter_ready")
    def on_video_current_frame(self, video_current_frame, video_loaded, **kwargs):
        if not video_loaded or not self.state.video_adapter_ready:
            return

        video_current_frame = int(video_current_frame)
        ts = Timestamp()

        if self.video_previous_frame_index != video_current_frame:
            # step through next frames if the requested frame is just a few ahead
            if (
                self.video_previous_frame_index < video_current_frame
                and self.video_previous_frame_index + 10 > video_current_frame
            ):
                while (
                    self.video_source.next_frame(ts)
                    and ts.get_frame() < video_current_frame
                ):
                    continue
            else:
                # otherwise seek to the requested frame
                self.video_source.seek_frame(ts, video_current_frame)

        self.video_adapter.update_frame(self.video_source.frame_image())
        self.video_previous_frame_index = video_current_frame
        self.metadata = self.video_source.frame_metadata()
        self.state.ui_meta = [
            dict(name=tag_traits_by_tag(key).name(), value=value.as_string())
            for key, value in self.metadata[0]
        ]
        self.state.flush()  # makes metadata show in the table when using --data CLI arg

    @change("video_playing")
    def on_video_playing(self, video_playing, **kwargs):
        if video_playing:
            asynchronous.create_task(self._play())

    # -------------------------------------------------------------------------
    # GUI
    # -------------------------------------------------------------------------

    def _build_ui(self, *args, **kwargs):
        with QLayout(self.server, view="hHh lpR fFf") as layout:
            if not self.cli_args.use_tk:
                with tauri.Dialog() as dialog:
                    self.dialog.open_handler = dialog.open
                    self.dialog.save_handler = dialog.save
            client.Style(
                """
                /* remove scrollbars  from main window */
                html { overflow: hidden; }

                /* remove transition delay/effect from video srub transition */ 
                .no-transition.q-slider--inactive .q-slider__selection {
                    transition: none !important;
                  }

                .no-transition.q-slider--inactive .q-slider__thumb--h {
                    transition: none !important;
                }
            """
            )
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
            AboutDialog()
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
                                v_model=("split_meta", 20),
                                style="position: absolute; top: 0; left: 0; bottom: 0; right: 0;",
                                limits=([0, 50],),
                                separator_style="opacity: 0;",
                            ):
                                with html.Template(raw_attrs=["v-slot:before"]):
                                    with quasar.QCard(
                                        flat=True,
                                        bordered=True,
                                        v_show=("show_view_metadata", True),
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
                                            rows_per_page_options=0,
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
                                html.Div(
                                    style="white-space: pre-line;",
                                    v_text=("log_stream", "Empty"),
                                )
            self.ui = layout
