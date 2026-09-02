"""App-wide constants and user-facing filesystem locations."""

import os
import sys
from pathlib import Path

APP_NAME = "Map Quiz Maker"

IMG_WIDTH_CM = 17.78  # matches the fixed image width (7in) baked into the Typst worksheet layout

# The folder quizzes are written to when the user hasn't chosen one via
# "Save As". Deliberately an absolute path under the user's home rather than
# a bare relative "output" -- a relative path resolves against the process
# working directory, so launching from a desktop shortcut or a file manager
# scattered finished quizzes into folders the user had no way to find.
DEFAULT_OUTPUT_DIR_NAME = "Map Quizzes"


def default_output_dir() -> Path:
    """The out-of-the-box quiz destination: ~/Documents/Map Quizzes.

    Falls back to the home directory itself on the rare setup with no
    Documents folder, so the path is always somewhere the user can reach.
    """
    home = Path.home()
    documents = home / "Documents"
    parent = documents if documents.is_dir() else home
    return parent / DEFAULT_OUTPUT_DIR_NAME


def settings_path() -> Path:
    """Location of the small JSON file remembering the last-used folder."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "map-quiz-maker" / "settings.json"
