"""Rasterizado del SVG a PNG con alfa. Ver CLAUDE.md #4.6 y #7.

Se usa resvg si esta disponible (rueda de pip, sin dependencias externas)
y cairosvg como alternativa. En Windows cairosvg necesita las DLL de Cairo,
asi que resvg es la opcion recomendada ahi.
"""

from __future__ import annotations

from .constants import W, H

_ENGINE = None


def raster_engine() -> str:
    """Devuelve 'resvg', 'cairosvg' o lanza RuntimeError si no hay ninguno."""
    global _ENGINE
    if _ENGINE:
        return _ENGINE
    try:
        import resvg_py  # noqa: F401
        _ENGINE = "resvg"
        return _ENGINE
    except Exception:
        pass
    try:
        import cairosvg  # noqa: F401
        _ENGINE = "cairosvg"
        return _ENGINE
    except Exception as e:
        raise RuntimeError(
            "No hay motor de rasterizado. Instala uno:\n"
            "  pip install resvg-py     (recomendado, funciona en Windows sin nada mas)\n"
            "  pip install cairosvg     (necesita las librerias de Cairo en el sistema)\n"
            f"Ultimo error: {e}"
        )


def rasterize(svg: str, out_png: str) -> None:
    """Convierte el SVG a PNG con transparencia."""
    if raster_engine() == "resvg":
        import resvg_py
        data = resvg_py.svg_to_bytes(svg_string=svg, width=W, height=H)
        with open(out_png, "wb") as f:
            f.write(bytes(data))
    else:
        import cairosvg
        cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=out_png,
                         output_width=W, output_height=H)
