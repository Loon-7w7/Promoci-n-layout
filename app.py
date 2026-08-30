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
from overlay import Config, POSITIONS

BASE = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="Overlay Twitch/Kick")
app.mount("/fonts", StaticFiles(directory=os.path.join(BASE, "fonts")), name="fonts")


class RenderIn(BaseModel):
    twitch: str | None = None
    kick: str | None = None
    label: str = "sígueme en vivo"
    position: str = "media"
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
    label: str = Query("sígueme en vivo"),
    position: str = Query("media"),
):
    """Fotograma final del overlay, para la vista previa del navegador."""
    try:
        cfg = Config(twitch, kick, label, position).clean()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    svg = overlay.frame_svg(99.0, cfg)
    return Response(svg, media_type="image/svg+xml",
                    headers={"Cache-Control": "no-store"})


@app.post("/render")
def render(body: RenderIn):
    """Renderiza el WebM con canal alfa y lo devuelve como descarga."""
    if not overlay.ffmpeg_ok():
        raise HTTPException(status_code=500,
                            detail="No encuentro ffmpeg en el PATH del servidor.")
    try:
        cfg = Config(body.twitch, body.kick, body.label,
                     body.position, body.duration, body.fps).clean()
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
    return {"ok": True, "ffmpeg": overlay.ffmpeg_ok(), "posiciones": list(POSITIONS)}
