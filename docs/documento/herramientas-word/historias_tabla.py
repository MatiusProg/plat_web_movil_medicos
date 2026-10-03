"""Convierte las historias de usuario escritas como párrafos sueltos en tablas del modelo US-01.

Uso:
    python historias_tabla.py ENTRADA.docx SALIDA.docx [--sprint 2] [--cambios cambios.json]

Tramo: dentro del capítulo "Sprint N", desde el título "Historias de Usuario" (o
"1.2 Historias de Usuario") hasta "1.3 Contexto del Sistema". Cada historia tiene que venir así:

    US-17 — Reserva de ficha médica        <- título (queda encima de la tabla)
    Reserva de ficha por el paciente       <- nombre corto (fila 0)
    CU18 — Reserva de Ficha Médica         <- fila 1, izquierda
    El paciente reserva...                 <- fila 1, derecha
    Prioridad: ALTA / Cant Horas: 16 hr    <- fila 3
    Funcionalidades: + a) b) ...           <- fila 4
    Responsables: + "Web: … · Móvil: …"    <- fila 5 (se parte en líneas por " · ")
    Prototipo (...)                        <- fila 6

El modelo es la tabla que sigue a "US-01 — Registro de paciente" en el Sprint 0.
Si en el tramo hay una imagen, otra tabla o algo que no sea esa estructura, se detiene.
--cambios: JSON {"US-32": {"func": [...], "resp": [...]}} para reemplazar incisos o responsables.
El título del tramo pasa a "1.2 Historias de Usuario", sin numeración automática.
"""
import argparse, html, json, re, sys
from comun import *

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('entrada'); ap.add_argument('salida')
    ap.add_argument('--sprint', type=int, default=2)
    ap.add_argument('--cambios')
    a = ap.parse_args()
    cambios = json.load(open(a.cambios, encoding='utf8')) if a.cambios else {}
    x = abrir(a.entrada); E = elements(x)
    S = lambda n: x[E[n][1]:E[n][2]]
    T = lambda n: html.unescape(txt(S(n))).strip()
    L = limites_sprints(x, E)
    i0, i1 = L[a.sprint]
    try:
        head = buscar(x, E, 'Historias de Usuario', 'Titulo3', i0, i1)
    except SystemExit:
        head = buscar(x, E, '1.2 Historias de Usuario', 'Titulo3', i0, i1)
    fin = buscar(x, E, '1.3 Contexto del Sistema', 'Titulo3', head, i1)
    s0 = limites_sprints(x, E)[0]
    u01 = buscar(x, E, 'US-01 — Registro de paciente', None, *s0)
    tpl = S(u01 + 1); assert E[u01 + 1][0] == 'tbl'
    for n in range(head + 1, fin):
        if E[n][0] != 'p' or tiene_imagen(S(n)):
            sys.exit(f'PARADO: en el tramo hay algo que no es un párrafo de texto (elemento {n}).')
    lines, stories = [T(n) for n in range(head + 1, fin)], []
    for n, t in zip(range(head + 1, fin), lines):
        if re.match(r'^US-\d+ — ', t):
            stories.append({'title': t, 'lines': []})
        elif stories:
            stories[-1]['lines'].append(t)
        elif t:
            sys.exit(f'PARADO: texto antes de la primera historia: {t[:60]!r}')
    out = []
    for st in stories:
        L_ = st['lines']
        rest = [l for l in L_[3:] if l]
        try:
            i_f, i_r = rest.index('Funcionalidades:'), rest.index('Responsables:')
            d = {'short': L_[0], 'cu': L_[1], 'desc': [L_[2]],
                 'prio': next(l for l in rest if l.startswith('Prioridad')),
                 'horas': next(l for l in rest if l.startswith('Cant Horas')),
                 'func': rest[i_f + 1:i_r], 'resp': [rest[i_r + 1]], 'proto': [rest[i_r + 2]]}
            assert len(rest) == i_r + 3
        except (ValueError, StopIteration, AssertionError, IndexError):
            sys.exit(f'PARADO: {st["title"]!r} no tiene la estructura esperada.')
        us = st['title'].split(' — ')[0]
        d.update(cambios.get(us, {}))
        out.append(title_par(st['title']) + story_table(tpl, d) + empty_par())
        print(us, '-', len(d['func']), 'incisos')
    h = S(head)
    h2 = re.sub(r'<w:numPr>.*?</w:numPr>', '', h, count=1, flags=re.S)
    h2 = h2.replace('>Historias de Usuario<', '>1.2 Historias de Usuario<', 1)
    ops = {head: h2, head + 1: ''.join(out)}
    for n in range(head + 2, fin):
        ops[n] = ''
    guardar(a.entrada, aplicar(x, E, ops), a.salida)
    print('historias:', len(stories), '->', a.salida)

if __name__ == '__main__':
    main()
