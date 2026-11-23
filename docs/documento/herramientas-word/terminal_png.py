"""Dibuja un extracto de una salida de consola como PNG con aspecto de terminal.

Se usa para la evidencia del 2.3.2: la imagen muestra líneas reales de la
ejecución (pytest, flutter test o la API), nunca texto escrito a mano.
"""
import textwrap

from PIL import Image, ImageDraw, ImageFont

FUENTE = r'C:\Windows\Fonts\consola.ttf'
FUENTE_B = r'C:\Windows\Fonts\consolab.ttf'
TAM = 21
ANCHO_COLS = 92
FONDO = (30, 30, 30)
BARRA = (60, 60, 60)
COLORES = {
    'normal': (212, 212, 212),
    'cmd': (220, 220, 170),
    'ok': (106, 200, 120),
    'mal': (240, 110, 110),
    'gris': (140, 140, 140),
    'titulo': (156, 220, 254),
}


def color_de(linea):
    if linea.startswith('$ '):
        return 'cmd'
    if ' PASSED' in linea or ' passed' in linea or 'All tests passed' in linea or linea.startswith('OK '):
        return 'ok'
    if ' FAILED' in linea or ' failed' in linea or ' ERROR' in linea or linea.startswith('MAL '):
        return 'mal'
    if linea.startswith('…') or linea.startswith('platform') or linea.startswith('collected') or linea.startswith('rootdir'):
        return 'gris'
    return 'normal'


def dibujar(titulo, lineas, ruta):
    f = ImageFont.truetype(FUENTE, TAM)
    fb = ImageFont.truetype(FUENTE_B, TAM)
    renglones = []
    for ln in lineas:
        c = color_de(ln)
        partes = textwrap.wrap(ln, ANCHO_COLS, subsequent_indent='    ', break_long_words=True,
                               break_on_hyphens=False) or ['']
        renglones += [(p, c) for p in partes]
    _, _, w_car, h_car = f.getbbox('M')
    alto_l = int(TAM * 1.45)
    ancho = int(w_car * (ANCHO_COLS + 4)) + 40
    alto = 44 + 18 + alto_l * len(renglones) + 18
    img = Image.new('RGB', (ancho, alto), FONDO)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, ancho, 34], fill=BARRA)
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([14 + i * 22, 11, 26 + i * 22, 23], fill=col)
    d.text((90, 8), titulo, font=fb, fill=COLORES['titulo'])
    y = 44 + 10
    for txt, c in renglones:
        d.text((20, y), txt, font=fb if c == 'cmd' else f, fill=COLORES[c])
        y += alto_l
    img.save(ruta, optimize=True)
    return ruta
