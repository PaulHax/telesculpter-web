from tkinter import filedialog, Tk

from trame.app import get_server, asynchronous
from trame.decorators import TrameApp, change, controller
from trame.ui.quasar import QLayout
from trame.widgets import quasar, html, client

from .assets import ASSETS


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
        file_to_load = filedialog.askopenfile(
            title="Select video to load",
        )
        print(f"{file_to_load=}")

    @controller.set("on_desktop_msg")
    def desktop_msg(self, msg):
        if msg == "menu:open-video":
            self.open_file()
        elif msg == "menu:exit":
            self.exit()
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
