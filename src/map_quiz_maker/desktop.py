"""Handing a finished file back to the desktop environment.

Opening a PDF in the system viewer and revealing a folder in the file
manager are the two things that let the completion dialog answer "where did
my quiz go?" concretely rather than by printing a path the user then has to
go find themselves.
"""

import os
import subprocess
import sys
from pathlib import Path


def _launch(args: list[str]) -> bool:
    try:
        subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def open_file(path) -> bool:
    """Opens `path` in whatever application the OS associates with it.

    Returns False if no handler could be launched, so the caller can say so
    instead of leaving the user staring at a button that did nothing.
    """
    path = Path(path)
    if not path.exists():
        return False

    if sys.platform == "win32":
        try:
            os.startfile(path)  # the documented Windows way to open a file
        except OSError:
            return False
        return True
    if sys.platform == "darwin":
        return _launch(["open", str(path)])
    return _launch(["xdg-open", str(path)])


def show_in_folder(path) -> bool:
    """Reveals `path` in the file manager, selecting it where supported.

    Falls back to opening the containing folder, which is the useful part of
    the gesture even when the file manager can't select a specific file.
    """
    path = Path(path)
    folder = path.parent if path.parent.exists() else path

    if sys.platform == "win32":
        if path.exists() and _launch(["explorer", f"/select,{path}"]):
            return True
        return open_file(folder)
    if sys.platform == "darwin":
        if path.exists() and _launch(["open", "-R", str(path)]):
            return True
        return open_file(folder)
    return open_file(folder)
