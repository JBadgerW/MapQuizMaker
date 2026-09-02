"""Pure filename helpers for the export pipeline."""

import re

# Whitelist rather than blacklist: anything outside this set becomes an
# underscore, so path separators, drive-letter colons, and leading dots can
# never reach the filesystem. Periods are excluded deliberately -- that rules
# out both `..` traversal and accidental dotfiles. Disallowed characters are
# substituted rather than deleted so "Rivers/Mountains" keeps its word break
# instead of collapsing to "RiversMountains".
_DISALLOWED = re.compile(r"[^A-Za-z0-9 _-]")
_UNDERSCORE_RUNS = re.compile(r"[_\s]+")
_TRIM_CHARS = "_- "

# Long enough for any realistic class + title, short enough to stay clear of
# the ~255-byte per-component limit once a `_v12.pdf` suffix is appended.
MAX_STEM_LENGTH = 120

FALLBACK_STEM = "quiz"


def sanitize_filename(text: str) -> str:
    """Reduces arbitrary user text to a safe single path component.

    Never returns an empty string: text that sanitizes away entirely (or was
    empty to begin with) falls back to ``FALLBACK_STEM``, so a build with no
    class or title still writes a findable file instead of a dotfile.
    """
    cleaned = _DISALLOWED.sub("_", text)
    cleaned = _UNDERSCORE_RUNS.sub("_", cleaned).strip(_TRIM_CHARS)
    cleaned = cleaned[:MAX_STEM_LENGTH].strip(_TRIM_CHARS)
    return cleaned or FALLBACK_STEM
