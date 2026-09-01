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

# orden fijo de las plataformas soportadas. Decide cual va a la izquierda y
# cual a la derecha cuando hay dos activas (Config.active() lo respeta).
# Como maximo dos a la vez: lo valida Config.clean().
PLATFORM_ORDER = ("twitch", "kick", "tiktok", "youtube")

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
VIOLET_SOFT = "#A78BFA"
GREEN = "#53FC18"
GREEN_DEEP = "#2FA80A"
INK = "#07070A"

# TikTok: acento cian sobre fondo casi negro. YouTube: rojo. No son los
# logos oficiales (ver icons.py), pero sí los colores que la gente asocia
# de un vistazo a cada plataforma.
TIKTOK = "#25F4EE"
TIKTOK_DEEP = "#0FB8B2"
YOUTUBE = "#FF0033"
YOUTUBE_DEEP = "#B3001F"
YOUTUBE_SOFT = "#FF8FA3"
