"""Reparte los fotogramas entre procesos y llama a ffmpeg. Ver CLAUDE.md #4.6 y #7.

Los parametros de ffmpeg no son negociables si se quiere conservar el alfa:
-c:v libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0.

ffmpeg se busca primero en el PATH del sistema (Docker, desarrollo local) y,
si no aparece, se cae al binario portatil de imageio-ffmpeg (Vercel y
cualquier entorno sin ffmpeg instalado). El resultado se memoriza igual que
raster_engine() en raster.py.
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


_FFMPEG = None


def _ffmpeg_path() -> str | None:
    global _FFMPEG
    if _FFMPEG:
        return _FFMPEG
    path = shutil.which("ffmpeg")
    if path:
        _FFMPEG = path
        return _FFMPEG
    try:
        import imageio_ffmpeg
        _FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
        return _FFMPEG
    except Exception:
        return None


def ffmpeg_ok() -> bool:
    return _ffmpeg_path() is not None


def render_webm(cfg: Config, out_path: str, workers: int | None = None) -> str:
    ffmpeg = _ffmpeg_path()
    if not ffmpeg:
        raise RuntimeError(
            "No encuentro ffmpeg. Instalalo y agregalo al PATH, o instala "
            "imageio-ffmpeg (pip install imageio-ffmpeg)."
        )
    raster_engine()  # falla temprano y con un mensaje claro si no hay rasterizador
    cfg = cfg.clean()
    n = int(round(cfg.duration * cfg.fps))
    tmp = tempfile.mkdtemp(prefix="overlay_")
    try:
        jobs = [(i, i / cfg.fps, asdict(cfg), tmp) for i in range(n)]
        with ProcessPoolExecutor(max_workers=workers or max(1, (os.cpu_count() or 2))) as ex:
            list(ex.map(_worker, jobs, chunksize=4))
        subprocess.run(
            [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
             "-framerate", str(cfg.fps), "-i", os.path.join(tmp, "f%05d.png"),
             "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
             "-b:v", "0", "-crf", "26", "-auto-alt-ref", "0", "-row-mt", "1",
             out_path],
            check=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out_path
