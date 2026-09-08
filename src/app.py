"""
Servidor web del generador de overlays.

    uvicorn app:app --reload --port 8000

Luego abre http://127.0.0.1:8000
"""

from __future__ import annotations

import os
import tempfile

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

import overlay
from overlay import Config, POSITIONS, PLATFORM_ORDER

BASE = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="Overlay Twitch/Kick/TikTok/YouTube")
app.mount("/fonts", StaticFiles(directory=os.path.join(BASE, "fonts")), name="fonts")
app.mount("/svg", StaticFiles(directory=os.path.join(BASE, "svg")), name="svg")
app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")


class RenderIn(BaseModel):
    twitch: str | None = None
    kick: str | None = None
    tiktok: str | None = None
    youtube: str | None = None
    label: str = "sígueme en vivo"
    position: str = "media"
    align: str = "centro"
    animation: str = "barrido"
    duration: float = Field(6.0, ge=2, le=30)
    fps: int = 30


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(BASE, "static", "index.html"), encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/preview.svg")
def preview(
    twitch: str | None = Query(None),
    kick: str | None = Query(None),
    tiktok: str | None = Query(None),
    youtube: str | None = Query(None),
    label: str = Query("sígueme en vivo"),
    position: str = Query("media"),
    align: str = Query("centro"),
    animation: str = Query("barrido"),
    animate: int = Query(0, description="1 = la vista previa reproduce la entrada en bucle"),
):
    """Vista previa del overlay. Con animate=1 sale animada con SMIL."""
    try:
        cfg = Config(twitch, kick, tiktok, youtube, label, position, align, animation).clean()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    svg = overlay.frame_svg(99.0, cfg, cycle=3.4 if animate else None)
    return Response(svg, media_type="image/svg+xml",
                    headers={"Cache-Control": "no-store"})


@app.post("/render")
def render(body: RenderIn):
    """Renderiza el WebM con canal alfa y lo devuelve como descarga."""
    if not overlay.ffmpeg_ok():
        raise HTTPException(status_code=500,
                            detail="No encuentro ffmpeg en el PATH del servidor.")
    try:
        cfg = Config(body.twitch, body.kick, body.tiktok, body.youtube, body.label,
                     body.position, body.align, body.animation, body.duration, body.fps).clean()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    fd, path = tempfile.mkstemp(suffix=".webm")
    os.close(fd)
    try:
        overlay.render_webm(cfg, path)
    except Exception as e:
        os.unlink(path)
        raise HTTPException(status_code=500, detail=f"Fallo el render: {e}")

    name = f"overlay-{cfg.slug()}.webm"
    return FileResponse(
        path,
        media_type="video/webm",
        filename=name,
        background=BackgroundTask(lambda: os.path.exists(path) and os.unlink(path)),
    )


@app.get("/health")
def health():
    try:
        motor = overlay.raster_engine()
    except Exception as e:
        motor = f"ninguno ({e})"
    return {"ok": True, "ffmpeg": overlay.ffmpeg_ok(), "rasterizador": motor,
            "posiciones": list(POSITIONS), "alineaciones": list(overlay.ALIGNMENTS),
            "animaciones": overlay.ANIMATIONS,
            "plataformas": list(PLATFORM_ORDER), "plataformas_maximo": 2}
