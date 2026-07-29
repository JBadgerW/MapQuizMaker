from map_quiz_maker.export.naming import sanitize_filename


def test_sanitize_filename_replaces_whitespace():
    assert sanitize_filename("Humanities IV Greek") == "Humanities_IV_Greek"
    assert sanitize_filename("A\tB\nC") == "A_B_C"
