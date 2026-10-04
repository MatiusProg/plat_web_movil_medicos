"""Mueve las capturas del segundo juego de historias del Sprint 1 al primero y borra el segundo.

Uso:
    python mover_capturas.py ENTRADA.docx SALIDA.docx

Las imágenes se mueven como párrafo completo (<w:p> con su <w:drawing>), sin tocar
el XML del dibujo: r:embed, tamaño y docPr quedan iguales. word/media y los .rels no se tocan.
Ubica los dos juegos por texto dentro del capítulo "Sprint 1": los títulos "US-NN — …"
entre "1.2 Historias de Usuario" y "1.3 Contexto del Sistema"; tienen que ser 28 (dos veces
las mismas 14 historias, en el mismo orden). Si no, se detiene.
"""
import re, sys, collections
from comun import *

ent, sal = sys.argv[1], sys.argv[2]
x = abrir(ent)
E = elements(x)
T = lambda n: txt(x[E[n][1]:E[n][2]]).strip()
S = lambda n: x[E[n][1]:E[n][2]]
US = lambda n: re.match(r'^(US-\d+) — ', T(n)).group(1)
a1, b1 = limites_sprints(x, E)[1]
h = buscar(x, E, '1.2 Historias de Usuario', 'Titulo3', a1, b1)
c = buscar(x, E, '1.3 Contexto del Sistema', 'Titulo3', h, b1)

# --- los dos juegos, verificados por texto ---
titles = [i for i in range(h, c) if E[i][0] == 'p' and re.match(r'^US-\d+ — ', T(i))]
if len(titles) != 28:
    sys.exit(f'PARADO: esperaba 28 títulos de historia en el Sprint 1 y hay {len(titles)}.')
first, second = titles[:14], titles[14:]
assert [US(i) for i in first] == [US(i) for i in second]
assert all(E[i + 1][0] == 'tbl' for i in titles)
END = second[-1] + 2                     # párrafo vacío tras la última tabla del segundo juego
assert T(END + 1) == '1.3 Contexto del Sistema' and not T(END), T(END + 1)
DEL = range(second[0], END + 1)          # títulos, tablas y vacíos del segundo juego
for n in DEL:
    s = S(n)
    if E[n][0] == 'p':
        assert '<w:drawing' not in s and '<w:pict' not in s
        assert n in second or not T(n), (n, T(n))
# ninguna otra relación (r:id / r:embed) vive en lo que se borra, salvo los dibujos que se mueven
seg = x[E[DEL[0]][1]:E[DEL[-1]][2]]
emb = re.findall(r'r:embed="(\w+)"', seg)
assert len(re.findall(r'r:(?:id|embed|link|pict)="', seg)) == len(emb), 'hay otras relaciones en el segundo juego'

RESP = {
    'US-03': {'replace': {'Web:': ['Web: Karen Ortega', 'Móvil: Karen Ortega']}},
    'US-05': {'add': ['No se desarrolló en el Sprint 1 (era de Michael Mamani, que retiró la materia); pasa al Sprint 2.']},
    'US-09': {'add': ['No se desarrolló en el Sprint 1 (era de Michael Mamani, que retiró la materia); pasa al Sprint 2.']},
    'US-10': {'add': ['No se desarrolló en el Sprint 1 (era de Michael Mamani, que retiró la materia); pasa al Sprint 2.']},
}

def cell_paras(tc):
    return PARA_RE.findall(tc)

def set_cell_paras(tc, paras):
    pr = re.search(r'<w:tcPr>.*?</w:tcPr>', tc, re.S)
    return '<w:tc>' + (pr.group(0) if pr else '') + ''.join(paras) + '</w:tc>'

ops = {}
moved = collections.OrderedDict()
for f, s2 in zip(first, second):
    us = US(f)
    tbl = S(f + 1)
    rs = rows(tbl)
    # 1) imágenes del segundo juego, en orden de fila
    pics = []
    for tr in rows(S(s2 + 1)):
        for tc in cells(tr):
            for pp in cell_paras(tc):
                if '<w:drawing' in pp or '<w:pict' in pp:
                    pics.append(pp)
    # 2) fila Prototipo (6): texto + imágenes + un vacío
    if pics:
        tc6 = cells(rs[6])[0]
        ps = cell_paras(tc6)
        texto = [q for q in ps if txt(q).strip()]
        vacio = [q for q in ps if not txt(q).strip()][:1]
        new6 = rs[6].replace(tc6, set_cell_paras(tc6, texto + pics + vacio), 1)
        tbl = tbl.replace(rs[6], new6, 1)
        moved[us] = [e for q in pics for e in re.findall(r'r:embed="(\w+)"', q)]
    # 3) responsables (fila 5)
    if us in RESP:
        rs = rows(tbl)
        tc5 = cells(rs[5])[0]
        ps = cell_paras(tc5)
        out = []
        for q in ps:
            t = txt(q).strip()
            rep = RESP[us].get('replace', {})
            if t in rep:
                out += [p(r(v)) for v in rep[t]]
            else:
                out.append(q)
        out += [p(r(v)) for v in RESP[us].get('add', [])]
        tbl = tbl.replace(rs[5], rs[5].replace(tc5, set_cell_paras(tc5, out), 1), 1)
    if tbl != S(f + 1):
        ops[f + 1] = tbl

for n in DEL:
    ops[n] = ''

guardar(ent, aplicar(x, E, ops), sal)
for k, v in moved.items():
    print(k, v)
print('elementos borrados:', len(DEL), '->', sal)
