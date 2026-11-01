"""Inserta las capturas web del Sprint 3 en la fila «Prototipo» de cada historia.

Uso: python capturas_sprint3.py ENTRADA.docx SALIDA.docx CARPETA_CAPTURAS

Agrega cada PNG a word/media, su relación en document.xml.rels y un dibujo
en línea con el mismo XML que usan las capturas del Sprint 2 (dos por renglón).
No toca ninguna imagen que ya exista.
"""
import sys, re, zipfile, struct, os
sys.path.insert(0, r'D:\UNI\Si2\PROYECTO_MEDICOS\docs\documento\herramientas-word')
from comun import *

ENT, SAL, CAP = sys.argv[1], sys.argv[2], sys.argv[3]

CAPTURAS = {
    'US-23 — Ficha asistida en mostrador': [
        '52-web-mostrador-paciente-elegido', '53-web-mostrador-horario-elegido',
        '54-web-mostrador-ficha-reservada', '55-web-mostrador-cobro-en-ventanilla'],
    'US-30 — Reportes operativos': [
        '61-web-reporte-fichas-constructor', '62-web-reporte-fichas-resultado',
        '63-web-reporte-fichas-pdf', '64-web-reporte-pagos-constructor',
        '65-web-reporte-pagos-resultado', '66-web-reporte-pagos-excel'],
}
ANCHO = 2606040          # 2,85 in, como las del Sprint 2
ANCHO_VERTICAL = 1600200  # 1,75 in para el PDF, que es vertical

def png_size(path):
    with open(path, 'rb') as f:
        head = f.read(24)
    return struct.unpack('>II', head[16:24])

z = zipfile.ZipFile(ENT)
x = z.read('word/document.xml').decode('utf8')
rels = z.read('word/_rels/document.xml.rels').decode('utf8')
medias = [n for n in z.namelist() if n.startswith('word/media/')]
n_media = max(int(m) for n in medias for m in re.findall(r'(\d+)', os.path.basename(n))) + 1
n_rid = max(int(i) for i in re.findall(r'Id="rId(\d+)"', rels)) + 1
n_doc = max(int(i) for i in re.findall(r'<wp:docPr id="(\d+)"', x)) + 1

nuevos = {}   # ruta en el zip -> bytes
nuevas_rels = []

def dibujo(nombre):
    global n_media, n_rid, n_doc
    path = os.path.join(CAP, nombre + '.png')
    w, h = png_size(path)
    cx = ANCHO_VERTICAL if h > w else ANCHO
    cy = round(cx * h / w)
    media = f'media/image{n_media}.png'
    nuevos['word/' + media] = open(path, 'rb').read()
    rid = f'rId{n_rid}'
    nuevas_rels.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="{media}"/>')
    did = n_doc
    n_media += 1; n_rid += 1; n_doc += 1
    return (f'<w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
            f'<wp:docPr id="{did}" name="Captura {did}" descr="{esc(nombre)}"/>'
            '<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:nvPicPr><pic:cNvPr id="{did}" name="{esc(nombre)}.png"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing>')

E = elements(x)
s3 = buscar(x, E, 'Sprint 3', 'Titulo11')
s4 = buscar(x, E, 'Sprint 4', 'Titulo11')
ops = {}
for titulo, fotos in CAPTURAS.items():
    n = buscar(x, E, titulo, 'Titulo4', s3, s4)
    t, a, b = E[n + 1]
    assert t == 'tbl', titulo
    tbl = x[a:b]
    ultima = rows(tbl)[-1]
    tc = cells(ultima)[0]
    assert 'Prototipo' in txt(tc), titulo
    PPR_IMG = '<w:pPr><w:ind w:firstLine="0"/><w:jc w:val="center"/></w:pPr>'
    parrafos = ''
    for i in range(0, len(fotos), 2):
        par = fotos[i:i + 2]
        runs_ = '<w:r><w:t xml:space="preserve"> </w:t></w:r>'.join(f'<w:r>{dibujo(f)}</w:r>' for f in par)
        parrafos += f'<w:p>{PPR_IMG}{runs_}</w:p>'
    # Después del párrafo «Prototipo (…)», antes de los vacíos del final.
    ps = PARA_RE.findall(tc)
    proto = next(p for p in ps if 'Prototipo' in txt(p))
    tc2 = tc.replace(proto, proto + parrafos, 1)
    ops[n + 1] = tbl.replace(tc, tc2, 1)

x2 = aplicar(x, E, ops)
rels2 = rels.replace('</Relationships>', ''.join(nuevas_rels) + '</Relationships>')

with zipfile.ZipFile(SAL, 'w', zipfile.ZIP_DEFLATED) as out:
    for info in z.infolist():
        if info.filename == 'word/document.xml':
            data = x2.encode('utf8')
        elif info.filename == 'word/_rels/document.xml.rels':
            data = rels2.encode('utf8')
        else:
            data = z.read(info.filename)
        out.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
    for nombre, data in nuevos.items():
        out.writestr(nombre, data, compress_type=zipfile.ZIP_DEFLATED)
print('capturas agregadas:', len(nuevos), '->', SAL)
