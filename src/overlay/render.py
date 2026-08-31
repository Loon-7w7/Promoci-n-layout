"""Reparte los fotogramas entre procesos y llama a ffmpeg. Ver CLAUDE.md #4.6.

Los parametros de ffmpeg no son negociables si se quiere conservar el alfa:
-c:v libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict

from .config import Config
from .raster import rasterize, raster_engine
from .svg import frame_svg


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
