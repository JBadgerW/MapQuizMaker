"""Orchestrates the Typst-based quiz build: shuffles markers, marshals
QuizState into the template's expected data shape, writes a generated
per-build .typ file to a scratch directory, and compiles it in-process via
the bundled `typst` Python package -- no system LaTeX/Typst install required.

Only finished PDFs are written to the user's output folder. The generated
.typ is a build intermediate and lives in a temporary directory that is
removed afterwards, so the folder a teacher opens holds only the files they
would actually print.

Everything Typst reads -- the template, the map image, the generated source
-- is assembled into that one temporary directory, which becomes the Typst
project root. Nothing is addressed by a path derived from the source tree,
so the build behaves identically from a checkout, an installed wheel, or a
frozen single-file executable.
"""

import random
import shutil
import tempfile
from contextlib import contextmanager
from importlib.resources import as_file, files
from pathlib import Path

import typst
from PIL import Image

from map_quiz_maker.config import IMG_WIDTH_CM
from map_quiz_maker.export.naming import sanitize_filename
from map_quiz_maker.export.typst_data import (
    build_version_dict,
    versions_to_typst_source,
)
from map_quiz_maker.settings import get_output_dir

# Package data, not filesystem paths: `files()` resolves through the import
# system, so this works wherever the package is installed. Deriving the
# template location by walking up from __file__ only ever worked inside a
# source checkout, and the template was not shipped in the wheel at all.
ASSETS = files("map_quiz_maker") / "assets"
TEMPLATE_RESOURCE = ASSETS / "quiz_template.typ"
FONTS_RESOURCE = ASSETS / "fonts"

TEMPLATE_FILENAME = "quiz_template.typ"
IMAGE_STEM = "map"


def _compile(
    versions: list, typ_path: Path, pdf_path: Path, font_paths: list[str]
) -> None:
    versions_source = versions_to_typst_source(versions)
    typ_path.write_text(
        f'#import "{TEMPLATE_FILENAME}": render\n'
        f"#let versions = {versions_source}\n"
        f"#render(versions)\n",
        encoding="utf-8",
    )
    typst.compile(
        str(typ_path),
        output=str(pdf_path),
        # The sandbox is the project root, so the template and image resolve
        # as plain relative names. This replaces a `root="/"` that existed
        # only to let absolute paths through.
        root=str(typ_path.parent),
        font_paths=font_paths,
        # Bundled fonts only. Falling through to system fonts is what let the
        # worksheet re-flow on any machine without Linux Libertine installed.
        ignore_system_fonts=True,
    )


@contextmanager
def _build_sandbox(image_file_path: Path):
    """Assembles a self-contained directory for Typst to compile from.

    Yields `(sandbox_dir, image_name, font_paths)`. The directory and
    everything in it is removed on exit, so none of it reaches the user's
    quiz folder.
    """
    with tempfile.TemporaryDirectory(prefix="map-quiz-maker-build-") as scratch:
        sandbox = Path(scratch)
        (sandbox / TEMPLATE_FILENAME).write_bytes(TEMPLATE_RESOURCE.read_bytes())

        image_name = IMAGE_STEM + image_file_path.suffix
        shutil.copy(image_file_path, sandbox / image_name)

        # `as_file` materializes the fonts on disk for the rare loader that
        # doesn't already serve them from one (a zipimport, say); for an
        # ordinary install it hands back the real directory.
        with as_file(FONTS_RESOURCE) as fonts_dir:
            yield sandbox, image_name, [str(fonts_dir)]


def image_size_cm(image_file_path) -> tuple[float, float]:
    """The printed size of a map, in centimetres.

    Width is fixed by the worksheet layout; height follows from the image's
    own aspect ratio.
    """
    with Image.open(image_file_path) as image:
        width_px, height_px = image.size
    return IMG_WIDTH_CM, IMG_WIDTH_CM * height_px / width_px


def build_quiz(doc, output_dir=None, filename_stem=None) -> list[Path]:
    """Builds one or more randomized versions of `doc` and compiles them.

    Versions are always numbered 1..num_versions for the current build (no
    cross-build continuity or other numbering scheme). With
    `num_versions == 1`, the output filename has no version suffix. With
    `num_versions > 1` and `separate_files`, each version gets its own
    `_v{n}` suffixed file; otherwise all versions are combined into one PDF.

    `filename_stem`, if given, is used verbatim as the base filename (e.g.
    from a "Save As" dialog); otherwise it's derived from class + title.

    `output_dir` defaults to the remembered/last-used quiz folder rather than
    a path relative to the working directory, so output never depends on
    where the app happened to be launched from.

    Returns the list of PDF paths written (length 1 unless num_versions > 1
    and separate_files is True).
    """
    if doc.image_path is None:
        raise ValueError("This quiz has no map image yet.")

    meta = doc.meta
    output_dir = Path(output_dir) if output_dir is not None else get_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    image_file_path = Path(doc.image_path).resolve()
    image_width_cm, image_height_cm = image_size_cm(image_file_path)

    class_name, title = meta.class_name, meta.title
    instructions = meta.instructions
    include_word_bank = meta.include_word_bank

    base_markers = list(doc.markers)
    num_versions = max(1, meta.num_versions)
    separate_files = meta.separate_files
    base_filename = (
        filename_stem if filename_stem is not None else sanitize_filename(f"{class_name}_{title}")
    )

    def _make_version_dict(version_number: int, image_name: str) -> dict:
        shuffled = list(base_markers)
        random.shuffle(shuffled)
        word_bank = None
        if include_word_bank:
            # Blank answers would print as empty word-bank entries; a repeated
            # answer is listed once, since the bank is a set of choices.
            word_bank = list(dict.fromkeys(m.answer.strip() for m in shuffled if m.answer.strip()))
            random.shuffle(word_bank)
        return build_version_dict(
            class_name=class_name,
            title=title,
            version=str(version_number),
            instructions=instructions,
            image_filename=image_name,
            image_width_cm=image_width_cm,
            image_height_cm=image_height_cm,
            markers=shuffled,
            word_bank=word_bank,
        )

    version_numbers = list(range(1, num_versions + 1))

    with _build_sandbox(image_file_path) as (sandbox, image_name, font_paths):
        if num_versions > 1 and separate_files:
            pdf_paths = []
            for n in version_numbers:
                pdf_path = output_dir / f"{base_filename}_v{n}.pdf"
                _compile(
                    [_make_version_dict(n, image_name)],
                    sandbox / f"{base_filename}_v{n}.typ",
                    pdf_path,
                    font_paths,
                )
                pdf_paths.append(pdf_path)
            return pdf_paths

        pdf_path = output_dir / f"{base_filename}.pdf"
        version_dicts = [_make_version_dict(n, image_name) for n in version_numbers]
        _compile(
            version_dicts, sandbox / f"{base_filename}.typ", pdf_path, font_paths
        )
        return [pdf_path]
