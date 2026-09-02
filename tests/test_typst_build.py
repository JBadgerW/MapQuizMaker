"""End-to-end coverage of the build orchestration: real Typst compiles, so a
broken template or a bad path is caught here rather than in the GUI."""

import tempfile
from pathlib import Path

import pytest
from PIL import Image

from map_quiz_maker.export import typst_build
from map_quiz_maker.models import QuizState


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
def compiled_versions(monkeypatch):
    """Captures the version dicts handed to each compile.

    The generated .typ is a temporary build intermediate now, so assertions
    about what reached the template read it here rather than off disk.
    """
    batches = []
    real_compile = typst_build._compile

    def spy(versions, *args, **kwargs):
        batches.append(versions)
        real_compile(versions, *args, **kwargs)

    monkeypatch.setattr(typst_build, "_compile", spy)
    return batches


@pytest.fixture
def quiz_state():
    state = QuizState()
    for x, y, answer in [(2.0, 3.0, "Athens"), (8.0, 9.0, "Sparta")]:
        marker = state.add_marker(x, y)
        state.update_answer(marker.id, answer)
    return state


def build(quiz_state, image_path, **overrides):
    kwargs = {
        "quiz_state": quiz_state,
        "image_file_path": image_path,
        "image_width_cm": 17.78,
        "image_height_cm": 13.34,
        "class_name": "Humanities IV",
        "title": "Ancient Greece",
        "instructions": "Label each numbered location.",
    }
    kwargs.update(overrides)
    return typst_build.build_quiz(**kwargs)


def test_writes_to_the_remembered_folder_not_the_working_directory(
    quiz_state, image_path, tmp_path, monkeypatch
):
    destination = tmp_path / "Map Quizzes"
    monkeypatch.setattr(typst_build, "get_output_dir", lambda: destination)

    # Launching from a desktop shortcut or a file manager means an arbitrary
    # working directory; the destination must not follow it.
    elsewhere = tmp_path / "some-unrelated-cwd"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    [pdf] = build(quiz_state, image_path)

    assert pdf.parent == destination
    assert pdf.is_file() and pdf.stat().st_size > 0
    assert not (elsewhere / "output").exists()


def test_derives_a_safe_filename_from_class_and_title(quiz_state, image_path, tmp_path):
    [pdf] = build(
        quiz_state, image_path, output_dir=tmp_path, title="Rivers/Mountains: Ch. 4"
    )

    assert pdf.name == "Humanities_IV_Rivers_Mountains_Ch_4.pdf"
    assert pdf.is_file()


def test_builds_even_with_no_class_or_title(quiz_state, image_path, tmp_path):
    [pdf] = build(quiz_state, image_path, output_dir=tmp_path, class_name="", title="")

    assert pdf.name == "quiz.pdf"
    assert pdf.is_file()


def test_separate_files_get_one_pdf_per_version(quiz_state, image_path, tmp_path):
    pdfs = build(
        quiz_state, image_path, output_dir=tmp_path, num_versions=3, separate_files=True
    )

    assert [p.name for p in pdfs] == [
        "Humanities_IV_Ancient_Greece_v1.pdf",
        "Humanities_IV_Ancient_Greece_v2.pdf",
        "Humanities_IV_Ancient_Greece_v3.pdf",
    ]
    assert all(p.is_file() for p in pdfs)


def test_output_embeds_the_bundled_font(quiz_state, image_path, tmp_path):
    """System fonts are ignored at compile time, so the worksheet typesets
    identically whether or not the machine has Linux Libertine installed."""
    [pdf] = build(quiz_state, image_path, output_dir=tmp_path)

    assert b"LinLibertine" in pdf.read_bytes()


def test_blank_instructions_still_compile(quiz_state, image_path, tmp_path):
    """The template suppresses the instructions block when it's empty; that
    branch has to survive a real compile."""
    [pdf] = build(quiz_state, image_path, output_dir=tmp_path, instructions="")

    assert pdf.is_file() and pdf.stat().st_size > 0


def test_only_finished_pdfs_land_in_the_output_folder(quiz_state, image_path, tmp_path):
    """The generated .typ and the source image are build inputs, not things
    the teacher should have to pick out of their quiz folder."""
    output_dir = tmp_path / "quizzes"
    build(
        quiz_state,
        image_path,
        output_dir=output_dir,
        num_versions=2,
        separate_files=True,
    )

    assert sorted(p.name for p in output_dir.iterdir()) == [
        "Humanities_IV_Ancient_Greece_v1.pdf",
        "Humanities_IV_Ancient_Greece_v2.pdf",
    ]


def test_the_scratch_directory_is_cleaned_up(quiz_state, image_path, tmp_path):
    leftovers = list(Path(tempfile.gettempdir()).glob("map-quiz-maker-*"))
    assert leftovers == []

    build(quiz_state, image_path, output_dir=tmp_path)

    assert list(Path(tempfile.gettempdir()).glob("map-quiz-maker-*")) == []


def test_instructions_reach_the_generated_source(
    quiz_state, image_path, tmp_path, compiled_versions
):
    build(quiz_state, image_path, output_dir=tmp_path, instructions="Label the map.")

    [version] = compiled_versions[0]
    assert version["instructions"] == "Label the map."


def test_word_bank_is_included_only_when_requested(
    quiz_state, image_path, tmp_path, compiled_versions
):
    build(quiz_state, image_path, output_dir=tmp_path, include_word_bank=True)
    build(quiz_state, image_path, output_dir=tmp_path, include_word_bank=False)

    with_bank, without_bank = (batch[0] for batch in compiled_versions)
    assert sorted(with_bank["word-bank"]) == ["Athens", "Sparta"]
    assert without_bank["word-bank"] == []
