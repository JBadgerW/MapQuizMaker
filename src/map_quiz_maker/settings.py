"""Persistence for the handful of preferences that should outlive a session.

Deliberately best-effort: a settings file that is missing, unreadable, or
corrupt must never stop the app from starting or block a build, so every
operation here degrades to the default rather than raising.
"""

import json
from pathlib import Path

from map_quiz_maker.config import default_output_dir, settings_path

_LAST_OUTPUT_DIR = "last_output_dir"


def _read() -> dict:
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write(data: dict) -> None:
    path = settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass  # Preferences are a convenience; losing them is not worth an error.


def get_output_dir() -> Path:
    """The folder to write quizzes into: last used, else the default."""
    remembered = _read().get(_LAST_OUTPUT_DIR)
    if isinstance(remembered, str) and remembered:
        candidate = Path(remembered)
        if candidate.is_dir():
            return candidate
    return default_output_dir()


def set_output_dir(path) -> None:
    """Remembers `path` as the destination for the next build."""
    data = _read()
    data[_LAST_OUTPUT_DIR] = str(Path(path))
    _write(data)
