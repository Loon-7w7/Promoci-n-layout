"""Iconos de Twitch y Kick: formas geometricas propias, no los logos oficiales.

Si se cambian por los oficiales, hay que bajarlos de la guia de marca de cada
plataforma y respetar sus reglas de uso. Ver CLAUDE.md #6.
"""

from __future__ import annotations

from .constants import ICON, VIOLET_DEEP, GREEN, INK


def twitch_icon(x: float, y: float) -> str:
    s = ICON / 100.0 * 0.64
    return (f'<g transform="translate({x:.1f},{y:.1f})">'
            f'<rect width="{ICON}" height="{ICON}" rx="19" fill="#FFFFFF"/>'
            f'<g transform="translate({ICON*0.18:.1f},{ICON*0.18:.1f}) scale({s:.4f})">'
            f'<rect x="12" y="14" width="76" height="52" rx="10" fill="{VIOLET_DEEP}"/>'
            f'<polygon points="32,66 32,89 55,66" fill="{VIOLET_DEEP}"/>'
            f'<rect x="40" y="28" width="9" height="25" rx="4.5" fill="#FFFFFF"/>'
            f'<rect x="57" y="28" width="9" height="25" rx="4.5" fill="#FFFFFF"/>'
            f'</g></g>')


def kick_icon(x: float, y: float) -> str:
    s = ICON / 100.0 * 0.64
    return (f'<g transform="translate({x:.1f},{y:.1f})">'
            f'<rect width="{ICON}" height="{ICON}" rx="19" fill="{GREEN}"/>'
            f'<g transform="translate({ICON*0.18:.1f},{ICON*0.18:.1f}) scale({s:.4f})">'
            f'<rect x="23" y="18" width="18" height="64" fill="{INK}"/>'
            f'<rect x="41" y="36" width="18" height="28" fill="{INK}"/>'
            f'<rect x="59" y="18" width="18" height="18" fill="{INK}"/>'
            f'<rect x="59" y="64" width="18" height="18" fill="{INK}"/>'
            f'</g></g>')
