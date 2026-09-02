"""Build failures must arrive as sentences, not as raw exception text."""

import typst
from PIL import UnidentifiedImageError

from map_quiz_maker.gui.build_errors import describe


def test_an_unreadable_image_says_what_to_do():
    message = describe(UnidentifiedImageError("cannot identify image file"))
    assert "PNG or JPEG" in message
    assert "cannot identify" not in message, "raw library text isn't useful here"


def test_a_missing_map_is_named_as_the_map():
    exc = FileNotFoundError(2, "No such file or directory")
    exc.filename = "/home/jon/maps/greece.jpg"

    message = describe(exc, image_path="/home/jon/maps/greece.jpg")

    assert "map image has moved" in message
    assert "/home/jon/maps/greece.jpg" in message


def test_another_missing_file_is_not_blamed_on_the_map():
    exc = FileNotFoundError(2, "No such file or directory")
    exc.filename = "/tmp/something-else.typ"

    message = describe(exc, image_path="/home/jon/maps/greece.jpg")

    assert "map image has moved" not in message
    assert "/tmp/something-else.typ" in message


def test_permission_denied_suggests_the_likely_cause():
    exc = PermissionError(13, "Permission denied")
    exc.filename = "/read-only/quiz.pdf"

    message = describe(exc)

    assert "isn't allowed to write" in message
    assert "viewer" in message, "an open PDF is the usual cause on Windows"


def test_a_full_disk_is_reported_plainly():
    exc = OSError(28, "No space left on device")
    assert "disk space" in describe(exc)


def test_a_typst_failure_keeps_its_message():
    message = describe(typst.TypstError("expected expression"))
    assert "expected expression" in message
    assert "Typst couldn't lay out" in message


def test_an_unknown_failure_still_shows_something():
    message = describe(RuntimeError("something odd"))
    assert "something odd" in message
