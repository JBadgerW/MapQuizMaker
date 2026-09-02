"""Reading and writing `.etqw` bundles.

A map quiz is expressed as one etqw document (format 1.1) containing a single
section with a single `fill_in_the_blank` subsection: the map is the
subsection's image stimulus, and each numbered location is one question whose
answer lives inline in the stem as a `{{answer}}` marker. That type is the
only one that represents both of this app's modes -- with and without a word
bank -- since `Subsection.show_word_bank` is exactly the app's checkbox.

Two images travel in the subsection's `media/`:

  map.png         the stimulus, with the numbers already drawn on it, because
                  etqw's renderer draws an image as-is and has no notion of a
                  marker.
  map-source.*    the clean original, referenced only from the `x_mapquiz`
                  extension below, so this app can reopen the document and
                  move a marker.

`x_mapquiz` on the stimulus carries the marker coordinates. Only
`manifest.sections[]` sets `additionalProperties: false` in the etqw schemas,
so the extension validates; etqw's own loader reads the fields it knows and
ignores it. The consequence, deliberately accepted: a document opened and
re-saved in etqw comes back as a plain image-stimulus subsection with the
coordinates and the clean map dropped. etqw is the consumer, this app is the
editor.
"""

import json
import re
import tempfile
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from map_quiz_maker.etqw.typst_text import escape_typst, unescape_typst
from map_quiz_maker.models import Marker, QuizDocument
from map_quiz_maker.render import render_marked_image

FORMAT = "etqw"
FORMAT_VERSION = "1.1"
SUBSECTION_TYPE = "fill_in_the_blank"
DOCUMENT_TYPE = "quiz"
FILE_SUFFIX = ".etqw"

STIMULUS_FILENAME = "map.png"
SOURCE_STEM = "map-source"

# Maps fill the content width; etqw's own default of 70% would shrink a map
# that the teacher sized deliberately.
STIMULUS_WIDTH_PCT = 100

EXTENSION_KEY = "x_mapquiz"
EXTENSION_VERSION = 1

#: `{{answer}}` markers inside a fill-in-the-blank stem. Mirrors
#: ``twg.models.BLANK_MARKER_RE``; braces carry no meaning in Typst markup.
BLANK_MARKER_RE = re.compile(r"\{\{([^{}]*)\}\}")


class EtqwError(Exception):
    """A bundle could not be read as a Map Quiz Maker document."""


# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------


def _slug(text: str, max_chars: int = 40) -> str:
    """Filesystem-safe slug. Mirrors ``twg.serialization._slug``.

    Folder names are a convenience in this format, not data -- the canonical
    order is the ref arrays -- but matching the other app's shape keeps a
    bundle recognisable when unzipped.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_chars]


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def _question_dicts(markers) -> list[dict]:
    return [
        {
            "id": _new_id(),
            "source_id": None,
            "type": SUBSECTION_TYPE,
            "stem": "{{" + escape_typst(marker.answer.strip()) + "}}",
        }
        for marker in markers
    ]


def _stimulus_dict(markers, source_name: str, meta, shuffle_seed: int) -> dict:
    """The image stimulus, plus this app's marker coordinates."""
    return {
        "kind": "image",
        "path": STIMULUS_FILENAME,
        "alt_text": f"Map with {len(markers)} numbered locations to identify",
        "width_pct": STIMULUS_WIDTH_PCT,
        EXTENSION_KEY: {
            "version": EXTENSION_VERSION,
            "source_image": source_name,
            # Same order as the questions above: the nth marker is the nth
            # question, which is what keeps answers and positions in step
            # without storing the answers twice.
            "markers": [{"x": m.x, "y": m.y} for m in markers],
            "options": {
                "num_versions": meta.num_versions,
                "separate_files": meta.separate_files,
                "combine_key": meta.combine_key,
            },
            # Saved so "Version 3" keeps naming the same paper after the
            # document is closed and reopened.
            "shuffle_seed": shuffle_seed,
        },
    }


def _subsection_dict(doc, source_name: str) -> dict:
    markers = doc.markers
    meta = doc.meta
    # Key order follows twg.serialization.subsection_to_dict so an unzipped
    # bundle diffs cleanly against one the other app wrote.
    subsection = {
        "id": _new_id(),
        "source_id": None,
        "type": SUBSECTION_TYPE,
        "title": meta.title or "Map Quiz",
        "show_header": True,
        "show_stimulus": True,
        "content": _question_dicts(markers),
    }
    if meta.instructions.strip():
        subsection["instructions"] = escape_typst(meta.instructions.strip())
    subsection["stimulus"] = _stimulus_dict(
        markers, source_name, meta, doc.shuffle_seed
    )
    subsection["show_word_bank"] = meta.include_word_bank
    return subsection


def save_document(doc: QuizDocument, path) -> Path:
    """Writes `doc` to `path` as a `.etqw` bundle. Returns the path written.

    The document's etqw identity is minted on first save and kept thereafter,
    so re-saving updates a document rather than creating a new one.
    """
    path = Path(path)
    if doc.image_path is None:
        raise EtqwError("This quiz has no map image yet, so there is nothing to save.")

    source_path = Path(doc.image_path)
    if not source_path.is_file():
        raise EtqwError(f"The map image is missing:\n{source_path}")

    markers = doc.markers
    meta = doc.meta

    doc.etqw_id = doc.etqw_id or _new_id()
    doc.created_at = doc.created_at or _now()

    title = meta.title or path.stem
    section_folder = f"sections/1_{_slug(title) or 'map-quiz'}"
    subsection_folder = (
        f"{section_folder}/subsections/{SUBSECTION_TYPE}-1_{_slug(title) or 'map-quiz'}"
    )
    source_name = SOURCE_STEM + source_path.suffix.lower()

    subsection = _subsection_dict(doc, source_name)
    section = {
        "id": _new_id(),
        "source_id": None,
        "title": title,
        "show_header": True,
        "subsections": [
            {"id": subsection["id"], "path": f"{subsection_folder}/subsection.json"}
        ],
    }
    manifest = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "id": doc.etqw_id,
        "source_id": doc.etqw_source_id,
        "type": DOCUMENT_TYPE,
        "title": title,
        "author": meta.author,
        "course": meta.class_name,
        "created_at": doc.created_at,
        "updated_at": _now(),
        "theme": "compact",
        "doc_version": "",
        "section_numbering": "roman",
        "sections": [{"id": section["id"], "path": f"{section_folder}/section.json"}],
    }

    with tempfile.TemporaryDirectory(prefix="map-quiz-maker-etqw-") as scratch:
        marked = render_marked_image(
            source_path, markers, Path(scratch) / STIMULUS_FILENAME
        )

        path.parent.mkdir(parents=True, exist_ok=True)
        # Written to a sibling first, then moved into place, so an
        # interrupted save cannot leave a half-written document behind.
        staging = path.with_name(path.name + ".writing")
        try:
            with zipfile.ZipFile(staging, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("manifest.json", json.dumps(manifest, indent=2))
                archive.writestr(
                    f"{section_folder}/section.json", json.dumps(section, indent=2)
                )
                archive.writestr(
                    f"{subsection_folder}/subsection.json",
                    json.dumps(subsection, indent=2),
                )
                archive.write(marked, f"{subsection_folder}/media/{STIMULUS_FILENAME}")
                archive.write(
                    source_path, f"{subsection_folder}/media/{source_name}"
                )
            staging.replace(path)
        finally:
            staging.unlink(missing_ok=True)

    doc.mark_clean(path)
    return path


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def blank_answers(stem: str) -> list[str]:
    """The answers embedded in a fill-in-the-blank stem, in order."""
    return [m.group(1).strip() for m in BLANK_MARKER_RE.finditer(stem or "")]


def _read_json(archive: zipfile.ZipFile, name: str) -> dict:
    try:
        return json.loads(archive.read(name).decode("utf-8"))
    except KeyError as exc:
        raise EtqwError(f"This file is missing {name}.") from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise EtqwError(f"{name} in this file is damaged and can't be read.") from exc


def _first_ref(container: dict, key: str, what: str) -> dict:
    refs = container.get(key) or []
    if not refs:
        raise EtqwError(f"This document has no {what}.")
    return refs[0]


def load_document(path) -> QuizDocument:
    """Reads a `.etqw` bundle back into an editable document.

    Raises `EtqwError` with a message worth showing the user for anything
    that is a valid etqw document but not one this app can edit.
    """
    path = Path(path)
    if not zipfile.is_zipfile(path):
        raise EtqwError("This doesn't look like an .etqw file.")

    with zipfile.ZipFile(path) as archive:
        manifest = _read_json(archive, "manifest.json")
        if manifest.get("format") != FORMAT:
            raise EtqwError("This isn't an etqw document.")
        if str(manifest.get("format_version", "")).split(".")[0] != "1":
            raise EtqwError(
                f"This document is format version {manifest.get('format_version')}, "
                "which this version of Map Quiz Maker doesn't understand."
            )

        section = _read_json(archive, _first_ref(manifest, "sections", "sections")["path"])
        subsection_path = _first_ref(section, "subsections", "subsections")["path"]
        subsection = _read_json(archive, subsection_path)

        if subsection.get("type") != SUBSECTION_TYPE:
            raise EtqwError(
                f"Map Quiz Maker can only open '{SUBSECTION_TYPE}' subsections, "
                f"and this one is '{subsection.get('type')}'."
            )

        stimulus = subsection.get("stimulus") or {}
        extension = stimulus.get(EXTENSION_KEY)
        if not extension:
            raise EtqwError(
                "This document has no marker positions saved in it, so it can't "
                "be edited as a map quiz.\n\nThat happens when the document was "
                "last saved by the etqw app, which doesn't keep them."
            )

        positions = extension.get("markers") or []
        questions = subsection.get("content") or []
        if len(positions) != len(questions):
            raise EtqwError(
                f"This document has {len(positions)} marker positions but "
                f"{len(questions)} questions, so they can't be matched up."
            )

        media_root = str(Path(subsection_path).parent / "media")
        source_name = extension.get("source_image")
        if not source_name:
            raise EtqwError("This document doesn't name its original map image.")

        media_dir = tempfile.TemporaryDirectory(prefix="map-quiz-maker-open-")
        try:
            archive.extract(f"{media_root}/{source_name}", media_dir.name)
        except KeyError as exc:
            raise EtqwError(
                f"The original map image ({source_name}) is missing from this file."
            ) from exc
        image_path = Path(media_dir.name) / media_root / source_name

    doc = QuizDocument()
    # Held so the extracted image outlives this function; the directory is
    # removed when the document is dropped.
    doc._media_tmp = media_dir

    doc.etqw_id = manifest.get("id")
    doc.etqw_source_id = manifest.get("source_id")
    doc.created_at = manifest.get("created_at")

    seed = extension.get("shuffle_seed")
    if isinstance(seed, int):
        doc.shuffle_seed = seed

    options = extension.get("options") or {}
    doc.update_meta(
        class_name=manifest.get("course") or "",
        author=manifest.get("author") or "",
        title=manifest.get("title") or "",
        instructions=unescape_typst(subsection.get("instructions") or ""),
        include_word_bank=bool(subsection.get("show_word_bank", False)),
        num_versions=max(1, int(options.get("num_versions", 1) or 1)),
        separate_files=bool(options.get("separate_files", False)),
        combine_key=bool(options.get("combine_key", False)),
    )

    markers = []
    for index, (position, question) in enumerate(zip(positions, questions), start=1):
        answers = blank_answers(question.get("stem", ""))
        markers.append(
            Marker(
                id=index,
                x=float(position.get("x", 0.0)),
                y=float(position.get("y", 0.0)),
                answer=unescape_typst(answers[0]) if answers else "",
                display_number=index,
            )
        )

    doc.set_image(image_path, keep_markers=True)
    doc.load_markers(markers, next_id=len(markers) + 1)
    doc.mark_clean(path)
    return doc
