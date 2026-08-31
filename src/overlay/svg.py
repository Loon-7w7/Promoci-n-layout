"""frame_svg(t, cfg, cycle=None): arma el SVG. Ver CLAUDE.md #4.5.

Con cycle=None devuelve el fotograma estatico del segundo t (lo usa el render
de video). Con cycle=3.4 devuelve el estado final mas animaciones SMIL,
muestreando anim_state 26 veces a lo largo de INTRO: es lo que anima la vista
previa del navegador sin renderizar un solo video.

El anidado de grupos de la barra es fragil: son seis </g> de cierre en la
ultima linea de frame_svg, y el orden opacidad > traslacion > centro > escala
> vuelta al origen > barrido es lo que hace que la barra escale desde su
propio centro. Contarlos si se agrega un grupo.
"""

from __future__ import annotations

from .animation import anim_state
from .config import Config
from .constants import W, H, BH, BR, ICON, GAPIT, VIOLET, GREEN, INTRO
from .icons import twitch_icon, kick_icon
from .layout import layout
from .typography import text_path


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
