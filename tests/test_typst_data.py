from dataclasses import dataclass

import typst

from map_quiz_maker.export.typst_data import (
    build_version_dict,
    escape_typst_string,
    versions_to_typst_source,
)


@dataclass
class FakeMarker:
    x: float
    y: float
    answer: str


def test_build_version_dict_shape():
    markers = [FakeMarker(1.0, 2.0, "Athens"), FakeMarker(3.0, 4.0, "Sparta")]

    result = build_version_dict(
        class_name="Humanities IV",
        title="Ancient Greece",
        version="1",
        instructions="Fill in the blanks.",
        image_filename="/tmp/map.jpg",
        image_width_cm=17.78,
        image_height_cm=13.0,
        markers=markers,
    )

    assert result["class"] == "Humanities IV"
    assert result["image"] == {"filename": "/tmp/map.jpg", "width-cm": 17.78, "height-cm": 13.0}
    assert result["markers"] == [
        {"display-number": 1, "x": 1.0, "y": 2.0, "answer": "Athens"},
        {"display-number": 2, "x": 3.0, "y": 4.0, "answer": "Sparta"},
    ]


def test_build_version_dict_word_bank_defaults_empty():
    result = build_version_dict("C", "T", "V", "I", "img.jpg", 1.0, 1.0, [])
    assert result["word-bank"] == []


def test_build_version_dict_word_bank_populated():
    result = build_version_dict(
        "C", "T", "V", "I", "img.jpg", 1.0, 1.0, [], word_bank=["Sparta", "Athens"]
    )
    assert result["word-bank"] == ["Sparta", "Athens"]


def test_escape_typst_string_handles_quotes_and_backslashes():
    assert escape_typst_string('Say "hi"') == 'Say \\"hi\\"'
    assert escape_typst_string("C:\\path") == "C:\\\\path"
    assert escape_typst_string('back\\"slash') == 'back\\\\\\"slash'


def test_versions_to_typst_source_escapes_adversarial_answers():
    markers = [FakeMarker(1.0, 1.0, 'Bob "The Builder"'), FakeMarker(2.0, 2.0, "back\\slash")]
    version = build_version_dict(
        class_name="C",
        title="T",
        version="V",
        instructions="I",
        image_filename="/tmp/map.jpg",
        image_width_cm=1.0,
        image_height_cm=1.0,
        markers=markers,
    )

    source = versions_to_typst_source([version])

    assert '\\"The Builder\\"' in source
    assert "back\\\\slash" in source
    # Sanity check the result is well-formed enough for a Typst dict literal:
    # every quote must be paired (escaped quotes don't count as delimiters).
    unescaped_quote_count = 0
    i = 0
    while i < len(source):
        if source[i] == "\\":
            i += 2
            continue
        if source[i] == '"':
            unescaped_quote_count += 1
        i += 1
    assert unescaped_quote_count % 2 == 0


def test_versions_to_typst_source_single_and_multi_element():
    v1 = build_version_dict("C", "T", "V", "I", "img.jpg", 1.0, 1.0, [])
    v2 = build_version_dict("C2", "T2", "V2", "I2", "img2.jpg", 1.0, 1.0, [])

    single = versions_to_typst_source([v1])
    multi = versions_to_typst_source([v1, v2])

    assert single.endswith(",)")
    assert multi.endswith(",)")


def test_escaped_adversarial_strings_are_valid_typst_source(tmp_path):
    """Lightweight parse-validity check: adversarial answer text must not
    break out of its string literal when compiled for real.
    """
    markers = [FakeMarker(1.0, 1.0, 'Quote " backslash \\ done')]
    version = build_version_dict("C\"lass", "Ti\\tle", "V", "I", "img.jpg", 1.0, 1.0, markers)
    source = versions_to_typst_source([version])

    typ_file = tmp_path / "check.typ"
    typ_file.write_text(f"#let versions = {source}\n#versions.at(0).markers.at(0).answer\n")

    # Raises typst.TypstError if the generated source isn't valid Typst.
    typst.compile(str(typ_file), output=str(tmp_path / "check.pdf"))
