"""Interoperability with the etqw worksheet/test format (version 1.1).

`.etqw` is Map Quiz Maker's own save format, so a saved quiz can be opened
directly in the etqw app and its subsection copied into a larger test.
"""

from map_quiz_maker.etqw.bundle import (
    FILE_SUFFIX,
    EtqwError,
    load_document,
    save_document,
)

__all__ = ["FILE_SUFFIX", "EtqwError", "load_document", "save_document"]
