# CLAUDE.md

Guía del proyecto para trabajar sobre él con un asistente en el editor.
Léela antes de tocar código: casi todo lo que parece una decisión arbitraria tiene
un motivo, y varios de esos motivos costaron trabajo descubrirlos.

---

## 1. Qué hace esto

Genera un overlay de "sígueme en [plataforma]" para video vertical, eligiendo hasta
**dos** de cuatro redes soportadas: Twitch, Kick, TikTok y YouTube.

La salida es un **WebM de 1080×1920 con canal alfa** y una animación de entrada.
Se arrastra a una pista superior en Filmora, sin chroma ni recortes: el fondo es
transparente de verdad, solo se dibuja una barra en la parte baja de la pantalla.

Hay dos formas de usarlo: una app web local (FastAPI + una página HTML) y un CLI
sobre el mismo motor.

**Restricción central:** el overlay no cubre la pantalla, convive con el video de
atrás. Todo lo demás (fondo semitransparente, sombras, zona segura, ancho máximo)
sale de ahí. Si una modificación rompe esa idea, probablemente esté mal.

---

## 2. Mapa de archivos

```
src/overlay/             Paquete del motor. Sin dependencias de FastAPI. Ejecutable como CLI.
  __init__.py              Reexporta la API publica (Config, layout, frame_svg, render_webm...).
  constants.py             Lienzo, paleta y tiempos. Los numeros magicos viven aqui, y solo aqui.
  typography.py            measure(), text_path(): la fuente convertida a trazos.
  config.py                Config y su unico validador, clean().
  layout.py                layout(cfg): toda la geometria resuelta en un solo lugar.
  icons.py                 icono de cada red: lee los SVG oficiales de src/svg/.
  platforms.py             registro de las 4 redes: icono, color y textos de cada una.
  animation.py             anim_state(t, cfg, L): unica fuente de verdad de la animacion.
  svg.py                   frame_svg(): arma el SVG completo a partir de las piezas anteriores.
  raster.py                raster_engine(), rasterize(): SVG -> PNG con alfa.
  render.py                render_webm(): fotogramas en paralelo + ffmpeg -> WebM.
  __main__.py              CLI: python -m overlay --twitch ... --kick ...
src/app.py               Servidor FastAPI. Solo traduce HTTP <-> Config. Sin lógica de dibujo.
src/static/index.html    Esqueleto de la interfaz. Sin framework ni paso de build.
src/static/style.css     Estilos de la interfaz.
src/static/app.js        Lógica de la interfaz (estado, validación, fetch a la API).
src/fonts/               Poppins Bold, Medium y Light (OFL 1.1) + su nota de licencia.
src/svg/                 Logos oficiales de Twitch, Kick, TikTok y YouTube. icons.py los lee.
requirements.txt         resvg-py es el rasterizador; cairosvg está comentado como alternativa.
                          imageio-ffmpeg es el respaldo portátil de ffmpeg (ver §10, Vercel).
Dockerfile                Deploy con ffmpeg del sistema (Render, Railway, cualquier contenedor).
vercel.json               Deploy serverless (ver §10). No reemplaza al Dockerfile, es otro camino.
docs/README.md           Para quien va a usar la app.
docs/CONTEXTO.md         Resumen corto de decisiones. Este archivo es la versión larga.
```

`src/overlay/` es el único paquete con lógica de verdad, dividido por responsabilidad (ver
§4). `src/app.py` deliberadamente no sabe nada de SVG ni de geometría: si te encuentras
escribiendo coordenadas en `app.py`, algo se salió de lugar.

Los módulos de `overlay/` calculan la ruta a `fonts/` y a `svg/` a partir de su propio
`__file__` (ver `typography.py` e `icons.py`), por eso el paquete, `fonts/` y `svg/`
viven juntos dentro de `src/`. Lo mismo pasa con `app.py` y `static/`. Si alguno se
mueve solo, esas rutas dejan de coincidir. `CLAUDE.md` y `requirements.txt` se quedan
en la raíz porque ahí es donde las herramientas (pip, Claude Code) los buscan por
convención.

`import overlay` sigue funcionando igual que cuando era un solo archivo: `__init__.py`
reexporta toda la API pública, así que `app.py` no tuvo que cambiar una sola línea al
partirlo en módulos.

---

## 3. Cómo fluye una petición

```
navegador
   │  GET /preview.svg?twitch=...&animate=1
   ▼
app.py: preview()  ──► Config(...).clean()  ──► overlay.frame_svg(99.0, cfg, cycle=3.4)
   │                                                     │
   │                                            SVG + animaciones SMIL
   ▼
<img src="/preview.svg?..."> el navegador reproduce la entrada en bucle
```

```
navegador
   │  POST /render  {twitch, kick, label, position, align, animation, duration, fps}
   ▼
app.py: render()  ──► overlay.render_webm(cfg, ruta_temporal)
                              │
                              ├─ 180 llamadas a frame_svg(t, cfg)      ← t en segundos
                              ├─ rasterize() de cada una a PNG con alfa (en paralelo)
                              └─ ffmpeg junta los PNG en WebM VP9 yuva420p
                                        │
                              FileResponse, y el temporal se borra después
```

La diferencia entre los dos caminos es **solo** el argumento `cycle` de `frame_svg`.
Mismo SVG, mismas funciones de animación.

---

## 4. El motor, por partes

El paquete `src/overlay/` sigue el mismo orden que esta sección: cada `4.N` corresponde
a un módulo. `frame_svg()` (§4.5, en `svg.py`) es el que importa y conecta todo lo
demás; el resto de los módulos no se conocen entre sí más de lo necesario
(`layout.py` importa `typography.py`, `svg.py` importa `layout.py`/`animation.py`/
`icons.py`/`typography.py`, y así).

### 4.1 Tipografía convertida a trazos (`typography.py`: `measure`, `text_path`)

No se usa `<text>` en ninguna parte. `fontTools` abre el `.ttf`, saca el contorno de
cada glifo con `SVGPathPen` y lo escribe como `<path>` con un `transform` que aplica
la escala y voltea el eje Y (las fuentes crecen hacia arriba, el SVG hacia abajo).

Dos razones:

1. El render no depende de fuentes instaladas en el sistema. Sale idéntico en
   cualquier máquina y en cualquier rasterizador.
2. `measure()` da el ancho real del texto **antes** de dibujarlo. De ahí sale el
   ajuste automático del cuerpo de letra, que es lo que evita que un nombre largo
   como `cristian_shippo` se desborde de la barra.

`text_path()` acepta `anchor` en `start`, `middle` o `end`, resuelto restando el
ancho medido. No existe `text-anchor` porque no hay elementos de texto.

Si cambias de fuente: reemplaza los `.ttf` y ajusta el diccionario `FONTS`. Nada más
depende del nombre del archivo.

### 4.2 `Config` y `clean()` (`config.py`)

Un dataclass plano con todo lo que el usuario puede elegir: un campo `str | None` por
cada una de las 4 plataformas (`twitch`, `kick`, `tiktok`, `youtube`), más texto,
posición, alineación, animación, duración y fps. `clean()` es el único lugar donde se
validan y normalizan los valores: recorta espacios, convierte cadenas vacías en
`None`, cae a los valores por defecto si llega una opción desconocida y limita
duración y fps.

**Regla que sostiene todo:** `clean()` cuenta cuántas de las 4 plataformas quedaron
con nombre. Cero, lanza `ValueError` ("al menos una"). Más de dos, también
("como máximo dos a la vez"). La interfaz también lo valida (deshabilita los
interruptores apagados en cuanto hay 2 activos, ver §5), pero la validación real
vive aquí, así que llamar a la API directamente tampoco puede saltársela. Devuelve
un 400 con el motivo.

`clean()` devuelve una **Config nueva**, no muta. Las funciones de dibujo asumen que
reciben una config ya limpia.

`Config.active()` devuelve `[(id_plataforma, nombre), ...]`, con 1 o 2 elementos, en
el orden de `PLATFORM_ORDER` (`constants.py`: twitch, kick, tiktok, youtube). Es el
único lugar del código que decide "cuál va a la izquierda y cuál a la derecha": todo
lo demás (`layout.py`, `svg.py`) itera sobre esa lista en vez de preguntar por una
plataforma en particular. Si agregas una quinta plataforma, el registro nuevo va en
`platforms.py` y el id nuevo en `PLATFORM_ORDER`; el resto del motor no necesita
saber que existe.

### 4.3 `layout(cfg)` — toda la geometría en un solo lugar (`layout.py`)

Devuelve un diccionario con las coordenadas ya resueltas. Ninguna otra función
calcula posiciones: si necesitas una coordenada nueva, se agrega aquí.

Orden en que decide las cosas, que importa:

1. **Ancho.** Con dos plataformas la barra siempre mide `MAXW`. Con una sola, mide lo
   que necesite el contenido, entre 420 y `MAXW`.
2. **Cuerpo de letra.** Se calcula el espacio disponible por lado y se compara con el
   ancho medido del nombre más largo. Si no cabe, se reduce proporcionalmente, con
   piso en `NAME_MIN`. Con una sola plataforma se parte de un cuerpo mayor
   (`NAME_MAX_1`) porque sobra espacio.
3. **Posición horizontal (`bx`).** Se resuelve *después* del ancho, por eso centrar
   funciona igual cuando la barra se encogió.
4. **Costura diagonal (`seam`).** Solo existe con dos plataformas: es el par de
   coordenadas X arriba y abajo de la línea que separa el color de la izquierda del
   de la derecha (cada una tiñe la barra con su propio `Platform.color`, ver 4.2).
   Con una sola plataforma es `None` y el código de dibujo se salta la línea y usa
   la barra completa como región de tinte.
5. **Etiqueta de arriba (`lab_x`).** Sigue la alineación de la barra.

Constantes que puedes tocar sin romper nada, todas en `constants.py`:

| Constante | Qué es | Cuidado |
| --- | --- | --- |
| `W`, `H` | Lienzo, 1080×1920 | Cambiarlo implica revisar `POSITIONS` |
| `MARGIN` | Margen lateral mínimo | |
| `MAXW` | Ancho máximo de la barra | **No subir de 822 sin pensarlo**, ver §6 |
| `BH`, `BR` | Alto y radio de la barra | |
| `PAD`, `ICON`, `GAPIT`, `CGAP` | Espaciado interno | Alimentan el cálculo de `avail` |
| `POSITIONS` | Las tres alturas en píxeles | |
| `NAME_MAX_2`, `NAME_MAX_1`, `NAME_MIN` | Rango del cuerpo de letra | |
| `VIOLET`, `GREEN`, `TIKTOK`, `YOUTUBE`... | Colores base | El color/icono/texto de cada red vive en `platforms.py`, no aquí |
| `PLATFORM_ORDER` | Las 4 plataformas, en el orden izquierda→derecha | Config.active() lo respeta |
| `INTRO` | Duración de la entrada, en segundos | Compartida por video y vista previa |

### 4.4 `anim_state(t, cfg, L)` — la única fuente de verdad de la animación (`animation.py`)

Función pura: recibe el segundo `t` y devuelve un diccionario con el estado visual en
ese instante.

```python
{
  "wipe": float,          # ancho del rectángulo de recorte del barrido
  "tx", "ty": float,      # desplazamiento de la barra completa
  "sx", "sy": float,      # escala de la barra, siempre desde su centro
  "op": float,            # opacidad de la barra completa
  "tw_dy", "tw_op": float,  # bloque de la izquierda (la primera de Config.active())
  "kk_dy", "kk_op": float,  # bloque de la derecha (la segunda, si hay dos)
  "lb_dx", "lb_dy", "lb_op": float,  # etiqueta de arriba
}
```

Las claves se llaman `tw_*`/`kk_*` por como empezó el proyecto (solo Twitch y Kick),
pero hoy son genéricas: identifican el primer y segundo bloque de la barra, sea cual
sea la plataforma que ocupe ese lado (`svg.py` los asigna por posición, no por
nombre). Arriba se calcula el escalonado que comparten todas las animaciones (la
izquierda entra primero, la derecha después, la etiqueta al final) y luego cada
`elif` sobrescribe lo suyo. Con una sola plataforma el escalonado se colapsa para
que no haya una espera rara.

Auxiliares: `_ease_out` es un cúbico de salida normal; `_ease_back` se pasa del
destino y regresa, es lo que hace el rebote; `_seg(t, a, b, ease)` normaliza un tramo
entre dos segundos y le aplica la curva.

**Agregar una animación nueva** son tres pasos:

1. Un `elif kind == "loquesea":` dentro de `anim_state`, escribiendo en las claves de
   `st`. No agregues claves nuevas sin revisar `frame_svg`, que es quien las consume.
2. Una entrada en el diccionario `ANIMATIONS` de `constants.py` (nombre interno →
   etiqueta visible). `clean()` valida contra ese diccionario, así que sin esto la
   opción se ignora.
3. Un `<option>` en el `<select id="animation">` de `static/index.html`.

No hace falta tocar el rasterizado, el SMIL ni ffmpeg. La vista previa animada sale
gratis, por el mecanismo de §4.5.

### 4.5 `frame_svg(t, cfg, cycle=None)` — arma el SVG (`svg.py`)

Con `cycle=None` devuelve el fotograma del segundo `t`, estático. Es lo que consume
el render de video.

Con `cycle=3.4` devuelve el estado final **más** animaciones SMIL: muestrea
`anim_state` 26 veces a lo largo de `INTRO` y convierte esas muestras en atributos
`values` y `keyTimes`. Eso es lo que hace que la vista previa del navegador se anime
sin renderizar un solo video.

La consecuencia buena: la vista previa y el video **no pueden desincronizarse**,
porque salen de la misma función. Si agregas una animación, aparece en los dos lados
sin trabajo extra.

Los ayudantes internos `anim()` y `anim_xy()` devuelven cadena vacía cuando
`cycle is None`, o cuando todas las muestras son iguales (no tiene sentido animar
algo que no cambia). Por eso el mismo `f-string` sirve para los dos modos.

**El anidado de grupos importa y es frágil.** De fuera hacia dentro:

```
<g opacity>              ← st["op"]
  <g translate>          ← st["tx"], st["ty"]
    <g translate(cx,cy)>       centro de la barra
      <g scale>          ← st["sx"], st["sy"]
        <g translate(-cx,-cy)> vuelta al origen
          <g clip-path=wipe>   ← st["wipe"]
             barra, tintes, costura, borde, bloques
```

El sándwich de traslaciones alrededor del `scale` es lo que hace que la barra escale
desde su propio centro y no desde la esquina del lienzo. Si agregas un grupo, cuenta
los `</g>` del final: son seis y están todos en una sola línea.

### 4.6 Rasterizado y render (`raster.py`, `render.py`)

`raster_engine()` prueba `resvg_py` y luego `cairosvg`, memoriza el resultado y, si no
hay ninguno, lanza un error con las instrucciones de instalación. `rasterize()`
despacha al que haya. Las dos viven en `raster.py`.

`render_webm()`, en `render.py`, reparte los fotogramas entre procesos con
`ProcessPoolExecutor` y después llama a ffmpeg. Cada worker (`_worker`, en el mismo
archivo) reconstruye la `Config` desde un dict porque los argumentos tienen que ser
serializables entre procesos.

Los parámetros de ffmpeg no son negociables si quieres conservar el alfa:
`-c:v libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0`.

---

## 5. La interfaz

Sin framework ni paso de build, pero dividida en tres archivos por tipo, todos dentro
de `src/static/`:

- `index.html` — el esqueleto: los cuatro bloques de plataforma (Twitch, Kick, TikTok,
  YouTube) con interruptor y campo de nombre, los controles (texto, animación, altura,
  alineación, duración), el botón, y a la derecha un escenario 9:16 con la vista previa
  sobre un fondo intercambiable entre cuadros, oscuro y claro, para revisar contraste.
  Enlaza a los otros dos con `<link rel="stylesheet" href="/static/style.css">` y
  `<script src="/static/app.js">`.
- `style.css` — todo el CSS, incluida una regla `:has()` que atenúa los interruptores
  deshabilitados.
- `app.js` — toda la lógica, alrededor de un arreglo `PLATFORMS` (id, checkbox, campo
  de nombre, panel) para no repetir cuatro veces la misma lógica:
  - `estado()` junta el formulario en el mismo objeto que espera la API.
  - `activas()` devuelve las plataformas con el interruptor encendido.
  - `validar()` decide el mensaje de error y si el botón va deshabilitado. Falla si hay
    cero activas, si hay más de dos, o si a alguna activa le falta el nombre.
  - `refrescar()` sincroniza el aspecto de los bloques, valida, y con 220 ms de retraso
    actualiza el `src` de la vista previa. Si la validación falla, quita el `src` para
    no dejar una imagen rota. También es quien **deshabilita los interruptores apagados**
    en cuanto hay 2 plataformas activas, para que nunca se pueda llegar a un estado
    inválido desde la interfaz (el límite real de todos modos vive en `clean()`, ver 4.2).

`app.py` sirve `index.html` con una ruta propia (`GET /`, lee el archivo y lo devuelve
como `HTMLResponse`) y monta `/static` con `StaticFiles` para que el navegador pueda
pedir `style.css` y `app.js` por su cuenta. Si agregas un archivo nuevo dentro de
`static/`, no hace falta tocar el montaje: ya sirve toda la carpeta.

**Agregar un control nuevo toca cuatro lugares, en este orden:**

1. `overlay/config.py`: campo en `Config`, normalización en `clean()`. Si el valor
   viene de una constante nueva, agrégala en `overlay/constants.py`.
2. `app.py`: campo en `RenderIn` y parámetro en `preview()`.
3. `static/index.html`: el elemento y su `id`; `static/app.js`: el `id` en la lista de
   escuchas y una línea en `estado()`.
4. `overlay/__main__.py`: el argumento de `argparse`, si tiene sentido desde el CLI.

Olvidar el paso 2 es el error silencioso más probable: la interfaz manda el valor, el
servidor lo ignora y no falla nada.

**Agregar una quinta plataforma** toca cinco lugares:

1. `overlay/constants.py`: el id nuevo al final de `PLATFORM_ORDER`, y sus colores.
2. `src/svg/xxx-icon.svg`: el logo oficial (ver §6), bajado de la guía de marca de la
   plataforma. `overlay/icons.py`: la función `xxx_icon(x, y)` que lo carga (calca las
   que ya existen; solo cambia el nombre de archivo y, si el SVG ya trae su propio
   fondo como el de YouTube, el `bg=None`).
3. `overlay/platforms.py`: la entrada en `PLATFORMS` (label, url, icono, color,
   `edge_light`/`edge_dark`, `tint_opacity`, `text_white`).
4. `overlay/config.py`: el campo `str | None` en `Config`. `clean()`, `active()` y
   `slug()` no necesitan cambios: ya iteran sobre `PLATFORM_ORDER`.
5. `app.py` (`RenderIn` y `preview()`), `static/index.html` (el bloque), y
   `overlay/__main__.py` (el argumento), igual que con cualquier control nuevo.

`layout.py` y `svg.py` no necesitan tocarse: ya trabajan sobre `Config.active()` en
vez de preguntar por una plataforma en particular.

---

## 6. Restricciones que no son negociables

**Zona segura.** `MAXW = 822` y `MARGIN = 48` dejan libre la columna de botones de
TikTok y Reels, que vive aproximadamente en `x > 880`. La altura "media" deja libre el
tercio inferior, donde van los subtítulos de la plataforma. Ensanchar la barra hace
que los botones de la app queden encima del overlay.

**Legibilidad sobre cualquier fondo.** El fondo de la barra es negro al 62 %, no un
bloque sólido, para que se siga viendo el video. Lo que lo salva sobre escenas claras
son las dos sombras (`#lift` para la barra, `#liftText` para el texto). Si las quitas,
el overlay desaparece sobre fondos brillantes.

**Los filtros llevan `color-interpolation-filters="sRGB"`.** Sin eso, resvg —que sigue
el estándar al pie de la letra— aplica las sombras en espacio lineal y el texto sale
apagado. cairosvg lo ignoraba, así que el problema solo aparece al cambiar de motor.
Cualquier filtro nuevo necesita el mismo atributo.

**Los iconos son los logos oficiales**, guardados como SVG en `src/svg/` (uno por
plataforma, bajados de la guía de marca de cada una). `overlay/icons.py` los lee al
vuelo: extrae el `viewBox` y el contenido del archivo, lo escala para que ocupe un
64 % del cuadrado `ICON` y lo centra ahí (YouTube usa 88 %, porque su SVG ya trae su
propio fondo redondeado y no hace falta dibujarle uno encima). Para cambiar un logo,
alcanza con reemplazar el archivo correspondiente en `src/svg/`: nada más depende de
su contenido, solo del nombre. Al ser marcas de terceros, cualquier reemplazo tiene
que respetar las reglas de uso de la guía de marca de esa plataforma.

**Como máximo dos plataformas a la vez.** No es una limitación técnica cualquiera:
`MAXW` y el ancho del icono/nombre están calibrados para dos bloques como mucho. Si
alguna vez hace falta mostrar tres o más, hay que rehacer la geometría de `layout.py`
desde cero, no solo subir el límite de `Config.clean()`.

---

## 7. Cosas que ya nos mordieron

- **cairosvg no arranca en Windows.** Falla con `no library called "cairo-2" was
  found` porque busca DLL que el sistema no trae. Por eso el rasterizador principal
  es `resvg-py`, que llega como rueda de pip sin nada externo. La alternativa, si
  alguien insiste con cairosvg, es instalar el GTK3 Runtime.
- **`ffprobe` reporta `pix_fmt=yuv420p` aunque el alfa esté ahí.** VP9 guarda el canal
  alfa en una pista aparte. No es un error. Lo que hay que mirar es el tag:
  ```
  ffprobe -v error -show_streams salida.webm | grep alpha_mode    # alpha_mode=1
  ```
- **Para decodificar un WebM con alfa hay que forzar el decodificador:**
  `ffmpeg -vcodec libvpx-vp9 -i entrada.webm ...`. El nativo descarta el alfa y vas a
  creer que el archivo salió mal.
- **ProRes 4444 también sirve** y Filmora lo lee, pero para 6 segundos pesa 31 MB
  contra 132 KB del WebM. Solo como respaldo si alguien reporta que su instalación no
  digiere el WebM.
- **PowerShell no tiene `source`.** El activador es `.\.venv\Scripts\Activate.ps1`, y
  si las directivas de ejecución lo bloquean:
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.
- **ffmpeg recién instalado no aparece hasta reiniciar la terminal**, porque el PATH
  se lee al abrirla.

---

## 8. Cómo probar un cambio

Los comandos de Python se ejecutan parado en `src/` (es donde el paquete `overlay`
puede importarse directo).

```bash
# ¿arranca y qué motor tiene?
curl http://127.0.0.1:8000/health

# geometría, sin levantar el servidor
cd src
python -c "from overlay import Config, layout; print(layout(Config('Loon_VT','LoonVT').clean()))"

# un fotograma suelto a PNG, para mirarlo
python -c "
from overlay import Config, frame_svg, rasterize
rasterize(frame_svg(0.4, Config('Loon_VT','LoonVT').clean()), 'prueba.png')"

# el video, por CLI (python -m, porque overlay ahora es un paquete)
python -m overlay --twitch Loon_VT --kick LoonVT --animation rebote --duration 4

# ¿sobrevivió el alfa?
ffprobe -v error -show_streams overlay-loon_vt.webm | grep alpha_mode
```

Casos que conviene revisar cuando toques `layout()` o `frame_svg()`, porque cada uno
recorre una rama distinta:

1. Dos plataformas con nombres cortos (`Loon_VT` / `LoonVT`).
2. Dos con un nombre largo (`cristian_shippo`), que dispara la reducción de letra.
3. Cada plataforma sola (Twitch, Kick, TikTok, YouTube): sin costura, barra encogida,
   cuerpo de letra mayor. TikTok y YouTube valen la pena en particular porque
   `text_white=False` en TikTok cambia el color del texto (ver `platforms.py`).
4. Las tres alineaciones, sobre todo con una sola plataforma.
5. Las seis animaciones, en `t = 0.15`, `0.4` y `1.2`.
6. La vista previa con `animate=1`, comprobando que el SVG sale bien formado.
7. Tres plataformas activas (por API o CLI): `clean()` debe rechazarlas con 400.

No hay suite de pruebas. Si vas a agregar una, `layout()` y `anim_state()` son
funciones puras y el sitio obvio por donde empezar.

---

## 9. Convenios

- Comentarios y mensajes al usuario en español. En los comentarios del código se
  evitan las tildes para no depender de la codificación del terminal; en los textos
  que ve el usuario, sí se usan.
- El paquete `overlay/` no importa nada de FastAPI. Tiene que seguir funcionando
  como CLI suelto (`python -m overlay`).
- Los números mágicos viven como constantes en `overlay/constants.py`, no dispersos
  en las funciones de dibujo.
- Cada módulo de `overlay/` tiene una sola responsabilidad (ver §4). Si una función
  nueva no encaja claramente en ninguno de los existentes, es una señal de que hace
  falta un módulo nuevo, no de que hay que forzarla en uno que no le corresponde.
- Los archivos generados (`.webm`, `.mov`, `frames/`) están en el `.gitignore`.

---

## 10. Desplegar

### Docker (Render, Railway, cualquier host de contenedores)

El `Dockerfile` instala `ffmpeg` con `apt-get` y corre `uvicorn` directo. No necesita
nada más: es el camino "natural" para esta app, porque el proceso vive todo el tiempo
que quiera y tiene disco propio.

### Vercel

Vercel es serverless: no corre el `Dockerfile`, cada request (o casi) es una función
nueva, y el directorio de despliegue es de solo lectura salvo `/tmp`. `vercel.json`,
en la raíz, apunta al entrypoint que Vercel detecta solo (`src/app.py`, que ya expone
`app`; FastAPI y Flask están entre los frameworks que reconoce sin configuración
extra). Tres cosas que no son obvias:

- **No hay `ffmpeg` instalado.** `overlay/render.py` primero busca `ffmpeg` en el
  PATH (sirve para Docker y desarrollo local) y, si no aparece, cae al binario
  portátil de `imageio-ffmpeg` (ver `requirements.txt`), que trae su propio ejecutable
  de ffmpeg empaquetado y no depende de nada del sistema.
- **`/var/task` es de solo lectura.** Los fotogramas y el WebM final ya se escriben
  con `tempfile` en el directorio temporal del sistema, que en Linux es `/tmp` por
  default, así que esto no necesitó cambios.
- **`includeFiles: "src/**"` en `vercel.json` es necesario.** `fonts/`, `svg/` y
  `static/` se leen por ruta en tiempo de ejecución (`StaticFiles`, `text_path()` en
  `typography.py`, `icons.py`), no por `import`, y el rastreador de dependencias de
  Vercel no los encuentra solo si no se lo decís explícitamente.

`maxDuration: 60` en `vercel.json` es el tope del plan Hobby. El render de 180
fotogramas (6 s a 30 fps) puede acercarse a eso en una función con pocos núcleos; si
se corta, subí ese número (necesita plan Pro, hasta 300 s o más con Fluid Compute) o
bajá `duration`/`fps` desde la interfaz. `resvg-py` también necesita rueda compatible
con el entorno de build de Vercel (Linux x86_64); si falla la instalación, revisá que
haya una rueda manylinux publicada para la versión de Python del proyecto.

Deploy: `vercel` (preview) o `vercel --prod`, parado en la raíz del repo.

## 11. Ideas pendientes

- Empaquetarlo en Docker.
- Selector de colores, para reusar el generador con otra paleta.
- Variante para cuando el nombre es idéntico en las dos plataformas: mostrarlo una
  sola vez, grande, cortado por la diagonal, con los dos iconos juntos al lado. Hoy
  se repite el mismo texto a los dos lados y obliga a encoger la letra.
- Integrar la versión apaisada de 1600×900 para pantalla de "ya vuelvo", que existe
  como SVG suelto y nunca entró a la app.
- Animación de salida, además de la de entrada.
