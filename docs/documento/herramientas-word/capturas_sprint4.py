"""Inserta las capturas del Sprint 4 en la fila «Prototipo» de cada tarjeta de historia.

Uso: python capturas_sprint4.py ENTRADA.docx SALIDA.docx CARPETA_CAPTURAS

Igual que capturas_us23_us30.py (Sprint 3): agrega cada PNG a word/media, su
relación y un dibujo en línea. Las web van de a dos por renglón (2,85 in) y las
del celular de a tres (1,75 in). No toca ninguna imagen que ya exista y salta la
tarjeta que ya tenga capturas.
"""
import sys, re, zipfile, struct, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import *

ENT, SAL, CAP = sys.argv[1], sys.argv[2], sys.argv[3]

CAPTURAS = {
    'US-37': ['US-37-01-web-proyeccion-de-demanda', 'US-37-02-web-demanda-por-especialidad-y-franja'],
    'US-39': ['US-39-01-web-resumen-de-la-consulta', 'US-39-02-movil-resumen-de-la-consulta'],
    'US-40': ['US-40-02-produccion-como-prepararte', 'US-40-03-produccion-resumen-con-estudio', 'US-40-01-movil-como-prepararte'],
    'US-41': ['US-41-01-web-medico-resumen-del-historial', 'US-41-02-web-resumen-con-atenciones-citadas-y-preconsulta'],
    'US-42': ['US-42-02-web-resumen-pendiente', 'US-42-01-web-resumen-aprobado', 'US-42-03-web-resumen-aprobado-aviso'],
    'US-46': ['US-46-02-web-mis-fichas-de-medicina-general', 'US-46-03-web-comprobantes-con-qr', 'US-46-01-movil-mis-ultimas-2-facturas-con-qr'],
    'US-47': ['US-47-06-web-paciente-chat-abierto-con-receta', 'US-47-07-web-paciente-consulta-enviada',
              'US-47-08-web-paciente-urgencia-derivada', 'US-47-10-web-medico-bandeja-posible-urgencia',
              'US-47-12-web-medico-respuesta', 'US-47-15-web-paciente-respuesta-y-chat-cerrado',
              'US-47-17-movil-chat-abierto-con-receta', 'US-47-20-movil-consulta-enviada',
              'US-47-22-movil-push-tu-medico-te-respondio'],
    'US-48': ['US-48-04-web-paciente-elige-estrellas', 'US-48-05-web-paciente-calificacion-enviada',
              'US-48-03-web-medico-promedio-de-calificacion', 'US-48-02-movil-calificacion-enviada'],
    'US-49': ['US-49-01-movil-mis-medicamentos', 'US-49-02-movil-recordarme-activo-proxima-toma',
              'US-49-03-movil-notificacion-hora-de-tu-toma', 'US-49-04-movil-notificacion-tomada-posponer',
              'US-49-05-movil-toma-marcada-desde-la-notificacion'],
    'US-50': ['US-50-01-web-pregunta-cuanto-ganamos', 'US-50-02-web-cuentas-del-periodo'],
    'US-51': ['US-51-03-web-experiencia-plus', 'US-51-04-web-preconsulta', 'US-51-01-movil-plus-produccion', 'US-51-02-movil-como-llegar-mapa'],
    'US-52': ['US-52-01-web-sin-turnos-ofrece-lista-de-espera', 'US-52-02-web-quedaste-en-la-lista',
              'US-52-03-web-mis-fichas-en-lista-de-espera', 'US-52-04-movil-mis-fichas-en-lista-de-espera'],
    'US-53': ['US-53-01-web-signos-normales-con-imc', 'US-53-02-web-anormal-se-marca', 'US-53-06-web-historial-del-medico',
              'US-53-09-web-medico-evolucion-presion', 'US-53-11-web-paciente-graficas-presion-y-peso',
              'US-53-12-movil-mis-signos-vitales-produccion', 'US-53-13-movil-graficas-presion-y-peso-produccion'],
}
ANCHO = 2606040           # 2,85 in
ANCHO_VERTICAL = 1600200  # 1,75 in
PPR_IMG = '<w:pPr><w:ind w:firstLine="0"/><w:jc w:val="center"/></w:pPr>'


def png_size(path):
    with open(path, 'rb') as f:
        head = f.read(24)
    assert head[:8] == b'\x89PNG\r\n\x1a\n', path
    return struct.unpack('>II', head[16:24])


z = zipfile.ZipFile(ENT)
x = z.read('word/document.xml').decode('utf8')
rels = z.read('word/_rels/document.xml.rels').decode('utf8')
medias = [n for n in z.namelist() if n.startswith('word/media/')]
n_media = max(int(m) for n in medias for m in re.findall(r'(\d+)', os.path.basename(n))) + 1
n_rid = max(int(i) for i in re.findall(r'Id="rId(\d+)"', rels)) + 1
n_doc = max(int(i) for i in re.findall(r'<wp:docPr id="(\d+)"', x)) + 1
nuevos, nuevas_rels = {}, []


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


def renglones(fotos):
    """Web de a dos, celular de a tres; cada grupo en su párrafo centrado."""
    web = [f for f in fotos if '-movil-' not in f]
    cel = [f for f in fotos if '-movil-' in f]
    out = ''
    for grupo, n in ((web, 2), (cel, 3)):
        for i in range(0, len(grupo), n):
            sep = '<w:r><w:t xml:space="preserve"> </w:t></w:r>'
            out += f'<w:p>{PPR_IMG}' + sep.join(f'<w:r>{dibujo(f)}</w:r>' for f in grupo[i:i + n]) + '</w:p>'
    return out


E = elements(x)
s4 = next(i for i, (t, a, b) in enumerate(E) if t == 'p' and txt(x[a:b]).strip() == 'Sprint 4' and 'Titulo1' in x[a:b])
ops, puestas = {}, 0
for us, fotos in CAPTURAS.items():
    n = next(i for i in range(s4, len(E)) if E[i][0] == 'p' and re.match(rf'{us}\s*[—-]', txt(x[E[i][1]:E[i][2]]).strip()))
    t, a, b = E[n + 1]
    assert t == 'tbl', us
    tbl = x[a:b]
    fila = next(r for r in rows(tbl) if cells(r) and txt(cells(r)[0]).strip().startswith('Prototipo'))
    if tiene_imagen(fila):
        print('ya tiene capturas, se salta:', us); continue
    tc = cells(fila)[0]
    proto = next(p for p in PARA_RE.findall(tc) if 'Prototipo' in txt(p))
    ops[n + 1] = tbl.replace(tc, tc.replace(proto, proto + renglones(fotos), 1), 1)
    puestas += len(fotos)
    print(us, len(fotos))

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
print('capturas agregadas:', puestas, '->', SAL)
