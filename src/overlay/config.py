"""Config y su unico validador. Ver CLAUDE.md #4.2."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .constants import POSITIONS, ALIGNMENTS, ANIMATIONS, PLATFORM_ORDER


@dataclass
class Config:
    twitch: str | None = None
    kick: str | None = None
    tiktok: str | None = None
    youtube: str | None = None
    label: str = "sígueme en vivo"
    position: str = "media"
    align: str = "centro"
    animation: str = "barrido"
    duration: float = 6.0
    fps: int = 30

    def clean(self) -> "Config":
        names = {p: (getattr(self, p) or "").strip() or None for p in PLATFORM_ORDER}
        active = [p for p in PLATFORM_ORDER if names[p]]
        if not active:
            raise ValueError("Hace falta al menos una plataforma: Twitch, Kick, TikTok o YouTube.")
        if len(active) > 2:
            raise ValueError("Como maximo dos plataformas a la vez.")
        return Config(
            names["twitch"], names["kick"], names["tiktok"], names["youtube"],
            (self.label or "").strip(),
            self.position if self.position in POSITIONS else "media",
            self.align if self.align in ALIGNMENTS else "centro",
            self.animation if self.animation in ANIMATIONS else "barrido",
            min(30.0, max(2.0, float(self.duration))),
            60 if int(self.fps) >= 60 else 30,
        )

    def active(self) -> list[tuple[str, str]]:
        """[(id_plataforma, nombre), ...] en el orden de PLATFORM_ORDER. 1 o 2 items."""
        return [(p, getattr(self, p)) for p in PLATFORM_ORDER if getattr(self, p)]

    def slug(self) -> str:
        active = self.active()
        base = active[0][1] if active else "overlay"
        return re.sub(r"[^a-zA-Z0-9._-]+", "-", base).strip("-.").lower() or "overlay"
