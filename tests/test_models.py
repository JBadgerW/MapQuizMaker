from map_quiz_maker.models import QuizState


def test_renumber_after_middle_delete():
    state = QuizState()
    state.add_marker(1, 1)
    m2 = state.add_marker(2, 2)
    state.add_marker(3, 3)
    state.add_marker(4, 4)

    state.delete_marker(m2.id)

    assert [m.display_number for m in state.markers] == [1, 2, 3]

    m5 = state.add_marker(5, 5)
    assert m5.display_number == 4


def test_renumber_after_first_delete():
    state = QuizState()
    m1 = state.add_marker(1, 1)
    m2 = state.add_marker(2, 2)
    m3 = state.add_marker(3, 3)

    state.delete_marker(m1.id)

    assert [m.display_number for m in state.markers] == [1, 2]
    assert [m.id for m in state.markers] == [m2.id, m3.id]


def test_renumber_after_last_delete():
    state = QuizState()
    m1 = state.add_marker(1, 1)
    m2 = state.add_marker(2, 2)
    m3 = state.add_marker(3, 3)

    state.delete_marker(m3.id)

    assert [m.display_number for m in state.markers] == [1, 2]
    assert [m.id for m in state.markers] == [m1.id, m2.id]


def test_delete_all_then_add():
    state = QuizState()
    m1 = state.add_marker(1, 1)
    m2 = state.add_marker(2, 2)

    state.delete_marker(m1.id)
    state.delete_marker(m2.id)

    assert state.markers == []

    m3 = state.add_marker(3, 3)
    assert m3.display_number == 1


def test_reset_clears_markers_and_numbering():
    state = QuizState()
    state.add_marker(1, 1)
    state.add_marker(2, 2)

    state.reset()

    assert state.markers == []
    m = state.add_marker(9, 9)
    assert m.id == 1
    assert m.display_number == 1


def test_listener_notified_on_add_and_delete():
    state = QuizState()
    calls = []
    state.add_listener(lambda: calls.append(1))

    m1 = state.add_marker(1, 1)
    state.delete_marker(m1.id)

    assert len(calls) == 2


def test_update_answer_sets_value():
    state = QuizState()
    m1 = state.add_marker(1, 1)
    state.update_answer(m1.id, "Athens")
    assert state.get_marker(m1.id).answer == "Athens"
