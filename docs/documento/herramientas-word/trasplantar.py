"""Lleva tramos ya editados de un .docx a otro, sin reemplazar el documento entero.

Uso:
    python trasplantar.py --base AVANCE.docx --editado COPIA.docx --destino OFICIAL.docx --salida OUT.docx
           [--tramo "texto inicial" "texto final"] ...

Cada tramo va desde el párrafo cuyo texto es exactamente "texto inicial" hasta el
párrafo "texto final" (este último NO se incluye). Por omisión son los dos tramos
que se editaron en la copia:

    2.4.3 Por qué C4 y cómo convive con UML   ->  2.6 Entorno de desarrollo
    Sprint 0 (Titulo11)                        ->  Sprint 3 (Titulo11)

Antes de tocar nada comprueba, tramo por tramo:
  1. que el destino tiene en ese tramo exactamente el mismo contenido que la base
     (texto, tipo de elemento, cantidad de imágenes y sus r:embed). Si un compañero
     editó el tramo en el destino, se detiene: esas ediciones no se pisan.
  2. que cada relación (r:embed, r:id) usada por el tramo editado existe en el
     destino y apunta al mismo archivo, y que ese archivo de word/media es idéntico.
Fuera de los tramos, el destino queda como estaba.
"""
import argparse, collections, re, sys, zipfile, hashlib, html
from comun import abrir, guardar, elements, txt, buscar

DEFAULT = [('2.4.3 Por qué C4 y cómo convive con UML', None, '2.6 Entorno de desarrollo', None),
           ('Sprint 0', 'Titulo11', 'Sprint 3', 'Titulo11')]

def tramo(xml, E, ini, est_ini, fin, est_fin):
    a = buscar(xml, E, ini, est_ini)
    b = buscar(xml, E, fin, est_fin, desde=a + 1)
    return a, b

def firma(xml, E, a, b):
    out = []
    for t, x, y in E[a:b]:
        s = xml[x:y]
        out.append((t, html.unescape(txt(s)), len(re.findall(r'<w:drawing>|<w:pict>', s)),
                    tuple(re.findall(r'r:embed="(\w+)"', s))))
    return out

def rels(path):
    with zipfile.ZipFile(path) as z:
        r = z.read('word/_rels/document.xml.rels').decode('utf8')
        media = {n: hashlib.md5(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('word/media/')}
    d = {}
    for m in re.finditer(r'<Relationship [^>]*>', r):
        s = m.group(0)
        d[re.search(r'Id="([^"]+)"', s).group(1)] = re.search(r'Target="([^"]+)"', s).group(1)
    return d, media

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True, help='documento del que partió la edición (antes de editar)')
    ap.add_argument('--editado', required=True)
    ap.add_argument('--destino', required=True)
    ap.add_argument('--salida', required=True)
    ap.add_argument('--tramo', nargs=2, action='append', metavar=('INICIO', 'FIN'))
    a = ap.parse_args()
    tramos = [(i, None, f, None) for i, f in a.tramo] if a.tramo else DEFAULT

    xb, xe, xd = abrir(a.base), abrir(a.editado), abrir(a.destino)
    Eb, Ee, Ed = elements(xb), elements(xe), elements(xd)
    re_rel, re_media = rels(a.editado)
    de_rel, de_media = rels(a.destino)

    cortes = []
    for ini, ei, fin, ef in tramos:
        bb = tramo(xb, Eb, ini, ei, fin, ef)
        be = tramo(xe, Ee, ini, ei, fin, ef)
        bd = tramo(xd, Ed, ini, ei, fin, ef)
        if firma(xb, Eb, *bb) != firma(xd, Ed, *bd):
            fb, fd = firma(xb, Eb, *bb), firma(xd, Ed, *bd)
            dif = next((i for i, (u, v) in enumerate(zip(fb, fd)) if u != v), min(len(fb), len(fd)))
            sys.exit(f'PARADO: el tramo {ini!r} del destino no coincide con la base '
                     f'(elemento {dif} del tramo: {fb[dif][1][:80] if dif < len(fb) else "-"!r} / '
                     f'{fd[dif][1][:80] if dif < len(fd) else "-"!r}). Hay ediciones que no están en la base.')
        frag = xe[Ee[be[0]][1]:Ee[be[1] - 1][2]]
        # Word renumera los rId al guardar: se traduce cada rId del editado al rId del
        # destino que apunta a un archivo de word/media con el mismo contenido (md5).
        por_hash = {}
        for rid_d, tgt_d in de_rel.items():
            h = de_media.get('word/' + tgt_d)
            if h:
                por_hash.setdefault(h, rid_d)
        mapa = {}
        for rid in sorted(set(re.findall(r'r:(?:embed|id|link)="(\w+)"', frag))):
            tgt = re_rel.get(rid)
            h = re_media.get('word/' + tgt) if tgt else None
            if h is None or h not in por_hash:
                sys.exit(f'PARADO: la relación {rid} ({tgt}) del tramo {ini!r} no tiene un archivo '
                         'idéntico en el destino. Las imágenes no se agregan ni se recomprimen.')
            mapa[rid] = por_hash[h]
        frag = re.sub(r'(r:(?:embed|id|link)=")(\w+)(")', lambda m: m.group(1) + mapa[m.group(2)] + m.group(3), frag)
        cambiados = {k: v for k, v in mapa.items() if k != v}
        if cambiados:
            print(f'  {len(cambiados)} rId traducidos al numerado del destino')
        cortes.append((Ed[bd[0]][1], Ed[bd[1] - 1][2], frag, ini, bd, be))

    # Los dibujos tienen que quedar con el XML exacto del destino: Word, al guardar la
    # copia, renumera docPr id y wp14:anchorId/editId. Se vuelve al XML del destino
    # buscando el dibujo que usa la misma imagen (mismo r:embed ya traducido).
    dib_d = re.findall(r'<w:drawing>.*?</w:drawing>|<w:pict>.*?</w:pict>', xd, re.S)
    por_emb = {}
    for d in dib_d:
        por_emb.setdefault(tuple(re.findall(r'r:(?:embed|id)="(\w+)"', d)), []).append(d)
    def restaurar(m):
        d = m.group(0)
        if d in dib_d:
            return d
        c = por_emb.get(tuple(re.findall(r'r:(?:embed|id)="(\w+)"', d)), [])
        if len(c) != 1:
            sys.exit('PARADO: no pude identificar sin ambigüedad el dibujo original de una imagen del tramo.')
        return c[0]
    # Marcadores: los w:id de bookmarkStart/End del tramo pueden chocar con los del resto.
    usados = set()
    pos = 0
    for x0, x1, *_ in sorted(cortes):
        usados |= set(re.findall(r'<w:bookmark(?:Start|End) [^>]*w:id="(\d+)"', xd[pos:x0]))
        pos = x1
    usados |= set(re.findall(r'<w:bookmark(?:Start|End) [^>]*w:id="(\d+)"', xd[pos:]))
    contador = [max([int(u) for u in usados] + [0])]
    nuevos = []
    for x0, x1, frag, ini, bd, be in cortes:
        frag = re.sub(r'<w:drawing>.*?</w:drawing>|<w:pict>.*?</w:pict>', restaurar, frag, flags=re.S)
        mapa_bm = {}            # el mismo id viejo -> el mismo id nuevo (Start y End quedan pareados)
        def renum(m):
            if m.group(2) not in mapa_bm:
                contador[0] += 1
                mapa_bm[m.group(2)] = str(contador[0])
            return m.group(1) + mapa_bm[m.group(2)] + m.group(3)
        frag = re.sub(r'(<w:bookmark(?:Start|End) [^>]*?w:id=")(\d+)(")', renum, frag)
        nuevos.append((x0, x1, frag, ini, bd, be))
    cortes = nuevos

    # El índice (TOC) del destino apunta a marcadores _Toc de sus títulos. Los títulos del
    # tramo editado traen los marcadores de la copia, con otros nombres: se les ponen los del
    # destino, emparejando título con título por su texto (sin la numeración ni tildes, y en
    # orden cuando el texto se repite entre sprints).
    import unicodedata
    def clave(t):
        t = unicodedata.normalize('NFKD', html.unescape(t)).encode('ascii', 'ignore').decode().lower().strip()
        return re.sub(r'^[\d.\s]+', '', t).rstrip('. ')
    fuera = xd
    for x0, x1, *_ in sorted(cortes, reverse=True):
        fuera = fuera[:x0] + fuera[x1:]
    referidos = set(re.findall(r'PAGEREF (_\w+)|w:anchor="(_\w+)"|REF (_\w+)', fuera))
    referidos = {n for tup in referidos for n in tup if n}
    BM = re.compile(r'<w:bookmarkStart [^>]*w:name="([^"]+)"[^>]*/>')
    nuevos = []
    for x0, x1, frag, ini, bd, be in cortes:
        # títulos del destino (en el tramo) con marcadores referidos
        quedan = collections.defaultdict(list)
        for t, a0, b0 in Ed[bd[0]:bd[1]]:
            s = xd[a0:b0]
            nombres = [n for n in BM.findall(s) if n in referidos]
            if nombres:
                quedan[clave(txt(s))].append(nombres)
        Ef = elements('<w:body>' + frag + '</w:body>')
        piezas, pos = [], 0
        for t, a0, b0 in Ef:
            a0 -= 8; b0 -= 8
            s = frag[a0:b0]
            if t == 'p' and re.search(r'<w:pStyle w:val="(?i:titulo|capitulo)', s):
                k = clave(txt(s))
                if quedan.get(k):
                    nombres = quedan[k].pop(0)
                    s = re.sub(r'<w:bookmark(?:Start|End) [^>]*/>', '', s)
                    ini_bm = fin_bm = ''
                    for nm in nombres:
                        contador[0] += 1
                        ini_bm += f'<w:bookmarkStart w:id="{contador[0]}" w:name="{nm}"/>'
                        fin_bm += f'<w:bookmarkEnd w:id="{contador[0]}"/>'
                    s = re.sub(r'(</w:pPr>|<w:p(?: [^>]*)?>(?!.*</w:pPr>))', lambda m: m.group(1) + ini_bm, s, count=1, flags=re.S)
                    s = s[:s.rfind('</w:p>')] + fin_bm + '</w:p>'
            piezas.append(frag[pos:a0] + s)
            pos = b0
        piezas.append(frag[pos:])
        frag = ''.join(piezas)
        perdidos = [(k, v) for k, v in quedan.items() if v]
        if perdidos:
            sys.exit(f'PARADO: títulos del índice sin pareja en el tramo {ini!r}: {perdidos[:5]}')
        nuevos.append((x0, x1, frag, ini, bd, be))
    cortes = nuevos

    out = xd
    for x0, x1, frag, ini, bd, be in sorted(cortes, reverse=True):
        out = out[:x0] + frag + out[x1:]
        print(f'tramo {ini!r}: destino {bd[0]}..{bd[1]} ({bd[1]-bd[0]} elementos) -> editado {be[1]-be[0]} elementos')
    guardar(a.destino, out, a.salida)
    print('escrito', a.salida)

if __name__ == '__main__':
    main()
