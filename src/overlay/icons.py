"""Iconos de Twitch, Kick, TikTok y YouTube: se leen de los SVG oficiales en
src/svg/ (subidos por el usuario), se escalan segun su viewBox y se centran
dentro del cuadrado de ICON px.

Al ser los logos oficiales, cualquier reemplazo de esos archivos tiene que
respetar la guia de marca de cada plataforma. Ver CLAUDE.md #6.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET

from .constants import ICON, INK

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SVG_DIR = os.path.join(BASE, "svg")

ET.register_namespace("", "http://www.w3.org/2000/svg")

_cache: dict[str, tuple[float, float, str]] = {}


def _load(name: str) -> tuple[float, float, str]:
    """Lee un SVG de src/svg/: (ancho, alto) de su viewBox y su contenido."""
    if name not in _cache:
        root = ET.parse(os.path.join(SVG_DIR, f"{name}.svg")).getroot()
        _, _, w, h = (float(v) for v in root.get("viewBox").split())
        parts = []
        for el in root:
            tag = el.tag.rsplit("}", 1)[-1]
            if tag in ("title", "desc", "defs"):
                continue
            parts.append(ET.tostring(el, encoding="unicode"))
        _cache[name] = (w, h, "".join(parts))
    return _cache[name]


def _icon(name: str, x: float, y: float, bg: str | None,
          content_ratio: float = 0.64) -> str:
    vb_w, vb_h, markup = _load(name)
    box = ICON * content_ratio
    scale = box / max(vb_w, vb_h)
    ox = (ICON - vb_w * scale) / 2
    oy = (ICON - vb_h * scale) / 2
    back = f'<rect width="{ICON}" height="{ICON}" rx="19" fill="{bg}"/>' if bg else ""
    return (f'<g transform="translate({x:.1f},{y:.1f})">'
            f'{back}'
            f'<g transform="translate({ox:.2f},{oy:.2f}) scale({scale:.5f})">{markup}</g>'
            f'</g>')


def twitch_icon(x: float, y: float) -> str:
    return _icon("twitch-icon", x, y, bg="#FFFFFF")


def kick_icon(x: float, y: float) -> str:
    return _icon("kick-icon", x, y, bg=INK)


def tiktok_icon(x: float, y: float) -> str:
    return _icon("tiktok-icon", x, y, bg="#FFFFFF")


def youtube_icon(x: float, y: float) -> str:
    return _icon("youtube-icon", x, y, bg="#FFFFFF", content_ratio=0.88)
