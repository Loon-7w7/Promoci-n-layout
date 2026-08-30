"""
Generador del overlay vertical para Twitch / Kick.

Pipeline: SVG por fotograma -> PNG con alfa (cairosvg) -> WebM VP9 con alfa (ffmpeg).
La tipografia Poppins se convierte a trazos, asi que el resultado no depende
de que la fuente este instalada en el sistema.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field, asdict

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

BASE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE, "fonts")
FONTS = {
    "bold": os.path.join(FONT_DIR, "Poppins-Bold.ttf"),
    "medium": os.path.join(FONT_DIR, "Poppins-Medium.ttf"),
    "light": os.path.join(FONT_DIR, "Poppins-Light.ttf"),
}

# ---------------------------------------------------------------- lienzo
W, H = 1080, 1920
BX = 48                 # margen izquierdo de la barra
BH, BR = 170, 30        # alto y radio de la barra
MAXW = 822              # ancho maximo (deja libre la columna de botones)
PAD = 40                # margen interno
ICON = 68               # lado del icono
GAPIT = 16              # separacion icono -> texto
CGAP = 40               # separacion entre las dos plataformas
NAME_MAX_2 = 46         # cuerpo del nombre con dos plataformas
NAME_MAX_1 = 54         # cuerpo del nombre con una sola
NAME_MIN = 26

POSITIONS = {"alta": 620, "media": 1230, "baja": 1500}

VIOLET = "#7C3AED"
VIOLET_DEEP = "#5B21B6"
GREEN = "#53FC18"
INK = "#07070A"

_cache: dict[str, tuple] = {}


# ---------------------------------------------------------------- tipografia
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


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


# ---------------------------------------------------------------- config
@dataclass
class Config:
    twitch: str | None = None
    kick: str | None = None
    label: str = "sígueme en vivo"
    position: str = "media"
    duration: float = 6.0
    fps: int = 30

    def clean(self) -> "Config":
        tw = (self.twitch or "").strip() or None
        kk = (self.kick or "").strip() or None
        if not tw and not kk:
            raise ValueError("Hace falta al menos un nombre: Twitch, Kick o los dos.")
        pos = self.position if self.position in POSITIONS else "media"
        dur = min(30.0, max(2.0, float(self.duration)))
        fps = 60 if int(self.fps) >= 60 else 30
        return Config(tw, kk, (self.label or "").strip(), pos, dur, fps)

    def slug(self) -> str:
        base = self.twitch or self.kick or "overlay"
        return re.sub(r"[^a-zA-Z0-9._-]+", "-", base).strip("-.").lower() or "overlay"


# ---------------------------------------------------------------- geometria
def layout(cfg: Config) -> dict:
    by = POSITIONS[cfg.position]
    both = bool(cfg.twitch and cfg.kick)

    if both:
        bw = MAXW
        avail = (bw - 2 * PAD - CGAP - 2 * (ICON + GAPIT)) / 2
        widest = max(measure(cfg.twitch, "bold", NAME_MAX_2, 0.5),
                     measure(cfg.kick, "bold", NAME_MAX_2, 0.5))
        size = NAME_MAX_2 if widest <= avail else max(NAME_MIN, NAME_MAX_2 * avail / widest)
        x1 = BX + PAD
        x2 = BX + PAD + (ICON + GAPIT) + avail + CGAP
        mid = (x1 + ICON + GAPIT + avail + x2) / 2
        seam = (mid + 30, mid - 30)
    else:
        name = cfg.twitch or cfg.kick
        size = NAME_MAX_1
        tw = max(measure(name, "bold", size, 0.5), measure("twitch.tv", "medium", 22, 2))
        bw = 2 * PAD + ICON + GAPIT + tw
        if bw > MAXW:
            size = max(NAME_MIN, size * (MAXW - 2 * PAD - ICON - GAPIT) / tw)
            tw = measure(name, "bold", size, 0.5)
            bw = min(MAXW, 2 * PAD + ICON + GAPIT + tw)
        bw = max(420, bw)
        x1 = BX + PAD
        x2 = x1
        seam = None

    return {
        "by": by, "bw": bw, "size": size, "seam": seam, "both": both,
        "x1": x1, "x2": x2,
        "icon_y": by + (BH - ICON) / 2,
        "url_y": by + 70,
        "name_y": by + 118,
    }


# ---------------------------------------------------------------- iconos
def twitch_icon(x: float, y: float) -> str:
    s = ICON / 100.0 * 0.64
    return (f'<g transform="translate({x},{y})">'
            f'<rect width="{ICON}" height="{ICON}" rx="19" fill="#FFFFFF"/>'
            f'<g transform="translate({ICON*0.18:.1f},{ICON*0.18:.1f}) scale({s:.4f})">'
            f'<rect x="12" y="14" width="76" height="52" rx="10" fill="{VIOLET_DEEP}"/>'
            f'<polygon points="32,66 32,89 55,66" fill="{VIOLET_DEEP}"/>'
            f'<rect x="40" y="28" width="9" height="25" rx="4.5" fill="#FFFFFF"/>'
            f'<rect x="57" y="28" width="9" height="25" rx="4.5" fill="#FFFFFF"/>'
            f'</g></g>')


def kick_icon(x: float, y: float) -> str:
    s = ICON / 100.0 * 0.64
    return (f'<g transform="translate({x},{y})">'
            f'<rect width="{ICON}" height="{ICON}" rx="19" fill="{GREEN}"/>'
            f'<g transform="translate({ICON*0.18:.1f},{ICON*0.18:.1f}) scale({s:.4f})">'
            f'<rect x="23" y="18" width="18" height="64" fill="{INK}"/>'
            f'<rect x="41" y="36" width="18" height="28" fill="{INK}"/>'
            f'<rect x="59" y="18" width="18" height="18" fill="{INK}"/>'
            f'<rect x="59" y="64" width="18" height="18" fill="{INK}"/>'
            f'</g></g>')


# ---------------------------------------------------------------- animacion
def _ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _seg(t: float, a: float, b: float) -> float:
    return _ease_out((t - a) / (b - a)) if b > a else 1.0


def frame_svg(t: float, cfg: Config) -> str:
    L = layout(cfg)
    by, bw, size = L["by"], L["bw"], L["size"]
    both, seam = L["both"], L["seam"]

    band_p = _seg(t, 0.00, 0.60)
    tw_p = _seg(t, 0.35, 0.75)
    kk_p = _seg(t, 0.50 if both else 0.35, 0.90 if both else 0.75)
    lb_p = _seg(t, 0.70, 1.10)

    wipe_w = bw * band_p
    band_dx = -26 * (1 - band_p)
    tw_dy = 20 * (1 - tw_p)
    kk_dy = 20 * (1 - kk_p)
    lb_dx = -24 * (1 - lb_p)

    band = f'<rect x="{BX}" y="{by}" width="{bw:.1f}" height="{BH}" rx="{BR}"/>'
    if seam:
        st, sb = seam
        left = f'<polygon points="{BX},{by} {st:.1f},{by} {sb:.1f},{by+BH} {BX},{by+BH}"/>'
        right = f'<polygon points="{st:.1f},{by} {BX+bw:.1f},{by} {BX+bw:.1f},{by+BH} {sb:.1f},{by+BH}"/>'
    else:
        left = right = band

    if both:
        edge = (f'<stop offset="0%" stop-color="#A78BFA"/><stop offset="48%" stop-color="{VIOLET}"/>'
                f'<stop offset="52%" stop-color="{GREEN}"/><stop offset="100%" stop-color="#2FA80A"/>')
    elif cfg.twitch:
        edge = f'<stop offset="0%" stop-color="#A78BFA"/><stop offset="100%" stop-color="{VIOLET}"/>'
    else:
        edge = f'<stop offset="0%" stop-color="{GREEN}"/><stop offset="100%" stop-color="#2FA80A"/>'

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
         f'''<defs>
  <clipPath id="band">{band}</clipPath>
  <clipPath id="bandL">{left}</clipPath>
  <clipPath id="bandR">{right}</clipPath>
  <clipPath id="wipe"><rect x="{BX-30}" y="{by-60}" width="{wipe_w+30:.2f}" height="{BH+120}"/></clipPath>
  <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">{edge}</linearGradient>
  <filter id="lift" x="-40%" y="-40%" width="180%" height="180%" color-interpolation-filters="sRGB">
    <feDropShadow dx="0" dy="6" stdDeviation="10" flood-color="#000000" flood-opacity="0.55"/>
  </filter>
  <filter id="liftText" x="-40%" y="-40%" width="180%" height="180%" color-interpolation-filters="sRGB">
    <feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="#000000" flood-opacity="0.75"/>
  </filter>
</defs>''']

    # etiqueta superior
    if cfg.label and lb_p > 0:
        s.append(f'<g opacity="{lb_p:.3f}" transform="translate({lb_dx:.2f},0)" filter="url(#liftText)">')
        s.append(f'<circle cx="{BX+18}" cy="{by-52}" r="9" fill="{GREEN if cfg.kick else "#A78BFA"}"/>')
        s.append('<g fill="#FFFFFF" opacity="0.95">'
                 + text_path(cfg.label, "light", 36, BX + 44, by - 40, 2) + '</g>')
        s.append('</g>')

    if band_p <= 0:
        s.append('</svg>')
        return "\n".join(s)

    s.append(f'<g clip-path="url(#wipe)" transform="translate({band_dx:.2f},0)">')
    s.append(f'<g filter="url(#lift)"><g opacity="0.62" fill="#000000">{band}</g></g>')
    if cfg.twitch:
        s.append(f'<g clip-path="url(#band)"><g clip-path="url(#bandL)">'
                 f'<rect x="{BX}" y="{by}" width="{bw:.1f}" height="{BH}" fill="{VIOLET}" opacity="0.40"/></g></g>')
    if cfg.kick:
        s.append(f'<g clip-path="url(#band)"><g clip-path="url(#bandR)">'
                 f'<rect x="{BX}" y="{by}" width="{bw:.1f}" height="{BH}" fill="{GREEN}" opacity="0.10"/></g></g>')
    if seam:
        st, sb = seam
        s.append(f'<g clip-path="url(#band)"><line x1="{st:.1f}" y1="{by}" x2="{sb:.1f}" y2="{by+BH}" '
                 f'stroke="{GREEN}" stroke-width="3" opacity="0.9"/></g>')
    s.append(f'<rect x="{BX}" y="{by}" width="{bw:.1f}" height="{BH}" rx="{BR}" fill="none" '
             f'stroke="url(#edge)" stroke-width="3" opacity="0.9"/>')

    if cfg.twitch and tw_p > 0:
        s.append(f'<g opacity="{tw_p:.3f}" transform="translate(0,{tw_dy:.2f})">')
        s.append(twitch_icon(L["x1"], L["icon_y"]))
        tx = L["x1"] + ICON + GAPIT
        s.append('<g fill="#FFFFFF" opacity="0.62">'
                 + text_path("twitch.tv", "medium", 22, tx, L["url_y"], 2) + '</g>')
        s.append('<g fill="#FFFFFF">'
                 + text_path(cfg.twitch, "bold", size, tx, L["name_y"], 0.5) + '</g>')
        s.append('</g>')

    if cfg.kick and kk_p > 0:
        s.append(f'<g opacity="{kk_p:.3f}" transform="translate(0,{kk_dy:.2f})">')
        s.append(kick_icon(L["x2"], L["icon_y"]))
        tx = L["x2"] + ICON + GAPIT
        s.append(f'<g fill="{GREEN}" opacity="0.7">'
                 + text_path("kick.com", "medium", 22, tx, L["url_y"], 2) + '</g>')
        s.append(f'<g fill="{GREEN}">'
                 + text_path(cfg.kick, "bold", size, tx, L["name_y"], 0.5) + '</g>')
        s.append('</g>')

    s.append('</g></svg>')
    return "\n".join(s)



# ---------------------------------------------------------------- rasterizado
# Se usa resvg si esta disponible (rueda de pip, sin dependencias externas)
# y cairosvg como alternativa. En Windows cairosvg necesita las DLL de Cairo,
# asi que resvg es la opcion recomendada ahi.
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


# ---------------------------------------------------------------- render
def _worker(job):
    i, t, cfg_dict, outdir = job
    cfg = Config(**cfg_dict)
    rasterize(frame_svg(t, cfg), os.path.join(outdir, f"f{i:05d}.png"))
    return i


def ffmpeg_ok() -> bool:
    return shutil.which("ffmpeg") is not None


def render_webm(cfg: Config, out_path: str, workers: int | None = None) -> str:
    if not ffmpeg_ok():
        raise RuntimeError("No encuentro ffmpeg en el PATH. Instalalo y vuelve a intentar.")
    raster_engine()  # falla temprano y con un mensaje claro si no hay rasterizador
    cfg = cfg.clean()
    n = int(round(cfg.duration * cfg.fps))
    tmp = tempfile.mkdtemp(prefix="overlay_")
    try:
        jobs = [(i, i / cfg.fps, asdict(cfg), tmp) for i in range(n)]
        with ProcessPoolExecutor(max_workers=workers or max(1, (os.cpu_count() or 2))) as ex:
            list(ex.map(_worker, jobs, chunksize=4))
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-framerate", str(cfg.fps), "-i", os.path.join(tmp, "f%05d.png"),
             "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
             "-b:v", "0", "-crf", "26", "-auto-alt-ref", "0", "-row-mt", "1",
             out_path],
            check=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out_path


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Genera el overlay WebM con alfa.")
    p.add_argument("--twitch")
    p.add_argument("--kick")
    p.add_argument("--label", default="sígueme en vivo")
    p.add_argument("--position", default="media", choices=list(POSITIONS))
    p.add_argument("--duration", type=float, default=6.0)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("-o", "--out")
    a = p.parse_args()
    c = Config(a.twitch, a.kick, a.label, a.position, a.duration, a.fps).clean()
    out = a.out or f"overlay-{c.slug()}.webm"
    print("Renderizando...", out)
    render_webm(c, out)
    print("Listo:", out)
