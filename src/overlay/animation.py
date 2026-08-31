"""anim_state(t, cfg, L): unica fuente de verdad de la animacion. Ver CLAUDE.md #4.4.

Funcion pura: recibe el segundo t y devuelve el estado visual completo en ese
instante. frame_svg() la muestrea tanto para el fotograma del video como para
las animaciones SMIL de la vista previa, asi que los dos no pueden
desincronizarse.

Agregar una animacion nueva: un elif kind == "..." aqui, una entrada en
ANIMATIONS (constants.py) y un <option> en el <select> de la interfaz. No hace
falta tocar el resto del paquete.
"""

from __future__ import annotations

from .config import Config


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
