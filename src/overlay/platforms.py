"""Registro de las plataformas soportadas: icono, color y textos de cada una.

Config.active() (ver config.py) devuelve como maximo dos, en el orden de
PLATFORM_ORDER (constants.py). svg.py asigna la primera al lado izquierdo de
la barra y la segunda al derecho; con una sola, ocupa toda la barra.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .constants import (
    VIOLET, VIOLET_SOFT, GREEN, GREEN_DEEP, TIKTOK, TIKTOK_DEEP,
    YOUTUBE, YOUTUBE_DEEP, YOUTUBE_SOFT,
)
from .icons import twitch_icon, kick_icon, tiktok_icon, youtube_icon


@dataclass(frozen=True)
class Platform:
    label: str                       # nombre visible en la interfaz
    url: str                         # dominio que se dibuja bajo el icono
    icon: Callable[[float, float], str]
    color: str                       # acento: borde y tinte de la barra
    edge_light: str                  # extremo claro del degradado del borde
    edge_dark: str                   # extremo oscuro (solo si queda a la derecha)
    tint_opacity: float              # opacidad del tinte de color sobre la barra
    text_white: bool                 # True: nombre/url en blanco. False: en su color.


PLATFORMS: dict[str, Platform] = {
    "twitch": Platform("Twitch", "twitch.tv", twitch_icon,
                        VIOLET, VIOLET_SOFT, VIOLET, 0.40, True),
    "kick": Platform("Kick", "kick.com", kick_icon,
                      GREEN, GREEN, GREEN_DEEP, 0.10, False),
    "tiktok": Platform("TikTok", "tiktok.com", tiktok_icon,
                        TIKTOK, TIKTOK, TIKTOK_DEEP, 0.12, False),
    "youtube": Platform("YouTube", "youtube.com", youtube_icon,
                         YOUTUBE, YOUTUBE_SOFT, YOUTUBE_DEEP, 0.35, True),
}
