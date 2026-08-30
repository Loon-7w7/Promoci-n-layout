# Contexto del proyecto

Notas para retomar el trabajo sin tener que reconstruir las decisiones desde cero.

## Qué es

Un generador de overlays de "sígueme en Twitch y Kick" para videos verticales.
La salida es un WebM 1080×1920 con canal alfa y una animación de entrada, pensado
para arrastrarlo a una pista superior en Filmora 15.

Nació como un SVG estático hecho a mano y terminó siendo una app web con FastAPI.

## Decisiones tomadas

**El overlay no cubre la pantalla.** Es una barra sobre fondo transparente, con el
fondo negro al 62 % para que se siga viendo el video de atrás. Sombra bajo la barra
y bajo el texto para que aguante tanto escenas oscuras como claras.

**Zona segura.** `MAXW = 822` y el margen izquierdo de 48 px dejan libre la columna
de botones de TikTok y Reels. La posición "media" (`y = 1230`) deja libre el tercio
inferior para los subtítulos de la plataforma.

**La costura diagonal es la firma visual.** Separa el lado morado de Twitch del lado
oscuro de Kick. Cuando solo hay una plataforma activa, la costura desaparece y la
barra se encoge para ajustarse al contenido.

**Tipografía convertida a trazos.** `fontTools` saca los contornos de Poppins y los
mete como `<path>` en el SVG. Así el render no depende de fuentes instaladas, y de
paso se puede medir el ancho real del nombre para ajustar el cuerpo de letra y que
nunca desborde la barra.

## Cómo está armado

```
app.py       FastAPI: /, /preview.svg, /render, /health
overlay.py   el motor completo, también usable por CLI
static/      una sola página, sin framework ni build
fonts/       Poppins Bold, Medium y Light (OFL 1.1)
```

Pipeline: `frame_svg(t, cfg)` arma el SVG de cada fotograma → `rasterize()` lo pasa a
PNG con alfa → `ffmpeg` los junta en WebM VP9 `yuva420p`.

La vista previa del navegador no renderiza video: pide el SVG del último fotograma a
`/preview.svg`, por eso es instantánea.

## Cosas que ya costaron trabajo, no repetirlas

- **cairosvg no funciona en Windows** sin las DLL de Cairo. Por eso el rasterizador
  principal es `resvg-py`, que viene como rueda de pip sin dependencias externas.
  `raster_engine()` detecta cuál hay disponible.
- **Los filtros necesitan `color-interpolation-filters="sRGB"`.** resvg sigue el
  estándar y sin eso las sombras salen apagadas. cairosvg lo ignoraba, así que el
  problema solo aparece al cambiar de motor.
- **Para verificar que el alfa sobrevivió:**
  `ffprobe -v error -show_streams salida.webm | grep alpha_mode` debe dar `alpha_mode=1`.
  Ojo: `ffprobe` reporta `pix_fmt=yuv420p` aunque el alfa esté ahí, porque VP9 lo
  guarda en una pista aparte. No es señal de error.
- **Para decodificar un WebM con alfa hay que forzar el decodificador:**
  `ffmpeg -vcodec libvpx-vp9 -i entrada.webm ...`. El decodificador nativo ignora el alfa.
- **ProRes 4444 también sirve** y Filmora lo lee, pero pesa 200 veces más (31 MB
  contra 132 KB para 6 segundos). Solo vale la pena como respaldo.
- Los fotogramas se generan con `ProcessPoolExecutor`. Son 180 para 6 segundos, así
  que el tiempo depende de los núcleos disponibles.

## Entorno

Windows con PowerShell. El activador del entorno virtual es
`.\.venv\Scripts\Activate.ps1`, no `source`.

## Ideas pendientes

- Empaquetarlo en Docker.
- Selector de colores para reutilizarlo con otras paletas.
- Variante para cuando el nombre es idéntico en las dos plataformas: mostrarlo una
  sola vez, grande, cortado por la diagonal, con los dos iconos juntos al lado. Se
  vería más limpio y con letra mucho más grande que repitiendo el mismo texto.
- Versión apaisada 1600×900 para pantalla de "ya vuelvo" (existe como SVG suelto,
  no está integrada en la app).
