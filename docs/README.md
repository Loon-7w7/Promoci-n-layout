# Generador de overlay Twitch / Kick / TikTok / YouTube

Interfaz web para generar el overlay vertical (1080×1920) en **WebM con canal alfa**,
con la animación de entrada. Eliges hasta **dos** de las cuatro plataformas, escribes
el nombre de cada una y descargas el archivo listo para Filmora.

## Qué necesitas

- Python 3.10 o superior
- **ffmpeg** en el PATH (`ffmpeg -version` tiene que responder)
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: `winget install Gyan.FFmpeg` y reinicia la terminal

El rasterizado de SVG lo hace `resvg-py`, que se instala como cualquier paquete de
pip y no necesita librerías del sistema en ningún sistema operativo.

## Instalación

Todo se ejecuta desde la raíz del repo, donde está `requirements.txt`.

Linux y macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si al activar el entorno sale un error de directivas de ejecución:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Solo aplica a esa ventana de terminal.

## Uso

El servidor vive en `src/`, así que hay que pararse ahí antes de levantarlo:

```bash
cd src
uvicorn app:app --port 8000
```

Abre <http://127.0.0.1:8000>.

La vista previa se actualiza sola mientras escribes y reproduce la entrada en bucle.
El botón genera el video completo con la entrada animada; tarda entre 10 y 60 segundos
según los núcleos que tenga tu máquina, porque renderiza 180 fotogramas.

Si quieres exponerlo en tu red local: `uvicorn app:app --host 0.0.0.0 --port 8000`.

## Desde la terminal, sin interfaz

`overlay` es un paquete de Python, así que se invoca con `-m` desde `src/`:

```bash
cd src
python -m overlay --twitch Loon_VT --kick LoonVT
python -m overlay --twitch Harukii_VT --kick Harukii_VT --position baja --animation rebote
python -m overlay --kick solo_kick --align izquierda -o mi-overlay.webm
python -m overlay --tiktok loonclips --youtube LoonYT
```

`--twitch`, `--kick`, `--tiktok`, `--youtube`: **al menos uno, como máximo dos** a
la vez (con tres o más, el programa se detiene con un error).

Opciones: `--align` (izquierda, centro, derecha), `--position` (alta, media, baja),
`--animation` (barrido, deslizar, rebote, escala, cortina, desvanecer),
`--duration`, `--fps`.

## Las animaciones

| Nombre | Qué hace |
| --- | --- |
| `barrido` | La barra se revela de izquierda a derecha |
| `deslizar` | Sube desde abajo con desvanecido |
| `rebote` | Igual, pero se pasa un poco y regresa |
| `escala` | Crece desde su propio centro |
| `cortina` | Se abre a lo ancho desde el centro |
| `desvanecer` | Solo aparece, sin movimiento |

En todas, los bloques de la izquierda y la derecha entran escalonados y el texto de
arriba aparece al final.

Están definidas en `anim_state()`, dentro de `src/overlay/animation.py`. Cada una es
un puñado de líneas que devuelven desplazamiento, escala y opacidad en función del
segundo `t`. Agregar una nueva es añadir un `elif` ahí y una opción en el `<select>`
de la interfaz. La vista previa del navegador se anima sola, porque muestrea esa
misma función y la convierte en SMIL.

## Cómo funciona

1. `src/overlay/svg.py` arma un SVG por fotograma. La posición, la opacidad y el
   barrido de entrada se calculan en función del tiempo con una curva `easeOutCubic`.
2. `fontTools` convierte cada letra de Poppins en un `<path>`, así que el resultado no
   depende de que la fuente esté instalada. De paso mide el ancho real del nombre para
   ajustar el cuerpo de letra y que nunca se desborde de la barra.
3. `resvg` rasteriza los fotogramas a PNG con transparencia, en paralelo. Si no está
   instalado, usa `cairosvg` como alternativa.
4. `ffmpeg` los junta en WebM con `libvpx-vp9` y `yuva420p`, que es lo que conserva el alfa.

Para comprobar que un archivo salió bien:

```bash
ffprobe -v error -show_streams overlay-loon_vt.webm | grep alpha_mode   # alpha_mode=1
```

## Qué puedes tocar

En `src/overlay/constants.py`:

- `POSITIONS`: las tres alturas de la barra en píxeles.
- `MAXW`: ancho máximo de la barra. Está en 822 para no chocar con la columna de
  botones de TikTok y Reels (la de la app, no la red social).
- `NAME_MAX_2` y `NAME_MAX_1`: cuerpo de letra máximo con dos plataformas o con una.

En `src/overlay/platforms.py` está el color, el icono y los textos de cada red. Para
cambiarle el color de acento a una, es el único archivo que hace falta tocar.

En `src/overlay/svg.py`, dentro de `frame_svg`, los tramos `_seg(t, inicio, fin)` (en
`src/overlay/animation.py`) controlan el tiempo de cada elemento de la entrada.

## Fuentes

Poppins está incluida en `src/fonts/` bajo licencia SIL Open Font License 1.1.
Puedes cambiarla por cualquier otro `.ttf`: reemplaza los archivos y ajusta el
diccionario `FONTS` en `src/overlay/typography.py`.

## Desplegar

### Vercel

```bash
vercel        # preview
vercel --prod # producción
```

Corrélo parado en la raíz del repo, donde está `vercel.json`. No hace falta
configurar nada más: Vercel detecta `src/app.py` solo y lo instala con el
`requirements.txt` de la raíz.

Vercel no trae `ffmpeg` instalado, así que el proyecto usa `imageio-ffmpeg` (ya
en `requirements.txt`) como respaldo portátil cuando no lo encuentra en el
sistema. Si el render tarda demasiado y la función corta a los 60 segundos,
bajá `duration` o `fps` desde la interfaz, o subí `maxDuration` en
`vercel.json` (necesita plan Pro).

### Docker (Render, Railway, cualquier host de contenedores)

El `Dockerfile` instala `ffmpeg` con `apt-get` y corre `uvicorn` directo, sin
nada más que configurar.

## Si algo falla

**`no library called "cairo-2" was found`**
Es cairosvg buscando las DLL de Cairo, que en Windows no vienen con el sistema.
Instala el rasterizador que no depende de nada externo:

```powershell
pip install resvg-py
```

El código lo detecta solo y lo prefiere sobre cairosvg. Para confirmar cuál está
usando, abre <http://127.0.0.1:8000/health>: el campo `rasterizador` te lo dice.

Si prefieres quedarte con cairosvg en Windows, instala el GTK3 Runtime, que trae
las DLL que le faltan.

**`No encuentro ffmpeg en el PATH`**
Instálalo y **reinicia la terminal**, porque el PATH se lee al abrirla.
