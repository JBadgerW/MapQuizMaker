"""Orchestrates the Typst-based quiz build: shuffles markers, marshals
QuizState into the template's expected data shape, writes a generated
per-build .typ file, and compiles it in-process via the bundled `typst`
Python package -- no system LaTeX/Typst install required.
"""

import random
import shutil
from pathlib import Path

import typst

from map_quiz_maker.config import OUTPUT_DIR_NAME
from map_quiz_maker.export.naming import sanitize_filename
from map_quiz_maker.export.typst_data import build_version_dict, versions_to_typst_source

# src/map_quiz_maker/export/typst_build.py -> up 3 levels to the repo root,
# where assets/templates/ lives.
REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PATH = REPO_ROOT / "assets" / "templates" / "quiz_template.typ"


def _compile(versions: list, typ_path: Path, pdf_path: Path) -> None:
    versions_source = versions_to_typst_source(versions)
    typ_path.write_text(
        f'#import "{TEMPLATE_PATH.as_posix()}": render\n'
        f"#let versions = {versions_source}\n"
        f"#render(versions)\n"
    )
    typst.compile(str(typ_path), output=str(pdf_path), root="/")


def build_quiz(
    quiz_state,
    image_file_path,
    image_width_cm,
    image_height_cm,
    class_name,
    title,
    instructions,
    num_versions=1,
    separate_files=False,
    include_word_bank=False,
    output_dir=None,
    filename_stem=None,
) -> list[Path]:
    """Builds one or more randomized quiz versions and compiles them to PDF.

    Versions are always numbered 1..num_versions for the current build (no
    cross-build continuity or other numbering scheme). With
    `num_versions == 1`, the output filename has no version suffix. With
    `num_versions > 1` and `separate_files`, each version gets its own
    `_v{n}` suffixed file; otherwise all versions are combined into one PDF.

    `filename_stem`, if given, is used verbatim as the base filename (e.g.
    from a "Save As" dialog); otherwise it's derived from class_name+title.

    Returns the list of PDF paths written (length 1 unless num_versions > 1
    and separate_files is True).
    """
    output_dir = Path(output_dir) if output_dir is not None else Path(OUTPUT_DIR_NAME)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_file_path = Path(image_file_path)
    image_output_path = output_dir / image_file_path.name
    if not image_output_path.exists():
        shutil.copy(image_file_path, image_output_path)

    base_markers = list(quiz_state.markers)
    num_versions = max(1, num_versions)
    base_filename = (
        filename_stem if filename_stem is not None else sanitize_filename(f"{class_name}_{title}")
    )

    def _make_version_dict(version_number: int) -> dict:
        shuffled = list(base_markers)
        random.shuffle(shuffled)
        word_bank = None
        if include_word_bank:
            word_bank = [m.answer for m in shuffled]
            random.shuffle(word_bank)
        return build_version_dict(
            class_name=class_name,
            title=title,
            version=str(version_number),
            instructions=instructions,
            image_filename=str(image_output_path.resolve()),
            image_width_cm=image_width_cm,
            image_height_cm=image_height_cm,
            markers=shuffled,
            word_bank=word_bank,
        )

    version_numbers = list(range(1, num_versions + 1))

    if num_versions > 1 and separate_files:
        pdf_paths = []
        for n in version_numbers:
            typ_path = output_dir / f"{base_filename}_v{n}.typ"
            pdf_path = output_dir / f"{base_filename}_v{n}.pdf"
            _compile([_make_version_dict(n)], typ_path, pdf_path)
            pdf_paths.append(pdf_path)
        return pdf_paths

    typ_path = output_dir / f"{base_filename}.typ"
    pdf_path = output_dir / f"{base_filename}.pdf"
    version_dicts = [_make_version_dict(n) for n in version_numbers]
    _compile(version_dicts, typ_path, pdf_path)
    return [pdf_path]
