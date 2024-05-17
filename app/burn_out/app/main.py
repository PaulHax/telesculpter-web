from .core import BurnOutApp


def main(server=None, **kwargs):
    app = BurnOutApp(server)
    app.server.start(**kwargs)

if __name__ == "__main__":
    main()
