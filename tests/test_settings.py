import json

import pytest

from map_quiz_maker import config, settings


@pytest.fixture
def settings_file(tmp_path, monkeypatch):
    path = tmp_path / "cfg" / "settings.json"
    monkeypatch.setattr(config, "settings_path", lambda: path)
    monkeypatch.setattr(settings, "settings_path", lambda: path)
    return path


def test_output_dir_defaults_to_an_absolute_path_under_home(settings_file):
    """A relative default resolves against the working directory, which is
    how finished quizzes previously ended up in unfindable folders."""
    result = settings.get_output_dir()
    assert result.is_absolute()
    assert result.parts[-1] == config.DEFAULT_OUTPUT_DIR_NAME


def test_remembers_the_last_used_folder(settings_file, tmp_path):
    chosen = tmp_path / "Quizzes"
    chosen.mkdir()

    settings.set_output_dir(chosen)

    assert settings.get_output_dir() == chosen
    assert json.loads(settings_file.read_text())["last_output_dir"] == str(chosen)


def test_forgets_a_folder_that_no_longer_exists(settings_file, tmp_path):
    gone = tmp_path / "on-a-usb-stick"
    gone.mkdir()
    settings.set_output_dir(gone)
    gone.rmdir()

    assert settings.get_output_dir() == config.default_output_dir()


@pytest.mark.parametrize("contents", ["", "not json", "[]", '{"last_output_dir": 7}'])
def test_a_corrupt_settings_file_never_breaks_the_app(settings_file, contents):
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(contents)

    assert settings.get_output_dir() == config.default_output_dir()


def test_writing_settings_survives_an_unwritable_location(tmp_path, monkeypatch):
    blocked = tmp_path / "nope"
    blocked.write_text("I am a file, not a directory")
    monkeypatch.setattr(settings, "settings_path", lambda: blocked / "settings.json")

    settings.set_output_dir(tmp_path)  # must not raise
