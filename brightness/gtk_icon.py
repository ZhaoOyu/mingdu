"""GTK symbolic quota-style brightness ring with native font outlines."""
from hashlib import sha256
from pathlib import Path
import tempfile

import cairo

from .presentation import ring_svg


def text_outline(text, center, baseline, size):
    context = cairo.Context(cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, None))
    context.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    context.set_font_size(size)
    bounds = context.text_extents(text)
    context.move_to(center - bounds.x_bearing - bounds.width / 2, baseline)
    context.text_path(text)
    commands = {cairo.PATH_MOVE_TO: "M", cairo.PATH_LINE_TO: "L",
                cairo.PATH_CURVE_TO: "C", cairo.PATH_CLOSE_PATH: "Z"}
    path = " ".join(commands[kind] + " ".join(f"{value:.4f}" for value in points)
                    for kind, points in context.copy_path())
    return f'<path d="{path}"/>'


class IconCache:
    def __init__(self):
        self.directory = tempfile.TemporaryDirectory(prefix="mingdu-icons-")
        self.paths = []

    def path(self, summary):
        svg = ring_svg(summary, text_outline)
        path = Path(self.directory.name) / ("mingdu-" + sha256(svg.encode()).hexdigest()[:16] + "-symbolic.svg")
        if path not in self.paths:
            path.write_text(svg)
        else:
            self.paths.remove(path)
        self.paths.append(path)
        if len(self.paths) > 64:
            self.paths.pop(0).unlink(missing_ok=True)
        return path

    def close(self):
        self.directory.cleanup()
