from .core import BurnOutApp


def main(server=None, **kwargs):
    app = BurnOutApp(server)
    app.server.start(on_message=app.server.controller.on_desktop_msg, **kwargs)


def app():
    menu = [
        (
            "File",
            [
                ("Open video", "open-video"),
                "---",
                ("Exit", "exit"),
            ],
        ),
    ]

    main(exec_mode="desktop", frameless=False, easy_drag=False, menu=menu)


if __name__ == "__main__":
    main()
