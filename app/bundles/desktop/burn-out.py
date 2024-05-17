import multiprocessing
import os
import sys

from burn_out.app.main import main

# redirect stdout/stderr to avoid issues when running on windows without a console
# see https://pyinstaller.org/en/latest/common-issues-and-pitfalls.html#sys-stdin-sys-stdout-and-sys-stderr-in-noconsole-windowed-applications-windows-only
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
