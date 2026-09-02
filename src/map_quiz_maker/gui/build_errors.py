"""Turning build failures into sentences a teacher can act on.

The build used to show `str(exc)` straight from the exception, so a bad
filename surfaced as "[Errno 2] No such file or directory:
'Rivers/Mountains.typ'". Each case here names what went wrong and what to do
about it; anything unrecognised still shows its message rather than being
swallowed.
"""

from pathlib import Path

import typst
from PIL import UnidentifiedImageError


def describe(exc: Exception, image_path=None) -> str:
    """A user-facing explanation of why a build failed."""
    if isinstance(exc, UnidentifiedImageError):
        return (
            "That map image is in a format the app can't read.\n\n"
            "Try opening it in another program and saving it as a PNG or JPEG."
        )

    if isinstance(exc, FileNotFoundError):
        missing = getattr(exc, "filename", None)
        if image_path is not None and missing and Path(missing) == Path(image_path):
            return (
                f"The map image has moved or been deleted:\n{missing}\n\n"
                "Load it again, or point the quiz at a new copy."
            )
        return f"A file the build needs is missing:\n{missing or exc}"

    if isinstance(exc, PermissionError):
        return (
            f"The app isn't allowed to write to that folder:\n"
            f"{getattr(exc, 'filename', '') or exc}\n\n"
            "Choose a different folder, or close the PDF if it's open in a "
            "viewer that locks it."
        )

    if isinstance(exc, OSError) and exc.errno == 28:  # ENOSPC
        return "There isn't enough free disk space to write the quiz."

    if isinstance(exc, typst.TypstError):
        return (
            "Typst couldn't lay out the worksheet.\n\n"
            f"{exc}\n\n"
            "This usually means an answer or title contains something the "
            "typesetter choked on. Try simplifying it."
        )

    if isinstance(exc, MemoryError):
        return (
            "The app ran out of memory building this quiz.\n\n"
            "A very large map image is the usual cause; try scaling it down."
        )

    return f"Something went wrong while building the quiz:\n\n{exc}"
