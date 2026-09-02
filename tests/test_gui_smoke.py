"""Wiring checks for the window and its panels.

Not a substitute for using the app, but it catches the failure these panels
are most prone to: a callback renamed on one side of the boundary and not the
other, which a unit test of either half would miss. Skipped where there's no
display.
"""

import os

import pytest
from PIL import Image

pytest.importorskip("ttkbootstrap")

pytestmark = pytest.mark.skipif(
    not os.environ.get("DISPLAY") and os.name != "nt",
    reason="needs a display",
)


@pytest.fixture
def window():
    import ttkbootstrap as ttkb

    from map_quiz_maker.app import THEME
    from map_quiz_maker.gui.main_window import MainWindow

    root = ttkb.Window(themename=THEME)
    root.withdraw()  # never put a window on the user's screen during tests
    main = MainWindow(root)
    root.update()
    yield main
    root.destroy()


@pytest.fixture
def map_image(tmp_path):
    path = tmp_path / "map.png"
    Image.new("RGB", (800, 600), "white").save(path)
    return path


def rows(window):
    return window.answer_list_panel._rows


def test_window_opens_empty(window):
    assert window.doc.markers == []
    assert not window.doc.dirty
    assert "Load an image" in window.image_panel.status_label.cget("text")


def test_typing_an_answer_survives_adding_the_next_marker(window, map_image):
    """The stage 1 regression, now through the real panels."""
    window.image_panel.show_image(map_image)
    window.doc.set_image(map_image)

    window._add_marker(0.2, 0.3)
    first = window.doc.markers[0].id
    rows(window)[first].var.set("Athens")

    window._add_marker(0.6, 0.7)
    window.root.update()

    assert [m.answer for m in window.doc.markers] == ["Athens", ""]
    assert rows(window)[first].var.get() == "Athens"


def test_adding_a_marker_selects_and_focuses_its_row(window, map_image, monkeypatch):
    """So the teacher can click the map and just start typing."""
    window.image_panel.show_image(map_image)
    window.doc.set_image(map_image)

    # Tk defers focus_set on a withdrawn toplevel, so assert the window asks
    # for the focus rather than that the WM granted it.
    focused = []
    monkeypatch.setattr(window.answer_list_panel, "focus_marker", focused.append)

    window._add_marker(0.2, 0.3)
    window.root.update()

    marker_id = window.doc.markers[0].id
    assert window.selected_id == marker_id
    assert focused == [marker_id]
    assert marker_id in rows(window)


def test_selecting_a_marker_highlights_it_in_both_views(window, map_image):
    window.image_panel.show_image(map_image)
    window.doc.set_image(map_image)
    window._add_marker(0.2, 0.3)
    window._add_marker(0.6, 0.7)
    first, second = (m.id for m in window.doc.markers)

    window._select_marker(first)
    window.root.update()

    assert window.selected_id == first
    circle, _text = window.image_panel._marker_items[first]
    other_circle, _ = window.image_panel._marker_items[second]
    assert window.image_panel.canvas.itemcget(circle, "outline") != (
        window.image_panel.canvas.itemcget(other_circle, "outline")
    )


def test_deleting_a_row_removes_it_from_both_views(window, map_image):
    window.image_panel.show_image(map_image)
    window.doc.set_image(map_image)
    window._add_marker(0.2, 0.3)
    window._add_marker(0.6, 0.7)
    first = window.doc.markers[0].id

    rows(window)[first]._on_delete()
    window.root.update()

    assert first not in rows(window)
    assert first not in window.image_panel._marker_items
    assert [m.display_number for m in window.doc.markers] == [1]


def test_canvas_reconciles_rather_than_redrawing(window, map_image):
    """A marker's canvas items must survive a renumber, or a drag in progress
    would lose the thing being dragged."""
    window.image_panel.show_image(map_image)
    window.doc.set_image(map_image)
    window._add_marker(0.2, 0.3)
    window._add_marker(0.6, 0.7)
    second = window.doc.markers[1].id
    items_before = window.image_panel._marker_items[second]

    window._delete_marker(window.doc.markers[0].id)
    window.root.update()

    assert window.image_panel._marker_items[second] == items_before
    text = items_before[1]
    assert window.image_panel.canvas.itemcget(text, "text") == "1"


def test_undo_restores_a_deleted_marker_through_the_window(window, map_image):
    window.image_panel.show_image(map_image)
    window.doc.set_image(map_image)
    window._add_marker(0.2, 0.3)
    marker_id = window.doc.markers[0].id
    rows(window)[marker_id].var.set("Athens")

    window._delete_marker(marker_id)
    window.root.update()
    assert window.doc.markers == []

    window.undo()
    window.root.update()
    assert [m.answer for m in window.doc.markers] == ["Athens"]
    assert len(rows(window)) == 1


def test_metadata_fields_write_through_to_the_document(window):
    window.details_panel.entries["title"].insert(0, "Ancient Greece")
    window.details_panel._changed("title")

    assert window.doc.meta.title == "Ancient Greece"
    assert window.doc.dirty


def test_build_options_write_through_to_the_document(window):
    window.build_options_panel.word_bank_var.set(True)
    window.build_options_panel.num_versions_var.set(7)
    window.root.update()

    assert window.doc.meta.include_word_bank is True
    assert window.doc.meta.num_versions == 7


def test_title_shows_the_unsaved_marker(window, map_image):
    window.image_panel.show_image(map_image)
    window.doc.set_image(map_image)
    window._add_marker(0.2, 0.3)
    window.root.update()

    assert window.root.title().startswith("*")

    window.doc.mark_clean()
    window._refresh_title()
    assert not window.root.title().startswith("*")


def test_status_line_counts_locations_and_blanks(window, map_image):
    window.image_panel.show_image(map_image)
    window.doc.set_image(map_image)
    window._add_marker(0.2, 0.3)
    window._add_marker(0.6, 0.7)
    window.root.update()

    status = window.image_panel.status_label.cget("text")
    assert "2 locations" in status
    assert "2 still need answers" in status


def test_open_and_save_round_trip_through_the_window(window, map_image, tmp_path):
    from map_quiz_maker.etqw import save_document

    window.image_panel.show_image(map_image)
    window.doc.set_image(map_image)
    window._add_marker(0.25, 0.35)
    marker_id = window.doc.markers[0].id
    rows(window)[marker_id].var.set("Athens")
    window._meta_changed(title="Greece", class_name="Humanities IV")

    path = save_document(window.doc, tmp_path / "greek.etqw")
    window._open_path(path)
    window.root.update()

    assert window.doc.meta.title == "Greece"
    assert [m.answer for m in window.doc.markers] == ["Athens"]
    assert len(rows(window)) == 1
    assert len(window.image_panel._marker_items) == 1
    assert not window.doc.dirty
