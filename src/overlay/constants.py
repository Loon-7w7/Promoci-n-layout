"""Numeros magicos del overlay: lienzo, paleta y tiempos de la animacion.

Todo lo que se puede tocar sin romper nada vive aqui. Ver CLAUDE.md #4.3 y #6
para el porque de cada valor.
"""

from __future__ import annotations

# ---------------------------------------------------------------- lienzo
W, H = 1080, 1920
MARGIN = 48             # margen lateral minimo
BH, BR = 170, 30        # alto y radio de la barra
MAXW = 822              # ancho maximo (deja libre la columna de botones)
PAD = 40                # margen interno
ICON = 68               # lado del icono
GAPIT = 16              # separacion icono -> texto
CGAP = 40               # separacion entre las dos plataformas
NAME_MAX_2 = 46         # cuerpo del nombre con dos plataformas
NAME_MAX_1 = 54         # cuerpo del nombre con una sola
NAME_MIN = 26

POSITIONS = {"alta": 620, "media": 1230, "baja": 1500}
ALIGNMENTS = ("izquierda", "centro", "derecha")

# nombre interno -> etiqueta para la interfaz
ANIMATIONS = {
    "barrido": "Barrido lateral",
    "deslizar": "Sube desde abajo",
    "rebote": "Sube con rebote",
    "escala": "Crece desde el centro",
    "cortina": "Se abre como cortina",
    "desvanecer": "Aparece suave",
}
INTRO = 1.15            # cuanto dura la entrada, en segundos

VIOLET = "#7C3AED"
VIOLET_DEEP = "#5B21B6"
GREEN = "#53FC18"
INK = "#07070A"
