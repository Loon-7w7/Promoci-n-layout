"""Config y su unico validador. Ver CLAUDE.md #4.2."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .constants import POSITIONS, ALIGNMENTS, ANIMATIONS


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
