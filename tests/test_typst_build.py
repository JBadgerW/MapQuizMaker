"""End-to-end coverage of the build orchestration: real Typst compiles, so a
broken template or a bad path is caught here rather than in the GUI."""

import tempfile
from pathlib import Path

import pytest
from PIL import Image

from map_quiz_maker.export import typst_build
from map_quiz_maker.export.typst_build import BuildCancelled
from map_quiz_maker.models import QuizDocument


@pytest.fixture
def image_path(tmp_path):
    """Deliberately outside the output folder, so a test asserting on that
    folder's contents can tell a copied image from the source image."""
    source_dir = tmp_path / "maps"
    source_dir.mkdir()
    path = source_dir / "blank map.jpg"
    Image.new("RGB", (800, 600), "white").save(path)
    return path


@pytest.fixture
def compiled(monkeypatch):
    """Captures (versions, part) for each compile.

    The generated .typ is a temporary build intermediate, so assertions about
    what reached the template read it here rather than off disk.
    """
    calls = []
    real_compile = typst_build._compile

    def spy(versions, typ_path, pdf_path, font_paths, part=typst_build.WORKSHEET):
        calls.append((versions, part))
        real_compile(versions, typ_path, pdf_path, font_paths, part=part)

    monkeypatch.setattr(typst_build, "_compile", spy)
    return calls


@pytest.fixture
def doc(image_path):
    document = QuizDocument()
    document.set_image(image_path)
    for x, y, answer in [(0.2, 0.3, "Athens"), (0.8, 0.9, "Sparta")]:
        marker = document.add_marker(x, y)
        document.update_answer(marker.id, answer)
    document.update_meta(
        class_name="Humanities IV",
        title="Ancient Greece",
        instructions="Label each numbered location.",
    )
    return document


def build(document, output_dir=None, filename_stem=None, **meta):
    if meta:
        document.update_meta(**meta)
    return typst_build.build_quiz(
        document, output_dir=output_dir, filename_stem=filename_stem
    )


# ---------------------------------------------------------------------------
# Output location and naming
# ---------------------------------------------------------------------------


def test_writes_to_the_remembered_folder_not_the_working_directory(
    doc, tmp_path, monkeypatch
):
    destination = tmp_path / "Map Quizzes"
    monkeypatch.setattr(typst_build, "get_output_dir", lambda: destination)

    # Launching from a desktop shortcut or a file manager means an arbitrary
    # working directory; the destination must not follow it.
    elsewhere = tmp_path / "some-unrelated-cwd"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    worksheet, key = build(doc)

    assert worksheet.parent == destination
    assert key.parent == destination
    assert worksheet.is_file() and worksheet.stat().st_size > 0
    assert not (elsewhere / "output").exists()


def test_derives_a_safe_filename_from_class_and_title(doc, tmp_path):
    worksheet, key = build(doc, output_dir=tmp_path, title="Rivers/Mountains: Ch. 4")

    assert worksheet.name == "Humanities_IV_Rivers_Mountains_Ch_4.pdf"
    assert key.name == "Humanities_IV_Rivers_Mountains_Ch_4_KEY.pdf"


def test_builds_even_with_no_class_or_title(doc, tmp_path):
    worksheet, key = build(doc, output_dir=tmp_path, class_name="", title="")

    assert worksheet.name == "quiz.pdf"
    assert key.name == "quiz_KEY.pdf"
    assert worksheet.is_file()


def test_separate_files_get_one_pdf_per_version_plus_one_key(doc, tmp_path):
    """The key is the teacher's reference copy, so it stays a single file
    however the worksheets are split."""
    paths = build(
        doc, output_dir=tmp_path, num_versions=3, separate_files=True
    )

    assert [p.name for p in paths] == [
        "Humanities_IV_Ancient_Greece_v1.pdf",
        "Humanities_IV_Ancient_Greece_v2.pdf",
        "Humanities_IV_Ancient_Greece_v3.pdf",
        "Humanities_IV_Ancient_Greece_KEY.pdf",
    ]
    assert all(p.is_file() for p in paths)


def test_only_finished_pdfs_land_in_the_output_folder(doc, tmp_path):
    output_dir = tmp_path / "quizzes"
    build(doc, output_dir=output_dir, num_versions=2, separate_files=True)

    assert sorted(p.name for p in output_dir.iterdir()) == [
        "Humanities_IV_Ancient_Greece_KEY.pdf",
        "Humanities_IV_Ancient_Greece_v1.pdf",
        "Humanities_IV_Ancient_Greece_v2.pdf",
    ]


def test_the_scratch_directory_is_cleaned_up(doc, tmp_path):
    def build_scratch_dirs():
        return set(Path(tempfile.gettempdir()).glob("map-quiz-maker-build-*"))

    before = build_scratch_dirs()
    build(doc, output_dir=tmp_path)

    assert build_scratch_dirs() == before, "the build left a scratch directory behind"


# ---------------------------------------------------------------------------
# Answer key separation
# ---------------------------------------------------------------------------


def test_the_key_is_a_separate_pdf_by_default(doc, tmp_path, compiled):
    worksheet, key = build(doc, output_dir=tmp_path)

    parts = [part for _versions, part in compiled]
    assert parts == [typst_build.WORKSHEET, typst_build.KEY]
    assert worksheet.name.endswith(".pdf") and "_KEY" not in worksheet.name
    assert key.name.endswith("_KEY.pdf")


def test_combine_key_puts_everything_in_one_file(doc, tmp_path, compiled):
    paths = build(doc, output_dir=tmp_path, combine_key=True)

    assert len(paths) == 1
    assert "_KEY" not in paths[0].name
    assert [part for _versions, part in compiled] == [typst_build.BOTH]


def test_a_combined_build_with_separate_files_writes_no_key_file(doc, tmp_path):
    paths = build(
        doc, output_dir=tmp_path, num_versions=2, separate_files=True, combine_key=True
    )

    assert [p.name for p in paths] == [
        "Humanities_IV_Ancient_Greece_v1.pdf",
        "Humanities_IV_Ancient_Greece_v2.pdf",
    ]


# ---------------------------------------------------------------------------
# Reproducible versions
# ---------------------------------------------------------------------------


def test_version_n_is_the_same_paper_every_build(doc, tmp_path, compiled):
    build(doc, output_dir=tmp_path, num_versions=4)
    build(doc, output_dir=tmp_path / "again", num_versions=4)

    first = [v["markers"] for v in compiled[0][0]]
    second = [v["markers"] for v in compiled[2][0]]
    assert first == second


def test_two_documents_shuffle_differently(doc, image_path, tmp_path, compiled):
    other = QuizDocument()
    other.set_image(image_path)
    for x, y, answer in [(0.2, 0.3, "Athens"), (0.8, 0.9, "Sparta")]:
        other.update_answer(other.add_marker(x, y).id, answer)

    assert doc.shuffle_seed != other.shuffle_seed


def test_versions_within_one_build_differ_from_each_other(doc, tmp_path, compiled):
    """Ten markers make an identical shuffle vanishingly unlikely, so this
    catches a seed that ignores the version number."""
    for n in range(8):
        marker = doc.add_marker(0.1 * n, 0.1 * n)
        doc.update_answer(marker.id, f"Place {n}")

    build(doc, output_dir=tmp_path, num_versions=5)

    orders = [
        tuple(m["answer"] for m in version["markers"]) for version in compiled[0][0]
    ]
    assert len(set(orders)) > 1


def test_the_key_carries_a_build_code(doc, tmp_path, compiled):
    build(doc, output_dir=tmp_path, num_versions=2)

    codes = [version["code"] for version in compiled[0][0]]
    assert codes == [
        typst_build.build_code(doc.shuffle_seed, 1),
        typst_build.build_code(doc.shuffle_seed, 2),
    ]
    assert all(code.endswith(f"-v{n}") for n, code in enumerate(codes, start=1))


def test_rng_is_stable_across_processes():
    """Seeded from sha256 rather than hash(), which is salted per process."""
    assert typst_build.rng_for_version(12345, 3).random() == pytest.approx(
        typst_build.rng_for_version(12345, 3).random()
    )
    assert typst_build.rng_for_version(12345, 3).random() != (
        typst_build.rng_for_version(12345, 4).random()
    )


# ---------------------------------------------------------------------------
# Progress and cancellation
# ---------------------------------------------------------------------------


def test_progress_is_reported_and_ends_complete(doc, tmp_path):
    doc.update_meta(num_versions=3)
    seen = []
    typst_build.build_quiz(
        doc, output_dir=tmp_path, on_progress=lambda *args: seen.append(args)
    )

    assert seen, "a build must report progress"
    assert all(0 <= done <= total for done, total, _label in seen)
    assert seen[-1][0] == seen[-1][1], "the last report must be complete"
    assert all(isinstance(label, str) and label for *_x, label in seen)


def test_progress_counts_each_compile_not_each_version(doc, tmp_path):
    """Versions sharing one document are one compile, which is what actually
    takes the time; a bar counting versions would stall on the last one."""
    doc.update_meta(num_versions=3)
    combined = []
    typst_build.build_quiz(
        doc, output_dir=tmp_path, on_progress=lambda *a: combined.append(a)
    )
    assert combined[0][1] == 2  # one worksheet compile + one key compile

    doc.update_meta(separate_files=True)
    split = []
    typst_build.build_quiz(
        doc, output_dir=tmp_path / "split", on_progress=lambda *a: split.append(a)
    )
    assert split[0][1] == 4  # three worksheet compiles + one key compile


def test_cancelling_stops_the_build(doc, tmp_path):
    doc.update_meta(num_versions=5, separate_files=True)
    compiles = []

    def cancel_after_two():
        compiles.append(1)
        return len(compiles) > 2

    with pytest.raises(BuildCancelled):
        typst_build.build_quiz(
            doc, output_dir=tmp_path, should_cancel=cancel_after_two
        )

    assert len(list(tmp_path.glob("*.pdf"))) < 5


def test_a_cancelled_build_still_cleans_up_its_scratch_directory(doc, tmp_path):
    def build_scratch_dirs():
        return set(Path(tempfile.gettempdir()).glob("map-quiz-maker-build-*"))

    before = build_scratch_dirs()
    with pytest.raises(BuildCancelled):
        typst_build.build_quiz(doc, output_dir=tmp_path, should_cancel=lambda: True)

    assert build_scratch_dirs() == before


# ---------------------------------------------------------------------------
# Content reaching the template
# ---------------------------------------------------------------------------


def test_output_embeds_the_bundled_font(doc, tmp_path):
    """System fonts are ignored at compile time, so the worksheet typesets
    identically whether or not the machine has Linux Libertine installed."""
    worksheet, _key = build(doc, output_dir=tmp_path)

    assert b"LinLibertine" in worksheet.read_bytes()


def test_blank_instructions_still_compile(doc, tmp_path):
    """The template suppresses the instructions block when it's empty; that
    branch has to survive a real compile."""
    worksheet, _key = build(doc, output_dir=tmp_path, instructions="")

    assert worksheet.is_file() and worksheet.stat().st_size > 0


def test_instructions_reach_the_generated_source(doc, tmp_path, compiled):
    build(doc, output_dir=tmp_path, instructions="Label the map.")

    [version] = compiled[0][0]
    assert version["instructions"] == "Label the map."


def test_word_bank_drops_blanks_and_duplicates(doc, tmp_path, compiled):
    """A blank answer would print as an empty bank entry, and a repeated one
    twice, neither of which is a choice a student can make."""
    doc.update_answer(doc.add_marker(0.4, 0.4).id, "Athens")  # duplicate
    doc.update_answer(doc.add_marker(0.5, 0.5).id, "   ")  # blank

    build(doc, output_dir=tmp_path, include_word_bank=True)

    [version] = compiled[0][0]
    assert sorted(version["word-bank"]) == ["Athens", "Sparta"]


def test_word_bank_is_omitted_when_not_requested(doc, tmp_path, compiled):
    build(doc, output_dir=tmp_path, include_word_bank=False)

    [version] = compiled[0][0]
    assert version["word-bank"] == []
