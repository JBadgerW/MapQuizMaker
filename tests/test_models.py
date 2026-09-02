from map_quiz_maker.models import QuizDocument


def make_document(count=0):
    doc = QuizDocument()
    for n in range(count):
        doc.add_marker(0.1 * (n + 1), 0.2 * (n + 1))
    return doc


def test_renumber_after_middle_delete():
    doc = QuizDocument()
    doc.add_marker(0.1, 0.1)
    m2 = doc.add_marker(0.2, 0.2)
    doc.add_marker(0.3, 0.3)
    doc.add_marker(0.4, 0.4)

    doc.delete_marker(m2.id)

    assert [m.display_number for m in doc.markers] == [1, 2, 3]
    assert doc.add_marker(0.5, 0.5).display_number == 4


def test_renumber_after_first_delete():
    doc = QuizDocument()
    m1 = doc.add_marker(0.1, 0.1)
    m2 = doc.add_marker(0.2, 0.2)
    m3 = doc.add_marker(0.3, 0.3)

    doc.delete_marker(m1.id)

    assert [m.display_number for m in doc.markers] == [1, 2]
    assert [m.id for m in doc.markers] == [m2.id, m3.id]


def test_ids_are_never_reused():
    """A view keys its widgets by marker id, so a reused id would attach an
    old row to a new marker."""
    doc = QuizDocument()
    m1 = doc.add_marker(0.1, 0.1)
    doc.delete_marker(m1.id)
    assert doc.add_marker(0.2, 0.2).id != m1.id


def test_listener_notified_on_add_and_delete():
    doc = QuizDocument()
    calls = []
    doc.add_listener(lambda: calls.append(1))

    m1 = doc.add_marker(0.1, 0.1)
    doc.delete_marker(m1.id)

    assert len(calls) == 2


def test_typing_an_answer_does_not_notify():
    """A notification would rebuild the very row being typed into."""
    doc = QuizDocument()
    m = doc.add_marker(0.1, 0.1)
    calls = []
    doc.add_listener(lambda: calls.append(1))

    doc.update_answer(m.id, "Athens")

    assert calls == []
    assert doc.get_marker(m.id).answer == "Athens"
    assert doc.dirty


def test_move_marker_keeps_number_and_answer():
    doc = QuizDocument()
    m = doc.add_marker(0.1, 0.1)
    doc.update_answer(m.id, "Athens")

    doc.move_marker(m.id, 0.7, 0.8)

    moved = doc.get_marker(m.id)
    assert (moved.x, moved.y) == (0.7, 0.8)
    assert moved.answer == "Athens"
    assert moved.display_number == 1


def test_moving_to_the_same_place_is_not_a_change():
    doc = QuizDocument()
    m = doc.add_marker(0.4, 0.4)
    doc.mark_clean()

    doc.move_marker(m.id, 0.4, 0.4)

    assert not doc.dirty


def test_undo_restores_a_deleted_marker_with_its_answer():
    doc = QuizDocument()
    m = doc.add_marker(0.3, 0.3)
    doc.update_answer(m.id, "Athens")

    doc.delete_marker(m.id)
    assert doc.markers == []

    doc.undo()
    assert [(x.display_number, x.answer) for x in doc.markers] == [(1, "Athens")]


def test_undo_and_redo_round_trip_a_move():
    doc = QuizDocument()
    m = doc.add_marker(0.2, 0.2)
    doc.move_marker(m.id, 0.9, 0.9)

    doc.undo()
    assert (doc.get_marker(m.id).x, doc.get_marker(m.id).y) == (0.2, 0.2)

    doc.redo()
    assert (doc.get_marker(m.id).x, doc.get_marker(m.id).y) == (0.9, 0.9)


def test_a_new_edit_clears_the_redo_stack():
    doc = QuizDocument()
    doc.add_marker(0.1, 0.1)
    doc.undo()
    assert doc.can_redo

    doc.add_marker(0.5, 0.5)
    assert not doc.can_redo


def test_undo_is_a_no_op_with_no_history():
    doc = QuizDocument()
    doc.undo()
    assert doc.markers == []
    assert not doc.can_undo


def test_loading_an_image_clears_markers_but_can_keep_them(tmp_path):
    doc = QuizDocument()
    doc.add_marker(0.1, 0.1)

    doc.set_image(tmp_path / "a.png")
    assert doc.markers == []

    doc.add_marker(0.2, 0.2)
    doc.set_image(tmp_path / "b.png", keep_markers=True)
    assert len(doc.markers) == 1


def test_dirty_tracking():
    doc = QuizDocument()
    assert not doc.dirty

    doc.add_marker(0.1, 0.1)
    assert doc.dirty

    doc.mark_clean()
    assert not doc.dirty

    doc.update_meta(title="Greece")
    assert doc.dirty


def test_update_meta_ignores_a_no_op():
    doc = QuizDocument()
    doc.update_meta(title="Greece")
    doc.mark_clean()

    doc.update_meta(title="Greece")
    assert not doc.dirty


def test_answers_and_missing_answers():
    doc = QuizDocument()
    a = doc.add_marker(0.1, 0.1)
    doc.add_marker(0.2, 0.2)
    c = doc.add_marker(0.3, 0.3)
    doc.update_answer(a.id, "Athens")
    doc.update_answer(c.id, "  ")

    assert doc.answers() == ["Athens"]
    assert [m.display_number for m in doc.markers_missing_answers()] == [2, 3]
