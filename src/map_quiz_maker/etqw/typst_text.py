"""Plain text <-> Typst markup, for the etqw boundary.

Every prose field in an etqw document -- stems, instructions, captions -- is
Typst markup, evaluated through `eval(s, mode: "markup")` when rendered. Map
Quiz Maker holds plain text, so it must escape on the way out or the source
is silently mangled: a run of underscores reads as emphasis delimiters and
disappears, and a stray `#` or `$` is a code or math expression that can fail
the compile outright.

The escape set mirrors `twg/importers/model.py` in the etqw project, which is
the authoritative implementation. Kept as a small local copy rather than an
import because the two apps ship separately.
"""

import re

# Backslash must come first in the class or it would re-escape the
# backslashes added for everything else.
_INLINE_SPECIALS = "\\`*_$#<>@[]"

# At the very start of a field these instead begin a list item or heading.
_LEADING_SPECIALS = "-+=/"

_ESCAPE_RE = re.compile("([" + re.escape(_INLINE_SPECIALS) + "])")
_LEADING_RE = re.compile(r"^([" + re.escape(_LEADING_SPECIALS) + r"])")
_UNESCAPE_RE = re.compile(
    r"\\([" + re.escape(_INLINE_SPECIALS + _LEADING_SPECIALS) + r"])"
)


def escape_typst(text: str) -> str:
    """Escapes plain text for storage in a Typst-markup field.

    Quotes are deliberately left alone: Typst turns them into typographic
    quotes, which is what a teacher's document wants anyway.
    """
    if not text:
        return text
    return _LEADING_RE.sub(r"\\\1", _ESCAPE_RE.sub(r"\\\1", text))


def unescape_typst(text: str) -> str:
    """The inverse of `escape_typst`, for reading a document back in.

    Exact for anything this module wrote. Markup a person added by hand in
    the other app (say `#emph[...]`) is returned as written, since there is
    no plain-text equivalent to recover.
    """
    if not text:
        return text
    return _UNESCAPE_RE.sub(r"\1", text)
