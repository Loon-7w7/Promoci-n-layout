# CLAUDE.md

Guía del proyecto para trabajar sobre él con un asistente en el editor.
Léela antes de tocar código: casi todo lo que parece una decisión arbitraria tiene
un motivo, y varios de esos motivos costaron trabajo descubrirlos.

---

## 1. Qué hace esto

Genera un overlay de "sígueme en Twitch y Kick" para video vertical.

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
overlay.py          Motor completo. Sin dependencias de FastAPI. Ejecutable como CLI.
app.py              Servidor FastAPI. Solo traduce HTTP <-> Config. Sin lógica de dibujo.
static/index.html   Interfaz. Una sola página, sin framework ni paso de build.
fonts/              Poppins Bold, Medium y Light (OFL 1.1) + su nota de licencia.
requirements.txt    resvg-py es el rasterizador; cairosvg está comentado como alternativa.
README.md           Para quien va a usar la app.
CONTEXTO.md         Resumen corto de decisiones. Este archivo es la versión larga.
```

`overlay.py` es el único archivo con lógica de verdad. `app.py` deliberadamente no
sabe nada de SVG ni de geometría: si te encuentras escribiendo coordenadas en
`app.py`, algo se salió de lugar.

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

### 4.1 Tipografía convertida a trazos (`measure`, `text_path`)

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

### 4.2 `Config` y `clean()`

Un dataclass plano con todo lo que el usuario puede elegir. `clean()` es el único
lugar donde se validan y normalizan los valores: recorta espacios, convierte cadenas
vacías en `None`, cae a los valores por defecto si llega una opción desconocida y
limita duración y fps.

**Regla que sostiene todo:** si `twitch` y `kick` quedan ambos en `None`, `clean()`
lanza `ValueError`. Ese es el "al menos una plataforma" del requisito. La interfaz
también lo valida para desactivar el botón, pero la validación real vive aquí, así
que llamar a la API directamente tampoco puede saltárselo. Devuelve un 400 con el
motivo.

`clean()` devuelve una **Config nueva**, no muta. Las funciones de dibujo asumen que
reciben una config ya limpia.

### 4.3 `layout(cfg)` — toda la geometría en un solo lugar

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
   coordenadas X arriba y abajo de la línea que separa el lado morado del oscuro.
   Con una sola plataforma es `None` y el código de dibujo se salta la línea y usa
   la barra completa como región de tinte.
5. **Etiqueta de arriba (`lab_x`).** Sigue la alineación de la barra.

Constantes que puedes tocar sin romper nada, todas arriba del archivo:

| Constante | Qué es | Cuidado |
| --- | --- | --- |
| `W`, `H` | Lienzo, 1080×1920 | Cambiarlo implica revisar `POSITIONS` |
| `MARGIN` | Margen lateral mínimo | |
| `MAXW` | Ancho máximo de la barra | **No subir de 822 sin pensarlo**, ver §6 |
| `BH`, `BR` | Alto y radio de la barra | |
| `PAD`, `ICON`, `GAPIT`, `CGAP` | Espaciado interno | Alimentan el cálculo de `avail` |
| `POSITIONS` | Las tres alturas en píxeles | |
| `NAME_MAX_2`, `NAME_MAX_1`, `NAME_MIN` | Rango del cuerpo de letra | |
| `VIOLET`, `GREEN`, `INK` | Paleta | |
| `INTRO` | Duración de la entrada, en segundos | Compartida por video y vista previa |

### 4.4 `anim_state(t, cfg, L)` — la única fuente de verdad de la animación

Función pura: recibe el segundo `t` y devuelve un diccionario con el estado visual en
ese instante.

```python
{
  "wipe": float,          # ancho del rectángulo de recorte del barrido
  "tx", "ty": float,      # desplazamiento de la barra completa
  "sx", "sy": float,      # escala de la barra, siempre desde su centro
  "op": float,            # opacidad de la barra completa
  "tw_dy", "tw_op": float,  # bloque de Twitch
  "kk_dy", "kk_op": float,  # bloque de Kick
  "lb_dx", "lb_dy", "lb_op": float,  # etiqueta de arriba
}
```

Arriba se calcula el escalonado que comparten todas las animaciones (Twitch entra
primero, Kick después, la etiqueta al final) y luego cada `elif` sobrescribe lo suyo.
Con una sola plataforma el escalonado se colapsa para que no haya una espera rara.

Auxiliares: `_ease_out` es un cúbico de salida normal; `_ease_back` se pasa del
destino y regresa, es lo que hace el rebote; `_seg(t, a, b, ease)` normaliza un tramo
entre dos segundos y le aplica la curva.

**Agregar una animación nueva** son tres pasos:

1. Un `elif kind == "loquesea":` dentro de `anim_state`, escribiendo en las claves de
   `st`. No agregues claves nuevas sin revisar `frame_svg`, que es quien las consume.
2. Una entrada en el diccionario `ANIMATIONS` (nombre interno → etiqueta visible).
   `clean()` valida contra ese diccionario, así que sin esto la opción se ignora.
3. Un `<option>` en el `<select id="animation">` de `index.html`.

No hace falta tocar el rasterizado, el SMIL ni ffmpeg. La vista previa animada sale
gratis, por el mecanismo de §4.5.

### 4.5 `frame_svg(t, cfg, cycle=None)` — arma el SVG

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

### 4.6 Rasterizado y render

`raster_engine()` prueba `resvg_py` y luego `cairosvg`, memoriza el resultado y, si no
hay ninguno, lanza un error con las instrucciones de instalación. `rasterize()`
despacha al que haya.

`render_webm()` reparte los fotogramas entre procesos con `ProcessPoolExecutor` y
después llama a ffmpeg. Cada worker reconstruye la `Config` desde un dict porque los
argumentos tienen que ser serializables.

Los parámetros de ffmpeg no son negociables si quieres conservar el alfa:
`-c:v libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0`.

---

## 5. La interfaz

Una sola página, sin dependencias. Vale la pena mantenerla así.

Piezas: dos bloques de plataforma con interruptor y campo de nombre, los controles
(texto, animación, altura, alineación, duración), el botón, y a la derecha un
escenario 9:16 con la vista previa sobre un fondo intercambiable entre cuadros,
oscuro y claro, para revisar contraste.

- `estado()` junta el formulario en el mismo objeto que espera la API.
- `validar()` decide el mensaje de error y si el botón va deshabilitado.
- `refrescar()` sincroniza el aspecto de los bloques, valida, y con 220 ms de retraso
  actualiza el `src` de la vista previa. Si la validación falla, quita el `src` para
  no dejar una imagen rota.
- Mientras no edites el campo de Kick a mano, se copia lo que escribes en Twitch. Si
  lo vacías, vuelve a copiarse. La bandera es `kickTocado`.

**Agregar un control nuevo toca cuatro lugares, en este orden:**

1. `overlay.py`: campo en `Config`, normalización en `clean()`, y el uso donde toque.
2. `app.py`: campo en `RenderIn` y parámetro en `preview()`.
3. `index.html`: el elemento, su `id` en la lista de escuchas, y una línea en `estado()`.
4. El `argparse` del final de `overlay.py`, si tiene sentido desde el CLI.

Olvidar el paso 2 es el error silencioso más probable: la interfaz manda el valor, el
servidor lo ignora y no falla nada.

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

**Los iconos son formas geométricas propias**, no los logos oficiales de Twitch ni de
Kick. Si vas a usar los oficiales, bájalos de las guías de marca de cada plataforma y
respeta sus reglas de uso.

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

```bash
# ¿arranca y qué motor tiene?
curl http://127.0.0.1:8000/health

# geometría, sin levantar el servidor
python -c "from overlay import Config, layout; print(layout(Config('Loon_VT','LoonVT').clean()))"

# un fotograma suelto a PNG, para mirarlo
python -c "
from overlay import Config, frame_svg, rasterize
rasterize(frame_svg(0.4, Config('Loon_VT','LoonVT').clean()), 'prueba.png')"

# el video, por CLI
python overlay.py --twitch Loon_VT --kick LoonVT --animation rebote --duration 4

# ¿sobrevivió el alfa?
ffprobe -v error -show_streams overlay-loon_vt.webm | grep alpha_mode
```

Casos que conviene revisar cuando toques `layout()` o `frame_svg()`, porque cada uno
recorre una rama distinta:

1. Las dos plataformas con nombres cortos (`Loon_VT` / `LoonVT`).
2. Las dos con un nombre largo (`cristian_shippo`), que dispara la reducción de letra.
3. Solo Twitch, y solo Kick: sin costura, barra encogida, cuerpo de letra mayor.
4. Las tres alineaciones, sobre todo con una sola plataforma.
5. Las seis animaciones, en `t = 0.15`, `0.4` y `1.2`.
6. La vista previa con `animate=1`, comprobando que el SVG sale bien formado.

No hay suite de pruebas. Si vas a agregar una, `layout()` y `anim_state()` son
funciones puras y el sitio obvio por donde empezar.

---

## 9. Convenios

- Comentarios y mensajes al usuario en español. En los comentarios del código se
  evitan las tildes para no depender de la codificación del terminal; en los textos
  que ve el usuario, sí se usan.
- `overlay.py` no importa nada de FastAPI. Tiene que seguir funcionando como CLI
  suelto.
- Los números mágicos viven como constantes arriba de `overlay.py`, no dispersos en
  las funciones de dibujo.
- Los archivos generados (`.webm`, `.mov`, `frames/`) están en el `.gitignore`.

---

## 10. Ideas pendientes

- Empaquetarlo en Docker.
- Selector de colores, para reusar el generador con otra paleta.
- Variante para cuando el nombre es idéntico en las dos plataformas: mostrarlo una
  sola vez, grande, cortado por la diagonal, con los dos iconos juntos al lado. Hoy
  se repite el mismo texto a los dos lados y obliga a encoger la letra.
- Integrar la versión apaisada de 1600×900 para pantalla de "ya vuelvo", que existe
  como SVG suelto y nunca entró a la app.
- Animación de salida, además de la de entrada.
