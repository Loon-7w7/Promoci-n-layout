# Generador de overlay Twitch / Kick

Interfaz web para generar el overlay vertical (1080×1920) en **WebM con canal alfa**,
con la animación de entrada. Cambias el nombre, activas o desactivas cada plataforma
y descargas el archivo listo para Filmora.

## Qué necesitas

- Python 3.10 o superior
- **ffmpeg** en el PATH (`ffmpeg -version` tiene que responder)
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: descárgalo de ffmpeg.org y agrégalo al PATH
- En Linux, cairosvg necesita las librerías de Cairo:
  `sudo apt install libcairo2 libpango-1.0-0 libpangocairo-1.0-0`

## Instalación

```bash
cd overlay-app
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

```bash
uvicorn app:app --port 8000
```

Abre <http://127.0.0.1:8000>.

La vista previa se actualiza sola mientras escribes (muestra el fotograma final).
El botón genera el video completo con la entrada animada; tarda entre 10 y 60 segundos
según los núcleos que tenga tu máquina, porque renderiza 180 fotogramas.

Si quieres exponerlo en tu red local: `uvicorn app:app --host 0.0.0.0 --port 8000`.

## Desde la terminal, sin interfaz

```bash
python overlay.py --twitch Loon_VT --kick LoonVT
python overlay.py --twitch Harukii_VT --kick Harukii_VT --position baja --duration 8
python overlay.py --kick solo_kick -o mi-overlay.webm
```

Al menos uno de `--twitch` o `--kick` es obligatorio.

## Cómo funciona

1. `overlay.py` arma un SVG por fotograma. La posición, la opacidad y el barrido de
   entrada se calculan en función del tiempo con una curva `easeOutCubic`.
2. `fontTools` convierte cada letra de Poppins en un `<path>`, así que el resultado no
   depende de que la fuente esté instalada. De paso mide el ancho real del nombre para
   ajustar el cuerpo de letra y que nunca se desborde de la barra.
3. `cairosvg` rasteriza los fotogramas a PNG con transparencia, en paralelo.
4. `ffmpeg` los junta en WebM con `libvpx-vp9` y `yuva420p`, que es lo que conserva el alfa.

Para comprobar que un archivo salió bien:

```bash
ffprobe -v error -show_streams overlay-loon_vt.webm | grep alpha_mode   # alpha_mode=1
```

## Qué puedes tocar

En `overlay.py`, arriba del todo:

- `POSITIONS`: las tres alturas de la barra en píxeles.
- `MAXW`: ancho máximo de la barra. Está en 822 para no chocar con la columna de
  botones de TikTok y Reels.
- `VIOLET`, `GREEN`, `INK`: la paleta.
- `NAME_MAX_2` y `NAME_MAX_1`: cuerpo de letra máximo con dos plataformas o con una.
- En `frame_svg`, los tramos `_seg(t, inicio, fin)` controlan el tiempo de cada
  elemento de la entrada.

## Fuentes

Poppins está incluida en `fonts/` bajo licencia SIL Open Font License 1.1.
Puedes cambiarla por cualquier otro `.ttf`: reemplaza los archivos y ajusta el
diccionario `FONTS`.
