"""Persistence for the handful of preferences that should outlive a session.

Deliberately best-effort: a settings file that is missing, unreadable, or
corrupt must never stop the app from starting or block a build, so every
operation here degrades to the default rather than raising.
"""

import json
from pathlib import Path

from map_quiz_maker.config import default_output_dir, settings_path

_LAST_OUTPUT_DIR = "last_output_dir"
_RECENT_FILES = "recent_files"

MAX_RECENT_FILES = 8


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


def get_recent_files() -> list[Path]:
    """Recently opened or saved quizzes, newest first.

    Files that have since been moved or deleted are filtered out rather than
    offered as menu entries that fail when clicked.
    """
    remembered = _read().get(_RECENT_FILES)
    if not isinstance(remembered, list):
        return []
    paths = []
    for entry in remembered:
        if isinstance(entry, str) and entry:
            candidate = Path(entry)
            if candidate.is_file():
                paths.append(candidate)
    return paths[:MAX_RECENT_FILES]


def remember_recent_file(path) -> None:
    """Moves `path` to the front of the recent list."""
    path = Path(path)
    entries = [str(p) for p in get_recent_files() if p != path]
    entries.insert(0, str(path))

    data = _read()
    data[_RECENT_FILES] = entries[:MAX_RECENT_FILES]
    _write(data)


def forget_recent_file(path) -> None:
    """Drops `path` from the recent list, e.g. after it failed to open."""
    path = Path(path)
    data = _read()
    entries = data.get(_RECENT_FILES)
    if not isinstance(entries, list):
        return
    data[_RECENT_FILES] = [e for e in entries if e != str(path)]
    _write(data)
