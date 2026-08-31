"""Texto convertido a trazos con fontTools. Ver CLAUDE.md #4.1.

No se usa <text> en ningun lado del SVG: measure() y text_path() son la unica
puerta de entrada a las fuentes, asi que el render no depende de que Poppins
este instalada en el sistema.
"""

from __future__ import annotations

import os

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(BASE, "fonts")
FONTS = {
    "bold": os.path.join(FONT_DIR, "Poppins-Bold.ttf"),
    "medium": os.path.join(FONT_DIR, "Poppins-Medium.ttf"),
    "light": os.path.join(FONT_DIR, "Poppins-Light.ttf"),
}

_cache: dict[str, tuple] = {}


def _load(weight: str):
    if weight not in _cache:
        f = TTFont(FONTS[weight])
        _cache[weight] = (f, f.getGlyphSet(), f["cmap"].getBestCmap(),
                          f["head"].unitsPerEm, f["hmtx"])
    return _cache[weight]


def measure(text: str, weight: str, size: float, tracking: float = 0.0) -> float:
    _, _, cmap, upem, hmtx = _load(weight)
    total = 0.0
    for ch in text:
        g = cmap.get(ord(ch))
        if g is None:
            continue
        total += hmtx[g][0] * size / upem + tracking
    return max(0.0, total - (tracking if text else 0))


def text_path(text: str, weight: str, size: float, x: float, y: float,
              tracking: float = 0.0, anchor: str = "start") -> str:
    """Devuelve los <path> del texto, con la linea base en y."""
    _, gs, cmap, upem, hmtx = _load(weight)
    scale = size / upem
    if anchor == "middle":
        x -= measure(text, weight, size, tracking) / 2
    elif anchor == "end":
        x -= measure(text, weight, size, tracking)
    out, cursor = [], x
    for ch in text:
        g = cmap.get(ord(ch))
        if g is None:
            continue
        pen = SVGPathPen(gs)
        gs[g].draw(pen)
        d = pen.getCommands()
        if d:
            out.append(f'<path transform="translate({cursor:.2f},{y:.2f}) '
                       f'scale({scale:.5f},{-scale:.5f})" d="{d}"/>')
        cursor += hmtx[g][0] * scale + tracking
    return "".join(out)
