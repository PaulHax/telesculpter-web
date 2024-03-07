import multiprocessing

from burn_out.app.main import app

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app()
