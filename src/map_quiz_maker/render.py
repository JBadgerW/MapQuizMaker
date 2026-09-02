"""Drawing numbered markers onto a copy of the map image.

The etqw format has no notion of a marker: `Stimulus` is an image with a
path and a width, and the etqw renderer draws it as-is. So the image that
travels in an etqw bundle has to arrive with its numbers already on it.

The clean source image travels alongside it, which is what lets Map Quiz
Maker reopen the document and move a marker.
"""

from importlib.resources import as_file
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Marker size scales with the image so it stays proportionate when the map is
# printed at a fixed width, with a floor for very small images.
MARKER_RADIUS_FRACTION = 0.016
MIN_MARKER_RADIUS = 9

FILL = (255, 255, 255, 235)
EDGE = (192, 57, 43, 255)
TEXT = (192, 57, 43, 255)
EDGE_WIDTH_FRACTION = 0.18

_FONT_RESOURCE_ANCHOR = "map_quiz_maker.assets.fonts"
_FONT_FILENAME = "LinLibertine_RB.otf"


def _load_font(size: int):
    """The bundled bold face, falling back to PIL's default.

    The fallback only matters if the bundled fonts are somehow unavailable;
    it keeps export working rather than failing over a label.
    """
    from importlib.resources import files

    try:
        with as_file(files(_FONT_RESOURCE_ANCHOR) / _FONT_FILENAME) as path:
            return ImageFont.truetype(str(path), size)
    except (OSError, ModuleNotFoundError):
        return ImageFont.load_default()


def render_marked_image(source_path, markers, destination_path) -> Path:
    """Writes a copy of `source_path` with each marker's number drawn on it.

    Marker x/y are fractions of the image (top-left origin), so the same
    numbers place labels here and in the Typst worksheet.
    """
    destination_path = Path(destination_path)

    with Image.open(source_path) as opened:
        base = opened.convert("RGBA")

    width, height = base.size
    radius = max(MIN_MARKER_RADIUS, round(min(width, height) * MARKER_RADIUS_FRACTION))
    edge_width = max(1, round(radius * EDGE_WIDTH_FRACTION))
    font = _load_font(max(8, round(radius * 1.35)))

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for marker in markers:
        cx = marker.x * width
        cy = marker.y * height
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=FILL, outline=EDGE, width=edge_width,
        )
        draw.text((cx, cy), str(marker.display_number), font=font, fill=TEXT, anchor="mm")

    combined = Image.alpha_composite(base, overlay)

    # JPEG has no alpha channel; flatten onto white for those, keep RGBA for
    # formats that support it so the map's own transparency survives.
    if destination_path.suffix.lower() in {".jpg", ".jpeg"}:
        flattened = Image.new("RGB", combined.size, (255, 255, 255))
        flattened.paste(combined, mask=combined.split()[3])
        flattened.save(destination_path)
    else:
        combined.save(destination_path)

    return destination_path
