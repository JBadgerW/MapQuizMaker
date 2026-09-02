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


# ---------------------------------------------------------------------------
# The threaded build
# ---------------------------------------------------------------------------


def test_progress_dialog_runs_a_build_on_a_worker_thread(window):
    """Tk is not thread-safe, so the build must not touch widgets itself."""
    import threading

    from map_quiz_maker.gui.build_progress_dialog import BuildProgressDialog

    ran_on = {}

    def work(on_progress, _should_cancel):
        ran_on["thread"] = threading.current_thread()
        on_progress(0, 2, "Building the worksheet...")
        on_progress(1, 2, "Building the answer key...")
        return ["a.pdf", "b.pdf"]

    result = BuildProgressDialog(window.root, work).run()

    assert result == ["a.pdf", "b.pdf"]
    assert ran_on["thread"] is not threading.main_thread()


def test_progress_dialog_reraises_a_failed_build(window):
    from map_quiz_maker.gui.build_progress_dialog import BuildProgressDialog

    def work(_on_progress, _should_cancel):
        raise OSError("disk full")

    with pytest.raises(OSError, match="disk full"):
        BuildProgressDialog(window.root, work).run()


def test_cancelling_returns_no_paths(window):
    import time

    from map_quiz_maker.export.typst_build import BuildCancelled
    from map_quiz_maker.gui.build_progress_dialog import BuildProgressDialog

    def work(on_progress, should_cancel):
        on_progress(0, 3, "Building version 1 of 3...")
        for _ in range(400):  # a bounded wait, so a bug fails instead of hanging
            if should_cancel():
                raise BuildCancelled
            time.sleep(0.01)
        return ["never.pdf"]

    dialog = BuildProgressDialog(window.root, work)
    # Scheduled from the main thread, which is where every widget call belongs.
    dialog.dialog.after(80, dialog.cancel)

    assert dialog.run() is None


def test_the_dialog_closes_itself_when_the_build_finishes(window):
    from map_quiz_maker.gui.build_progress_dialog import BuildProgressDialog

    dialog = BuildProgressDialog(window.root, lambda *_: ["a.pdf"])
    dialog.run()

    assert not dialog.dialog.winfo_exists()


def test_a_real_build_writes_a_worksheet_and_a_separate_key(
    window, map_image, tmp_path, monkeypatch
):
    """The whole path: window -> progress dialog -> worker thread -> Typst."""
    from map_quiz_maker.gui import main_window

    shown = []
    # The result dialog is modal and would wait for a click that never comes.
    monkeypatch.setattr(main_window, "show_build_result", lambda _root, paths: shown.append(paths))

    window.image_panel.show_image(map_image)
    window.doc.set_image(map_image)
    window.doc.update_answer(window.doc.add_marker(0.3, 0.4).id, "Athens")
    window._meta_changed(title="Greece", num_versions=2)

    window._build(output_dir=tmp_path, filename_stem="greece")
    window.root.update()

    assert sorted(p.name for p in tmp_path.glob("*.pdf")) == [
        "greece.pdf",
        "greece_KEY.pdf",
    ]
    assert shown, "the user must be told where the quiz went"


def test_a_build_failure_reaches_the_user_as_a_message(
    window, map_image, tmp_path, monkeypatch
):
    from map_quiz_maker.gui import main_window

    errors = []
    monkeypatch.setattr(
        main_window.messagebox,
        "showerror",
        lambda _title, message, **_kw: errors.append(message),
    )
    monkeypatch.setattr(
        main_window, "build_quiz", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full"))
    )

    window.image_panel.show_image(map_image)
    window.doc.set_image(map_image)
    window.doc.update_answer(window.doc.add_marker(0.3, 0.4).id, "Athens")

    window._build(output_dir=tmp_path, filename_stem="greece")
    window.root.update()

    assert errors and "disk full" in errors[0]
