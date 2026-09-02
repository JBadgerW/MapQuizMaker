"""Guards on how the app is distributed.

The template used to be resolved by walking up from ``__file__`` to the repo
root, and was not shipped in the wheel at all, so an installed copy could not
build a quiz. These tests fail if either half of that regresses.
"""

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from map_quiz_maker.export import typst_build

EXPECTED_FONTS = {
    "LinLibertine_R.otf",
    "LinLibertine_RB.otf",
    "LinLibertine_RI.otf",
    "LinLibertine_RBI.otf",
}


def test_template_is_readable_as_a_package_resource():
    source = typst_build.TEMPLATE_RESOURCE.read_text(encoding="utf-8")
    assert "#let render(" in source


def test_every_font_face_the_template_needs_is_bundled():
    """Regular, bold and italic are all used by the worksheet; a missing face
    is filled in silently by a fallback, which is the bug being prevented."""
    bundled = {p.name for p in typst_build.FONTS_RESOURCE.iterdir()}

    assert EXPECTED_FONTS <= bundled
    assert "LICENSE.txt" in bundled, "redistributed fonts must carry their licence"


def test_assets_live_inside_the_package_directory():
    """Hatchling ships whatever sits under the package directory, so this is
    what makes the assets land in the wheel."""
    package_root = Path(typst_build.__file__).resolve().parents[1]

    for resource in (typst_build.TEMPLATE_RESOURCE, typst_build.FONTS_RESOURCE):
        assert Path(str(resource)).resolve().is_relative_to(package_root)


@pytest.mark.skipif(shutil.which("uv") is None, reason="needs uv to build a wheel")
def test_the_built_wheel_contains_the_template_and_fonts(tmp_path):
    project_root = Path(typst_build.__file__).resolve().parents[3]

    subprocess.run(
        ["uv", "build", "--wheel", "-o", str(tmp_path)],
        cwd=project_root,
        check=True,
        capture_output=True,
    )

    [wheel] = tmp_path.glob("*.whl")
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

    assert "map_quiz_maker/assets/quiz_template.typ" in names
    for font in EXPECTED_FONTS:
        assert f"map_quiz_maker/assets/fonts/{font}" in names


@pytest.mark.skipif(shutil.which("uv") is None, reason="needs uv to build a wheel")
def test_an_installed_copy_can_build_a_quiz(tmp_path):
    """The end-to-end guard: install the wheel into a clean environment with
    no repo on sys.path, and compile a one-marker quiz with it."""
    project_root = Path(typst_build.__file__).resolve().parents[3]
    dist = tmp_path / "dist"
    venv = tmp_path / "venv"

    def uv(*args, **kwargs):
        subprocess.run(["uv", *args], check=True, capture_output=True, **kwargs)

    uv("build", "--wheel", "-o", str(dist), cwd=project_root)
    uv("venv", "-p", f"{sys.version_info.major}.{sys.version_info.minor}", str(venv))
    [wheel] = dist.glob("*.whl")

    python = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    uv("pip", "install", "--python", str(python), str(wheel))

    script = tmp_path / "build_a_quiz.py"
    script.write_text(
        "import map_quiz_maker\n"
        "from pathlib import Path\n"
        "from PIL import Image\n"
        "from map_quiz_maker.export.typst_build import build_quiz\n"
        "from map_quiz_maker.models import QuizState\n"
        "assert 'site-packages' in map_quiz_maker.__file__, map_quiz_maker.__file__\n"
        f"out = Path({str(tmp_path / 'quizzes')!r})\n"
        f"img = Path({str(tmp_path / 'map.png')!r})\n"
        "Image.new('RGB', (600, 450), 'white').save(img)\n"
        "state = QuizState()\n"
        "marker = state.add_marker(4.0, 6.0)\n"
        "state.update_answer(marker.id, 'Athens')\n"
        "[pdf] = build_quiz(quiz_state=state, image_file_path=img,\n"
        "    image_width_cm=17.78, image_height_cm=13.34,\n"
        "    class_name='Humanities IV', title='Ancient Greece',\n"
        "    instructions='Label each numbered location.', output_dir=out)\n"
        "print(pdf)\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [str(python), str(script)], check=True, capture_output=True, text=True
    )

    pdf = Path(result.stdout.strip().splitlines()[-1])
    assert pdf.is_file() and pdf.stat().st_size > 0
    assert b"LinLibertine" in pdf.read_bytes()
