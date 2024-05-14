from .core import BurnOutApp


def main(server=None, **kwargs):
    app = BurnOutApp(server)
    app.server.start(**kwargs)


def app():
    main(frameless=False, easy_drag=False)


if __name__ == "__main__":
    main()
