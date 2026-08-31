"""CLI: python -m overlay --twitch ... --kick ...

Ejecutar desde src/, para que el paquete "overlay" sea importable.
"""

from __future__ import annotations

import argparse

from . import Config, POSITIONS, ALIGNMENTS, ANIMATIONS, render_webm


def main() -> None:
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


if __name__ == "__main__":
    main()
