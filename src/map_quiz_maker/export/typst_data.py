"""Pure data marshalling for the Typst export.

Builds a plain Python dict describing one quiz version (matching the shape
`map_quiz_maker/assets/quiz_template.typ` expects) and serializes it to
Typst source syntax. Kept free of file I/O and the `typst` package itself so
data shape and string-escaping are easily unit-testable.
"""


def escape_typst_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_version_dict(
    class_name: str,
    title: str,
    version: str,
    instructions: str,
    image_filename: str,
    image_width_cm: float,
    image_height_cm: float,
    markers,
    word_bank=None,
) -> dict:
    """`markers` is an iterable of objects with .x/.y/.answer (e.g.
    map_quiz_maker.models.Marker), where x and y are fractions of the image
    in 0..1 from its top-left corner. Order is preserved as given by the
    caller (shuffling, if wanted, is the caller's responsibility).

    `word_bank`, if given, is a list of answer strings to render as a word
    bank right after the image; omit or pass None/[] to leave it out.
    """
    return {
        "class": class_name,
        "title": title,
        "version": version,
        "instructions": instructions,
        "image": {
            "filename": image_filename,
            "width-cm": image_width_cm,
            "height-cm": image_height_cm,
        },
        "markers": [
            {
                "display-number": index + 1,
                "x": marker.x,
                "y": marker.y,
                "answer": marker.answer,
            }
            for index, marker in enumerate(markers)
        ],
        "word-bank": list(word_bank) if word_bank else [],
    }


def _to_typst_literal(value) -> str:
    if isinstance(value, str):
        return f'"{escape_typst_string(value)}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, dict):
        if not value:
            return "(:)"
        items = ", ".join(f"{key}: {_to_typst_literal(val)}" for key, val in value.items())
        return f"({items})"
    if isinstance(value, (list, tuple)):
        if not value:
            return "()"
        items = ", ".join(_to_typst_literal(item) for item in value)
        return f"({items},)"  # trailing comma: unambiguous array syntax at any length
    raise TypeError(f"Cannot serialize {type(value)!r} to a Typst literal")


def versions_to_typst_source(versions: list) -> str:
    """`versions` is a list of version dicts (see build_version_dict). Returns
    a Typst array literal suitable for `#let versions = <this>`.
    """
    return _to_typst_literal(list(versions))
