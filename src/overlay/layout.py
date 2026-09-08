"""layout(cfg): toda la geometria resuelta en un solo lugar. Ver CLAUDE.md #4.3.

Ninguna otra funcion del paquete calcula posiciones. El orden de las cuentas
importa: el ancho se decide antes que la posicion horizontal, y esta antes
que la costura, porque cada paso depende del anterior.
"""

from __future__ import annotations

from .config import Config
from .constants import W, MARGIN, BH, MAXW, PAD, ICON, GAPIT, CGAP, NAME_MAX_2, NAME_MAX_1, NAME_MIN, POSITIONS
from .platforms import PLATFORMS
from .typography import measure


def layout(cfg: Config) -> dict:
    by = POSITIONS[cfg.position]
    active = cfg.active()
    both = len(active) == 2

    if both:
        bw = MAXW
        avail = (bw - 2 * PAD - CGAP - 2 * (ICON + GAPIT)) / 2
        widest = max(measure(name, "bold", NAME_MAX_2, 0.5) for _, name in active)
        size = NAME_MAX_2 if widest <= avail else max(NAME_MIN, NAME_MAX_2 * avail / widest)
    else:
        pid, name = active[0]
        size = NAME_MAX_1
        tw = max(measure(name, "bold", size, 0.5), measure(PLATFORMS[pid].url, "medium", 22, 2))
        bw = MAXW
        avail = bw - 2 * PAD - ICON - GAPIT
        if tw > avail:
            size = max(NAME_MIN, size * avail / tw)
            tw = measure(name, "bold", size, 0.5)
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
        block_w = ICON + GAPIT + tw
        x1 = x2 = bx + (bw - block_w) / 2
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
