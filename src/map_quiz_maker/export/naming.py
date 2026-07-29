"""Pure filename helpers for the export pipeline."""

import re


def sanitize_filename(text: str) -> str:
    return re.sub(r"\s", "_", text)
