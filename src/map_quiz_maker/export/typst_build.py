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

import hashlib
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


#: Which halves of each version a compile emits. See the template's `render`.
WORKSHEET = "worksheet"
KEY = "key"
BOTH = "both"

KEY_FILENAME_SUFFIX = "_KEY"


def rng_for_version(seed: int, version_number: int) -> random.Random:
    """The shuffle for one version of one document.

    Derived from the document's own seed rather than global `random`, so
    version N is the same paper every time it is built. Hashed with sha256
    because Python's `hash()` of a string is salted per process.
    """
    digest = hashlib.sha256(f"{seed}:{version_number}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def build_code(seed: int, version_number: int) -> str:
    """A short teacher-facing identifier printed on the answer key."""
    digest = hashlib.sha256(f"{seed}:{version_number}".encode()).hexdigest()
    return f"{digest[:6]}-v{version_number}"


def _compile(
    versions: list,
    typ_path: Path,
    pdf_path: Path,
    font_paths: list[str],
    part: str = WORKSHEET,
) -> None:
    versions_source = versions_to_typst_source(versions)
    typ_path.write_text(
        f'#import "{TEMPLATE_FILENAME}": render\n'
        f"#let versions = {versions_source}\n"
        f'#render(versions, part: "{part}")\n',
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


class BuildCancelled(Exception):
    """Raised inside a build when the caller asked it to stop."""


def build_quiz(
    doc,
    output_dir=None,
    filename_stem=None,
    on_progress=None,
    should_cancel=None,
) -> list[Path]:
    """Builds one or more randomized versions of `doc` and compiles them.

    Version N of a given document is reproducible: the shuffle comes from
    the document's own seed, not global `random`, so rebuilding gives the
    same paper back rather than a new one wearing the same version number.

    The answer key is written as its own PDF unless `meta.combine_key` is
    set. Printing the worksheets should not be able to hand out the answers.
    However versions are grouped, the key is always one file -- it is the
    teacher's reference copy, and N separate key files help nobody.

    `filename_stem`, if given, is used verbatim as the base filename (e.g.
    from a "Save As" dialog); otherwise it's derived from class + title.

    `output_dir` defaults to the remembered/last-used quiz folder rather than
    a path relative to the working directory, so output never depends on
    where the app happened to be launched from.

    `on_progress(done, total, label)` is called before each compile, and
    `should_cancel()` is checked between them; returning True raises
    `BuildCancelled`. A Typst compile cannot be interrupted part-way, so
    cancelling takes effect at the next version boundary.

    Returns the list of PDF paths written, worksheets first.
    """
    if doc.image_path is None:
        raise ValueError("This quiz has no map image yet.")

    meta = doc.meta
    output_dir = Path(output_dir) if output_dir is not None else get_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    image_file_path = Path(doc.image_path).resolve()
    image_width_cm, image_height_cm = image_size_cm(image_file_path)

    base_markers = list(doc.markers)
    num_versions = max(1, meta.num_versions)
    separate_files = meta.separate_files
    combine_key = meta.combine_key
    seed = doc.shuffle_seed
    base_filename = (
        filename_stem
        if filename_stem is not None
        else sanitize_filename(f"{meta.class_name}_{meta.title}")
    )

    def _make_version_dict(version_number: int, image_name: str) -> dict:
        rng = rng_for_version(seed, version_number)
        shuffled = list(base_markers)
        rng.shuffle(shuffled)

        word_bank = None
        if meta.include_word_bank:
            # Blank answers would print as empty word-bank entries; a repeated
            # answer is listed once, since the bank is a set of choices.
            word_bank = list(
                dict.fromkeys(m.answer.strip() for m in shuffled if m.answer.strip())
            )
            rng.shuffle(word_bank)

        version = build_version_dict(
            class_name=meta.class_name,
            title=meta.title,
            version=str(version_number),
            instructions=meta.instructions,
            image_filename=image_name,
            image_width_cm=image_width_cm,
            image_height_cm=image_height_cm,
            markers=shuffled,
            word_bank=word_bank,
        )
        version["code"] = build_code(seed, version_number)
        return version

    version_numbers = list(range(1, num_versions + 1))

    # One unit of work per compile, so the progress bar tracks what actually
    # takes the time rather than counting versions that share a document.
    if separate_files and num_versions > 1:
        total = num_versions + (0 if combine_key else 1)
    else:
        total = 1 if combine_key else 2
    done = 0

    def step(label: str) -> None:
        nonlocal done
        if should_cancel is not None and should_cancel():
            raise BuildCancelled
        if on_progress is not None:
            on_progress(done, total, label)
        done += 1

    pdf_paths: list[Path] = []

    with _build_sandbox(image_file_path) as (sandbox, image_name, font_paths):
        version_dicts = {n: _make_version_dict(n, image_name) for n in version_numbers}
        worksheet_part = BOTH if combine_key else WORKSHEET

        if separate_files and num_versions > 1:
            for n in version_numbers:
                step(f"Building version {n} of {num_versions}...")
                pdf_path = output_dir / f"{base_filename}_v{n}.pdf"
                _compile(
                    [version_dicts[n]],
                    sandbox / f"{base_filename}_v{n}.typ",
                    pdf_path,
                    font_paths,
                    part=worksheet_part,
                )
                pdf_paths.append(pdf_path)
        else:
            step(
                f"Building {num_versions} versions..."
                if num_versions > 1
                else "Building the worksheet..."
            )
            pdf_path = output_dir / f"{base_filename}.pdf"
            _compile(
                [version_dicts[n] for n in version_numbers],
                sandbox / f"{base_filename}.typ",
                pdf_path,
                font_paths,
                part=worksheet_part,
            )
            pdf_paths.append(pdf_path)

        if not combine_key:
            step("Building the answer key...")
            key_path = output_dir / f"{base_filename}{KEY_FILENAME_SUFFIX}.pdf"
            _compile(
                [version_dicts[n] for n in version_numbers],
                sandbox / f"{base_filename}{KEY_FILENAME_SUFFIX}.typ",
                key_path,
                font_paths,
                part=KEY,
            )
            pdf_paths.append(key_path)

        if on_progress is not None:
            on_progress(total, total, "Finishing...")

    return pdf_paths
