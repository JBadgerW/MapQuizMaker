import pytest

from map_quiz_maker.export.naming import (
    FALLBACK_STEM,
    MAX_STEM_LENGTH,
    sanitize_filename,
)


def test_replaces_whitespace_with_underscores():
    assert sanitize_filename("Humanities IV Greek") == "Humanities_IV_Greek"
    assert sanitize_filename("A\tB\nC") == "A_B_C"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Rivers/Mountains", "Rivers_Mountains"),
        ("Rivers\\Mountains", "Rivers_Mountains"),
        ("Ch. 4: Greece", "Ch_4_Greece"),
        ("Quiz *v2*", "Quiz_v2"),
        ("Q1 | Q2", "Q1_Q2"),
    ],
)
def test_strips_characters_that_are_illegal_in_a_path(text, expected):
    """A title a teacher would plausibly type must not reach the filesystem
    as a separator, a drive-letter colon, or a Windows-reserved character."""
    result = sanitize_filename(text)
    assert result == expected
    assert not set(result) & set('/\\:*?"<>|')


def test_cannot_produce_a_traversal_or_a_dotfile():
    assert sanitize_filename("../../etc/passwd") == "etc_passwd"
    assert sanitize_filename(".hidden") == "hidden"
    assert not sanitize_filename("...").startswith(".")


@pytest.mark.parametrize("text", ["", "   ", "___", "...", "///", "\t\n"])
def test_falls_back_rather_than_returning_an_empty_stem(text):
    """An empty stem would write ".pdf" -- a hidden file the user never finds."""
    assert sanitize_filename(text) == FALLBACK_STEM


def test_truncates_and_never_leaves_trailing_separators():
    result = sanitize_filename("Greece " * 200)
    assert len(result) <= MAX_STEM_LENGTH
    assert not result.endswith(("_", "-", " "))


def test_collapses_runs_of_separators():
    assert sanitize_filename("A   ---   B") == "A_---_B"
    assert sanitize_filename("A___B") == "A_B"
