"""
Generador del overlay vertical para Twitch, Kick, TikTok y YouTube.

Pipeline: SVG por fotograma -> PNG con alfa -> WebM VP9 con alfa (ffmpeg).
La tipografia Poppins se convierte a trazos, asi que el resultado no depende
de que la fuente este instalada en el sistema.

Para la vista previa del navegador el mismo SVG se emite con animaciones SMIL,
muestreadas de las mismas funciones que usa el video. Una sola fuente de verdad.

Se puede elegir como maximo dos plataformas a la vez (Config.clean() lo valida,
Config.active() devuelve cuales). El motor esta dividido por responsabilidad
(ver CLAUDE.md #4): constants, typography, config, layout, icons, platforms,
animation, svg, raster y render. Este archivo solo reexporta la API publica.
"""

from __future__ import annotations

from .config import Config
from .constants import (
    W, H, POSITIONS, ALIGNMENTS, ANIMATIONS, PLATFORM_ORDER,
    VIOLET, VIOLET_DEEP, GREEN, INK, INTRO,
)
from .layout import layout
from .raster import raster_engine, rasterize
from .render import ffmpeg_ok, render_webm
from .svg import frame_svg

__all__ = [
    "Config", "layout", "frame_svg", "raster_engine", "rasterize",
    "ffmpeg_ok", "render_webm",
    "W", "H", "POSITIONS", "ALIGNMENTS", "ANIMATIONS", "PLATFORM_ORDER",
    "VIOLET", "VIOLET_DEEP", "GREEN", "INK", "INTRO",
]
