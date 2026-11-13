"""Pega una imagen nueva en el párrafo vacío que sigue a un título.

Uso:
  python insertar_imagen.py ENTRADA.docx SALIDA.docx IMAGEN.png \
      --seccion "Sprint 4" --titulo "2.1.1.3 Diagrama de Redes" [--ancho-cm 12]

Es la única herramienta que AGREGA una imagen (la regla 5 de
../como-editar-el-word.md es para las demás). Por eso hace lo mínimo y
comprueba todo antes de escribir:

- busca el título por texto dentro de la sección `Sprint N` (Titulo11) y exige
  que el párrafo siguiente esté vacío y sin imagen: no pisa nada;
- agrega `word/media/<nombre nuevo>`, una relación nueva en
  `word/_rels/document.xml.rels` y el `<w:drawing>` en línea, centrado, con el
  mismo XML que usan las imágenes del Sprint 3;
- las imágenes, medios y relaciones que ya estaban no se tocan (lo comprueba
  `verificar.py`: tiene que dar un dibujo más y el resto idéntico).
"""
import sys, re, zipfile, argparse
from PIL import Image
from comun import abrir, elements, txt, buscar, tiene_imagen

ap = argparse.ArgumentParser()
ap.add_argument('entrada'); ap.add_argument('salida'); ap.add_argument('imagen')
ap.add_argument('--seccion', required=True); ap.add_argument('--titulo', required=True)
ap.add_argument('--ancho-cm', type=float, default=12.0)
a = ap.parse_args()

if not a.imagen.lower().endswith('.png'):
    raise SystemExit('PARADO: sólo PNG (el tipo ya está declarado en [Content_Types].xml)')

x = abrir(a.entrada)
E = elements(x)
sec = buscar(x, E, a.seccion, 'Titulo11')
sig = next((n for n in range(sec + 1, len(E))
            if E[n][0] == 'p' and 'w:val="Titulo11"' in x[E[n][1]:E[n][2]][:600]), len(E))
t = buscar(x, E, a.titulo, desde=sec, hasta=sig)
t0, p0, p1 = E[t + 1]
hueco = x[p0:p1]
if t0 != 'p' or tiene_imagen(hueco) or txt(hueco).strip():
    raise SystemExit(f'PARADO: después de «{a.titulo}» no hay un párrafo vacío; no se pisa nada')

with zipfile.ZipFile(a.entrada) as z:
    nombres = set(z.namelist())
    rels = z.read('word/_rels/document.xml.rels').decode('utf8')
    tipos = z.read('[Content_Types].xml').decode('utf8')
if 'Extension="png"' not in tipos:
    raise SystemExit('PARADO: el documento no declara el tipo png')

k = 1
while f'word/media/image{k}.png' in nombres:
    k += 1
media = f'word/media/image{k}.png'
rid = 'rId' + str(max(int(i) for i in re.findall(r'Id="rId(\d+)"', rels)) + 1)
docpr = max(int(i) for i in re.findall(r'<wp:docPr id="(\d+)"', x)) + 1
if docpr >= 2 ** 31:
    raise SystemExit('PARADO: no queda un id de dibujo libre')

w, h = Image.open(a.imagen).size
cx = int(a.ancho_cm * 360000)
cy = int(cx * h / w)
nombre = f'Imagen {docpr}'
dibujo = (
    '<w:p><w:pPr><w:ind w:firstLine="0"/><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:noProof/></w:rPr>'
    f'<w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
    '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
    f'<wp:docPr id="{docpr}" name="{nombre}" descr="{a.titulo}"/>'
    '<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'noChangeAspect="1"/></wp:cNvGraphicFramePr>'
    '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
    '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
    '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
    f'<pic:nvPicPr><pic:cNvPr id="{docpr}" name="{nombre}"/><pic:cNvPicPr/></pic:nvPicPr>'
    f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
    f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
    '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
    '</wp:inline></w:drawing></w:r></w:p>')
x2 = x[:p0] + dibujo + x[p1:]
rel = (f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
       f'Target="media/image{k}.png"/>')
rels2 = rels.replace('</Relationships>', rel + '</Relationships>')

with zipfile.ZipFile(a.entrada) as src, zipfile.ZipFile(a.salida, 'w', zipfile.ZIP_DEFLATED) as z:
    for info in src.infolist():
        if info.filename == 'word/document.xml':
            data = x2.encode('utf8')
        elif info.filename == 'word/_rels/document.xml.rels':
            data = rels2.encode('utf8')
        else:
            data = src.read(info.filename)
        z.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
    z.write(a.imagen, media)
print(f'Listo: {a.salida}\n  {media} como {rid}, {a.ancho_cm} cm de ancho ({w}x{h} px), debajo de «{a.titulo}»')
