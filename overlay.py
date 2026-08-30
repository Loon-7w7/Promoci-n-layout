"""
Generador del overlay vertical para Twitch / Kick.

Pipeline: SVG por fotograma -> PNG con alfa -> WebM VP9 con alfa (ffmpeg).
La tipografia Poppins se convierte a trazos, asi que el resultado no depende
de que la fuente este instalada en el sistema.

Para la vista previa del navegador el mismo SVG se emite con animaciones SMIL,
muestreadas de las mismas funciones que usa el video. Una sola fuente de verdad.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, asdict

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
MARGIN = 48             # margen lateral minimo
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
ALIGNMENTS = ("izquierda", "centro", "derecha")

# nombre interno -> etiqueta para la interfaz
ANIMATIONS = {
    "barrido": "Barrido lateral",
    "deslizar": "Sube desde abajo",
    "rebote": "Sube con rebote",
    "escala": "Crece desde el centro",
    "cortina": "Se abre como cortina",
    "desvanecer": "Aparece suave",
}
INTRO = 1.15            # cuanto dura la entrada, en segundos

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


# ---------------------------------------------------------------- config
@dataclass
class Config:
    twitch: str | None = None
    kick: str | None = None
    label: str = "sígueme en vivo"
    position: str = "media"
    align: str = "centro"
    animation: str = "barrido"
    duration: float = 6.0
    fps: int = 30

    def clean(self) -> "Config":
        tw = (self.twitch or "").strip() or None
        kk = (self.kick or "").strip() or None
        if not tw and not kk:
            raise ValueError("Hace falta al menos un nombre: Twitch, Kick o los dos.")
        return Config(
            tw, kk, (self.label or "").strip(),
            self.position if self.position in POSITIONS else "media",
            self.align if self.align in ALIGNMENTS else "centro",
            self.animation if self.animation in ANIMATIONS else "barrido",
            min(30.0, max(2.0, float(self.duration))),
            60 if int(self.fps) >= 60 else 30,
        )

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
    else:
        name = cfg.twitch or cfg.kick
        size = NAME_MAX_1
        tw = max(measure(name, "bold", size, 0.5), measure("twitch.tv", "medium", 22, 2))
        bw = 2 * PAD + ICON + GAPIT + tw
        if bw > MAXW:
            size = max(NAME_MIN, size * (MAXW - 2 * PAD - ICON - GAPIT) / tw)
            tw = measure(name, "bold", size, 0.5)
            bw = 2 * PAD + ICON + GAPIT + tw
        bw = min(MAXW, max(420, bw))
        avail = None

    if cfg.align == "centro":
        bx = (W - bw) / 2
    elif cfg.align == "derecha":
        bx = W - MARGIN - bw
    else:
        bx = MARGIN

    if both:
        x1 = bx + PAD
        x2 = bx + PAD + (ICON + GAPIT) + avail + CGAP
        mid = (x1 + ICON + GAPIT + avail + x2) / 2
        seam = (mid + 30, mid - 30)
    else:
        x1 = x2 = bx + PAD
        seam = None

    # la etiqueta de arriba sigue la alineacion de la barra
    lab_w = 18 + 26 + (measure(cfg.label, "light", 36, 2) if cfg.label else 0)
    if cfg.align == "centro":
        lab_x = bx + (bw - lab_w) / 2
    elif cfg.align == "derecha":
        lab_x = bx + bw - lab_w
    else:
        lab_x = bx + 18

    return {
        "by": by, "bx": bx, "bw": bw, "size": size, "seam": seam, "both": both,
        "x1": x1, "x2": x2, "lab_x": lab_x,
        "cx": bx + bw / 2, "cy": by + BH / 2,
        "icon_y": by + (BH - ICON) / 2,
        "url_y": by + 70,
        "name_y": by + 118,
    }


# ---------------------------------------------------------------- iconos
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


# ---------------------------------------------------------------- animacion
def _ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _ease_back(t: float) -> float:
    """Se pasa un poco del destino y regresa."""
    t = max(0.0, min(1.0, t))
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def _seg(t: float, a: float, b: float, ease=_ease_out) -> float:
    return ease((t - a) / (b - a)) if b > a else 1.0


def anim_state(t: float, cfg: Config, L: dict) -> dict:
    """Estado de la animacion en el segundo t. Unica fuente de verdad."""
    kind = cfg.animation
    solo = not L["both"]

    # los bloques de cada plataforma siempre entran escalonados
    tw_p = _seg(t, 0.35, 0.75)
    kk_p = _seg(t, 0.35 if solo else 0.50, 0.75 if solo else 0.90)
    lb_p = _seg(t, 0.70, 1.10)

    st = {
        "wipe": L["bw"] * 1.2, "tx": 0.0, "ty": 0.0,
        "sx": 1.0, "sy": 1.0, "op": 1.0,
        "tw_dy": 20 * (1 - tw_p), "tw_op": tw_p,
        "kk_dy": 20 * (1 - kk_p), "kk_op": kk_p,
        "lb_dx": 0.0, "lb_dy": 0.0, "lb_op": lb_p,
    }

    if kind == "barrido":
        p = _seg(t, 0.0, 0.60)
        st["wipe"] = L["bw"] * p
        st["tx"] = -26 * (1 - p)
        st["lb_dx"] = -24 * (1 - lb_p)

    elif kind == "deslizar":
        p = _seg(t, 0.0, 0.65)
        st["ty"] = 110 * (1 - p)
        st["op"] = min(1.0, p * 1.6)
        st["lb_dy"] = 40 * (1 - lb_p)

    elif kind == "rebote":
        p = _seg(t, 0.0, 0.85, _ease_back)
        st["ty"] = 130 * (1 - p)
        st["op"] = min(1.0, _seg(t, 0.0, 0.25))
        st["lb_dy"] = 50 * (1 - _seg(t, 0.70, 1.15, _ease_back))

    elif kind == "escala":
        p = _seg(t, 0.0, 0.60)
        st["sx"] = st["sy"] = 0.82 + 0.18 * p
        st["op"] = min(1.0, p * 1.7)

    elif kind == "cortina":
        p = _seg(t, 0.0, 0.55)
        st["sx"] = max(0.001, p)
        st["op"] = 1.0 if p > 0.02 else 0.0

    elif kind == "desvanecer":
        st["op"] = _seg(t, 0.0, 0.70)

    return st


# ---------------------------------------------------------------- SVG
def _smil(attr: str, values: list[str], cycle: float, kind: str | None = None) -> str:
    """Convierte una lista de muestras en una animacion SMIL para la vista previa."""
    n = len(values)
    keys = ";".join(f"{(i/(n-1))*(INTRO/cycle):.4f}" for i in range(n)) + ";1"
    vals = ";".join(values) + ";" + values[-1]
    tag = "animateTransform" if kind else "animate"
    extra = f' type="{kind}"' if kind else ""
    return (f'<{tag} attributeName="{attr}"{extra} values="{vals}" keyTimes="{keys}" '
            f'dur="{cycle}s" repeatCount="indefinite" calcMode="linear" fill="freeze"/>')


def frame_svg(t: float, cfg: Config, cycle: float | None = None) -> str:
    """
    Fotograma en el segundo t.
    Si se pasa `cycle`, el SVG sale con animaciones SMIL en bucle (vista previa).
    """
    L = layout(cfg)
    bx, by, bw, size = L["bx"], L["by"], L["bw"], L["size"]
    seam = L["seam"]
    st = anim_state(t if cycle is None else 99.0, cfg, L)

    samples = []
    if cycle:
        n = 26
        samples = [anim_state(i / (n - 1) * INTRO, cfg, L) for i in range(n)]

    def anim(attr, key, fmt="{:.3f}", kind=None):
        if not cycle:
            return ""
        vals = [fmt.format(s[key]) for s in samples]
        if len(set(vals)) == 1:
            return ""
        return _smil(attr, vals, cycle, kind)

    def anim_xy(kx, ky, kind="translate"):
        if not cycle:
            return ""
        vals = [f"{s[kx]:.3f} {s[ky]:.3f}" for s in samples]
        if len(set(vals)) == 1:
            return ""
        return _smil("transform", vals, cycle, kind)

    band = f'<rect x="{bx:.1f}" y="{by}" width="{bw:.1f}" height="{BH}" rx="{BR}"/>'
    if seam:
        s_t, s_b = seam
        left = f'<polygon points="{bx:.1f},{by} {s_t:.1f},{by} {s_b:.1f},{by+BH} {bx:.1f},{by+BH}"/>'
        right = f'<polygon points="{s_t:.1f},{by} {bx+bw:.1f},{by} {bx+bw:.1f},{by+BH} {s_b:.1f},{by+BH}"/>'
    else:
        left = right = band

    if L["both"]:
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
  <clipPath id="wipe"><rect x="{bx-30:.1f}" y="{by-60}" width="{st["wipe"]+30:.2f}" height="{BH+120}">{anim("width", "wipe", "{:.2f}")}</rect></clipPath>
  <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">{edge}</linearGradient>
  <filter id="lift" x="-40%" y="-40%" width="180%" height="180%" color-interpolation-filters="sRGB">
    <feDropShadow dx="0" dy="6" stdDeviation="10" flood-color="#000000" flood-opacity="0.55"/>
  </filter>
  <filter id="liftText" x="-40%" y="-40%" width="180%" height="180%" color-interpolation-filters="sRGB">
    <feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="#000000" flood-opacity="0.75"/>
  </filter>
</defs>''']

    # ---- etiqueta de arriba
    if cfg.label:
        s.append(f'<g opacity="{st["lb_op"]:.3f}">{anim("opacity", "lb_op")}')
        s.append(f'<g transform="translate({st["lb_dx"]:.2f},{st["lb_dy"]:.2f})">{anim_xy("lb_dx", "lb_dy")}')
        s.append('<g filter="url(#liftText)">')
        s.append(f'<circle cx="{L["lab_x"]+9:.1f}" cy="{by-52}" r="9" fill="{GREEN if cfg.kick else "#A78BFA"}"/>')
        s.append('<g fill="#FFFFFF" opacity="0.95">'
                 + text_path(cfg.label, "light", 36, L["lab_x"] + 44, by - 40, 2) + '</g>')
        s.append('</g></g></g>')

    # ---- barra: opacidad > traslacion > escala desde el centro > barrido
    s.append(f'<g opacity="{st["op"]:.3f}">{anim("opacity", "op")}')
    s.append(f'<g transform="translate({st["tx"]:.2f},{st["ty"]:.2f})">{anim_xy("tx", "ty")}')
    s.append(f'<g transform="translate({L["cx"]:.1f},{L["cy"]:.1f})">')
    s.append(f'<g transform="scale({st["sx"]:.4f},{st["sy"]:.4f})">{anim_xy("sx", "sy", "scale")}')
    s.append(f'<g transform="translate({-L["cx"]:.1f},{-L["cy"]:.1f})">')
    s.append('<g clip-path="url(#wipe)">')

    s.append(f'<g filter="url(#lift)"><g opacity="0.62" fill="#000000">{band}</g></g>')
    if cfg.twitch:
        s.append(f'<g clip-path="url(#band)"><g clip-path="url(#bandL)">'
                 f'<rect x="{bx:.1f}" y="{by}" width="{bw:.1f}" height="{BH}" fill="{VIOLET}" opacity="0.40"/></g></g>')
    if cfg.kick:
        s.append(f'<g clip-path="url(#band)"><g clip-path="url(#bandR)">'
                 f'<rect x="{bx:.1f}" y="{by}" width="{bw:.1f}" height="{BH}" fill="{GREEN}" opacity="0.10"/></g></g>')
    if seam:
        s_t, s_b = seam
        s.append(f'<g clip-path="url(#band)"><line x1="{s_t:.1f}" y1="{by}" x2="{s_b:.1f}" y2="{by+BH}" '
                 f'stroke="{GREEN}" stroke-width="3" opacity="0.9"/></g>')
    s.append(f'<rect x="{bx:.1f}" y="{by}" width="{bw:.1f}" height="{BH}" rx="{BR}" fill="none" '
             f'stroke="url(#edge)" stroke-width="3" opacity="0.9"/>')

    if cfg.twitch:
        s.append(f'<g opacity="{st["tw_op"]:.3f}">{anim("opacity", "tw_op")}')
        s.append(f'<g transform="translate(0,{st["tw_dy"]:.2f})">'
                 + (_smil("transform", [f'0 {x["tw_dy"]:.2f}' for x in samples], cycle, "translate") if cycle else ""))
        s.append(twitch_icon(L["x1"], L["icon_y"]))
        tx = L["x1"] + ICON + GAPIT
        s.append('<g fill="#FFFFFF" opacity="0.62">'
                 + text_path("twitch.tv", "medium", 22, tx, L["url_y"], 2) + '</g>')
        s.append('<g fill="#FFFFFF">'
                 + text_path(cfg.twitch, "bold", size, tx, L["name_y"], 0.5) + '</g>')
        s.append('</g></g>')

    if cfg.kick:
        s.append(f'<g opacity="{st["kk_op"]:.3f}">{anim("opacity", "kk_op")}')
        s.append(f'<g transform="translate(0,{st["kk_dy"]:.2f})">'
                 + (_smil("transform", [f'0 {x["kk_dy"]:.2f}' for x in samples], cycle, "translate") if cycle else ""))
        s.append(kick_icon(L["x2"], L["icon_y"]))
        tx = L["x2"] + ICON + GAPIT
        s.append(f'<g fill="{GREEN}" opacity="0.7">'
                 + text_path("kick.com", "medium", 22, tx, L["url_y"], 2) + '</g>')
        s.append(f'<g fill="{GREEN}">'
                 + text_path(cfg.kick, "bold", size, tx, L["name_y"], 0.5) + '</g>')
        s.append('</g></g>')

    s.append('</g></g></g></g></g></g></svg>')
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
    p.add_argument("--align", default="centro", choices=list(ALIGNMENTS))
    p.add_argument("--animation", default="barrido", choices=list(ANIMATIONS))
    p.add_argument("--duration", type=float, default=6.0)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("-o", "--out")
    a = p.parse_args()
    c = Config(a.twitch, a.kick, a.label, a.position, a.align,
               a.animation, a.duration, a.fps).clean()
    out = a.out or f"overlay-{c.slug()}.webm"
    print("Renderizando...", out)
    render_webm(c, out)
    print("Listo:", out)
