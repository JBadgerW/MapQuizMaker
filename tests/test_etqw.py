"""The .etqw save format.

The round-trip tests run anywhere. The conformance tests at the bottom check
the bundle against the etqw project's own schemas and loader, and skip when
that project isn't checked out beside this one -- a real guarantee on a
machine that has both, rather than a vendored copy of schemas that would
drift out of date.
"""

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from map_quiz_maker.etqw import EtqwError, load_document, save_document
from map_quiz_maker.etqw.bundle import EXTENSION_KEY, STIMULUS_FILENAME
from map_quiz_maker.etqw.typst_text import escape_typst, unescape_typst
from map_quiz_maker.models import QuizDocument

ETQW_PROJECT = Path.home() / "GitHub" / "test_worksheet_generator"

needs_etqw_project = pytest.mark.skipif(
    not (ETQW_PROJECT / "src" / "twg" / "repository.py").is_file()
    or importlib.util.find_spec("jsonschema") is None,
    reason="needs the etqw project checked out and jsonschema installed",
)


@pytest.fixture
def image_path(tmp_path):
    path = tmp_path / "greece.png"
    Image.new("RGB", (800, 600), "white").save(path)
    return path


@pytest.fixture
def doc(image_path):
    document = QuizDocument()
    document.set_image(image_path)
    for x, y, answer in [(0.25, 0.30, "Athens"), (0.60, 0.55, "Sparta")]:
        marker = document.add_marker(x, y)
        document.update_answer(marker.id, answer)
    document.update_meta(
        class_name="Humanities IV",
        author="J. Watson",
        title="Ancient Greece: Ch. 4",
        instructions="Label each numbered location.",
        include_word_bank=True,
        num_versions=5,
    )
    return document


def read_subsection(bundle_path) -> dict:
    with zipfile.ZipFile(bundle_path) as archive:
        name = next(n for n in archive.namelist() if n.endswith("subsection.json"))
        return json.loads(archive.read(name))


# ---------------------------------------------------------------------------
# Round trip
# ---------------------------------------------------------------------------


def test_round_trip_preserves_everything(doc, tmp_path):
    save_document(doc, tmp_path / "greek.etqw")
    reloaded = load_document(tmp_path / "greek.etqw")

    assert reloaded.meta == doc.meta
    assert [(m.x, m.y, m.answer) for m in reloaded.markers] == [
        (m.x, m.y, m.answer) for m in doc.markers
    ]
    assert [m.display_number for m in reloaded.markers] == [1, 2]


def test_saving_marks_the_document_clean(doc, tmp_path):
    assert doc.dirty
    path = save_document(doc, tmp_path / "greek.etqw")

    assert not doc.dirty
    assert doc.file_path == path


def test_a_reloaded_document_starts_clean(doc, tmp_path):
    save_document(doc, tmp_path / "greek.etqw")
    assert not load_document(tmp_path / "greek.etqw").dirty


def test_identity_is_minted_once_and_kept(doc, tmp_path):
    save_document(doc, tmp_path / "a.etqw")
    first_id, created = doc.etqw_id, doc.created_at

    save_document(doc, tmp_path / "b.etqw")
    assert (doc.etqw_id, doc.created_at) == (first_id, created)
    assert load_document(tmp_path / "b.etqw").etqw_id == first_id


def test_answers_with_typst_specials_survive(doc, tmp_path):
    """Underscores would otherwise read as emphasis delimiters and vanish."""
    tricky = ["Rub_al-Khali", "Cape #3", "-Delta", "a*b$c"]
    for marker, answer in zip(doc.markers, tricky):
        doc.update_answer(marker.id, answer)
    for x, y in [(0.1, 0.1), (0.2, 0.2)]:
        doc.update_answer(doc.add_marker(x, y).id, tricky[len(doc.markers) - 1])

    save_document(doc, tmp_path / "tricky.etqw")
    reloaded = load_document(tmp_path / "tricky.etqw")

    assert [m.answer for m in reloaded.markers] == [
        m.answer for m in doc.markers
    ]


def test_escaping_round_trips():
    for text in ["Athens", "Rub_al-Khali", "Cape #3", "-Delta", "a*b$c", "back\\slash"]:
        assert unescape_typst(escape_typst(text)) == text


def test_an_interrupted_save_leaves_no_partial_file(doc, tmp_path, monkeypatch):
    target = tmp_path / "greek.etqw"
    save_document(doc, target)
    good = target.read_bytes()

    def explode(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("map_quiz_maker.etqw.bundle.render_marked_image", explode)
    with pytest.raises(OSError):
        save_document(doc, target)

    assert target.read_bytes() == good, "the previous save must survive"
    assert not list(tmp_path.glob("*.writing"))


# ---------------------------------------------------------------------------
# Bundle shape
# ---------------------------------------------------------------------------


def test_bundle_layout(doc, tmp_path):
    path = save_document(doc, tmp_path / "greek.etqw")

    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()

    assert "manifest.json" in names
    assert any(n.endswith("/section.json") for n in names)
    assert any(n.endswith("/subsection.json") for n in names)
    assert any(n.endswith(f"/media/{STIMULUS_FILENAME}") for n in names)
    assert any("/media/map-source." in n for n in names)


def test_questions_carry_answers_inline_as_blank_markers(doc, tmp_path):
    save_document(doc, tmp_path / "greek.etqw")
    subsection = read_subsection(tmp_path / "greek.etqw")

    assert subsection["type"] == "fill_in_the_blank"
    assert [q["stem"] for q in subsection["content"]] == ["{{Athens}}", "{{Sparta}}"]
    assert all(q["type"] == "fill_in_the_blank" for q in subsection["content"])


def test_word_bank_checkbox_maps_to_show_word_bank(doc, tmp_path):
    save_document(doc, tmp_path / "on.etqw")
    assert read_subsection(tmp_path / "on.etqw")["show_word_bank"] is True

    doc.update_meta(include_word_bank=False)
    save_document(doc, tmp_path / "off.etqw")
    assert read_subsection(tmp_path / "off.etqw")["show_word_bank"] is False


def test_marker_positions_ride_in_the_extension(doc, tmp_path):
    save_document(doc, tmp_path / "greek.etqw")
    extension = read_subsection(tmp_path / "greek.etqw")["stimulus"][EXTENSION_KEY]

    assert extension["markers"] == [{"x": 0.25, "y": 0.30}, {"x": 0.60, "y": 0.55}]
    assert extension["source_image"].startswith("map-source")
    assert extension["options"]["num_versions"] == 5


def test_saving_without_an_image_is_refused():
    with pytest.raises(EtqwError, match="no map image"):
        save_document(QuizDocument(), "unused.etqw")


# ---------------------------------------------------------------------------
# Rejecting what can't be opened
# ---------------------------------------------------------------------------


def test_a_non_zip_is_rejected(tmp_path):
    path = tmp_path / "notes.etqw"
    path.write_text("this is not a bundle")
    with pytest.raises(EtqwError, match="doesn't look like"):
        load_document(path)


def test_a_document_without_marker_positions_explains_why(doc, tmp_path):
    """What a bundle looks like after the etqw app re-saves it: valid etqw,
    but the extension carrying the coordinates is gone."""
    path = save_document(doc, tmp_path / "greek.etqw")
    stripped = tmp_path / "stripped.etqw"

    with zipfile.ZipFile(path) as source, zipfile.ZipFile(stripped, "w") as target:
        for item in source.namelist():
            data = source.read(item)
            if item.endswith("subsection.json"):
                subsection = json.loads(data)
                del subsection["stimulus"][EXTENSION_KEY]
                data = json.dumps(subsection).encode()
            target.writestr(item, data)

    with pytest.raises(EtqwError, match="no marker positions"):
        load_document(stripped)


def test_a_foreign_subsection_type_is_refused(doc, tmp_path):
    path = save_document(doc, tmp_path / "greek.etqw")
    changed = tmp_path / "essay.etqw"

    with zipfile.ZipFile(path) as source, zipfile.ZipFile(changed, "w") as target:
        for item in source.namelist():
            data = source.read(item)
            if item.endswith("subsection.json"):
                subsection = json.loads(data)
                subsection["type"] = "essay"
                data = json.dumps(subsection).encode()
            target.writestr(item, data)

    with pytest.raises(EtqwError, match="essay"):
        load_document(changed)


# ---------------------------------------------------------------------------
# Conformance against the real etqw project
# ---------------------------------------------------------------------------


@needs_etqw_project
def test_the_etqw_app_can_load_and_validate_the_bundle(doc, tmp_path, monkeypatch):
    """load_bundle runs the etqw project's own JSON-schema validation."""
    monkeypatch.syspath_prepend(str(ETQW_PROJECT / "src"))
    from twg import repository

    path = save_document(doc, tmp_path / "greek.etqw")
    loaded = repository.load_bundle(path).doc

    assert loaded.type == "quiz"
    assert loaded.title == "Ancient Greece: Ch. 4"
    assert loaded.course == "Humanities IV"
    assert loaded.author == "J. Watson"

    [section] = loaded.sections
    [subsection] = section.subsections
    assert subsection.type == "fill_in_the_blank"
    assert subsection.show_word_bank is True
    assert subsection.stimulus.kind == "image"
    assert subsection.stimulus.path == STIMULUS_FILENAME
    assert [q.answers() for q in subsection.content] == [["Athens"], ["Sparta"]]


@needs_etqw_project
def test_the_etqw_app_renders_it_to_a_pdf(doc, tmp_path, monkeypatch):
    """The end-to-end guarantee: a quiz saved here prints from the other app."""
    monkeypatch.syspath_prepend(str(ETQW_PROJECT / "src"))
    from twg.render import render_bundle_obj
    from twg.repository import load_bundle

    path = save_document(doc, tmp_path / "greek.etqw")
    pdf = render_bundle_obj(load_bundle(path), tmp_path / "rendered.pdf")

    pdf = Path(pdf)
    assert pdf.is_file() and pdf.stat().st_size > 0
