from tkinter import filedialog, Tk
import webview

from trame.app import get_server, asynchronous
from trame.decorators import TrameApp, change, controller
from trame.ui.quasar import QLayout
from trame.widgets import quasar, html, client

from .assets import ASSETS

import logging
logger = logging.getLogger(__name__)

# make sure you source setup_KWIVER.sh from kwiver build directory before running the script to set the paths appropriately
from kwiver.vital.algo import VideoInput
from kwiver.vital.types import Timestamp

video_source = VideoInput.create("ffmpeg")


# this is for using native open file dialog
# https://stackoverflow.com/a/68230970
def webview_file_dialog():
    file = None
    def open_file_dialog(w):
        nonlocal file
        try:
            file = w.create_file_dialog(webview.OPEN_DIALOG)[0]
        except TypeError:
            pass  # user exited file dialog without picking
        finally:
            w.destroy()
    #https://pywebview.flowrl.com/examples/open_file_dialog.html
    window = webview.create_window("", hidden=True)
    webview.start(open_file_dialog, window)
    # file will either be a string or None
    return file



@TrameApp()
class BurnOutApp:
    def __init__(self, server=None):
        self.server = get_server(server, client_type="vue3")
        if self.server.hot_reload:
            self.server.controller.on_server_reload.add(self._build_ui)
        self._build_ui()

        # Set state variable
        self.state.trame__title = "Burn Out"
        self.state.trame__favicon = ASSETS.favicon

        # Tk handling
        self.tk_root = Tk()
        self.tk_root.withdraw()
        self.tk_root.wm_attributes("-topmost", 1)

    @property
    def state(self):
        return self.server.state

    @property
    def ctrl(self):
        return self.server.controller

    # -------------------------------------------------------------------------
    # Desktop app helpers
    # -------------------------------------------------------------------------

    def open_file(self):
        logger.debug("open file")
        #file_to_load = filedialog.askopenfile(
        #    title="Select video to load",
        #)
        # TODO not sure how to get string from TExtIO object from above
        file_to_load = webview_file_dialog()
        print(f"{file_to_load=}")
        video_source.open(str(file_to_load))

    def get_number_of_frames(self):
        logger.debug("get_number of frames")
        print(video_source.num_frames())
    
    def ith_frame(self):
        logger.debug("ith frame")
        print(video_source.num_frames())
        ts = Timestamp()
        k = 5

        video_source.seek_frame(ts,k)
        image = video_source.frame_image()
        # see kwiver/python/kwiver/vital/types/image_container.cxx for full API
        print(image)
        print(image.size())
        print(image.width())
        print(image.asarray())
      

    @controller.set("on_desktop_msg")
    def desktop_msg(self, msg):
        logger.debug(f"{msg=}")
        if msg == "menu:open-video":
            self.open_file()
        elif msg == "menu:exit":
            self.exit()
        elif msg =="menu:frame-num":
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
                with quasar.QBar(classes="pywebview-drag-region"):
                    html.Div("File", classes="cursor-pointer")
                    html.Div("View", classes="cursor-pointer")
                    html.Div("Help", classes="cursor-pointer")
                    quasar.QSpace()
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
                        dense=True, flat=True, icon="crop_square", click=self.maximize
                    )
                    quasar.QBtn(dense=True, flat=True, icon="close", click=self.exit)

            with quasar.QPageContainer():
                html.Div("Content 2")

            self.ui = layout
