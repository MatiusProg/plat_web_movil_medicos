"""Homogeneiza el formato de los capítulos Sprint 0, 1 y 2 (reglas de ../como-editar-el-word.md).

Uso:
    python normalizar.py ENTRADA.docx SALIDA.docx [--reconstruir 1]

Ubica todo por texto: los títulos "Sprint 0..3" (Titulo11), en cada sprint el tramo de
historias ("Historias de Usuario" o "1.2 Historias de Usuario" hasta "1.3 Contexto del
Sistema") y, si en un sprint las historias aparecen dos veces (el "segundo juego" del
Sprint 1), deja ese segundo juego sin tocar salvo el formato de sus títulos.
--reconstruir: sprints cuyas tablas de historias se rearman sobre el modelo US-01 con su
propio texto (por omisión el 1). En los demás sólo se fija la grilla 4248/4580.
"""
import argparse, re, collections, html, sys
from comun import *

ap = argparse.ArgumentParser()
ap.add_argument('entrada'); ap.add_argument('salida')
ap.add_argument('--reconstruir', type=int, nargs='*', default=[1])
args = ap.parse_args()

x = abrir(args.entrada)
E = elements(x)
S = lambda n: x[E[n][1]:E[n][2]]
T = lambda n: txt(S(n))
kind = lambda n: E[n][0]
has_img = tiene_imagen

SPR = limites_sprints(x, E)
STORY = {}
SECOND_SET = (0, 0)
for sp, (a, b) in SPR.items():
    try:
        h = buscar(x, E, 'Historias de Usuario', 'Titulo3', a, b)
    except SystemExit:
        h = buscar(x, E, '1.2 Historias de Usuario', 'Titulo3', a, b)
    c = buscar(x, E, '1.3 Contexto del Sistema', 'Titulo3', h, b)
    vistos, corte = set(), c
    for n in range(h + 1, c):
        m = re.match(r'^(US-\d+) — ', html.unescape(T(n)).strip()) if kind(n) == 'p' else None
        if m:
            k = 'US-%02d' % int(m.group(1)[3:])
            if k in vistos:
                corte = n; break
            vistos.add(k)
    STORY[sp] = (h + 1, corte)
    if corte != c:
        SECOND_SET = (corte, c)
        print(f'Sprint {sp}: segundo juego de historias en {corte}..{c} (no se tocan sus tablas)')
u01 = buscar(x, E, 'US-01 — Registro de paciente', None, *SPR[0])
assert kind(u01 + 1) == 'tbl'
TPL_US01 = S(u01 + 1)

ops = {}          # índice -> xml nuevo ('' = borrar)
log = collections.Counter()
def put(n, xml, why):
    assert n not in ops, n
    ops[n] = xml; log[why] += 1

# =================================================================
# 1. Historias de usuario
# =================================================================
tpl = TPL_US01                                      # tabla de US-01, Sprint 0
for sp, (a, b) in STORY.items():
    seq = []
    for n in range(a, b):
        if kind(n) == 'tbl':
            seq.append(('tbl', n))
        elif re.match(r'^US-\d+ — ', T(n).strip()):
            seq.append(('title', n))
        else:
            assert not T(n).strip() and not has_img(S(n)) and '<w:sectPr' not in S(n), (n, T(n))
            seq.append(('empty', n))
    out = []
    for i, (k, n) in enumerate(seq):
        if k == 'title':
            out.append(title_par(T(n)))
        elif k == 'tbl':
            if sp in args.reconstruir:       # se reconstruye sobre el modelo
                out.append(story_table(tpl, parse_story(S(n)))); log['historia S1 reconstruida'] += 1
            else:                            # ya tienen el formato; sólo anchos
                out.append(set_widths(S(n), [4248, 4580])); log[f'historia S{sp} anchos'] += 1
            out.append(empty_par())
    put(a, ''.join(out), 'region historias')
    for n in range(a + 1, b):
        put(n, '', 'region historias (borrado tras reconstruir)')
# segundo juego del Sprint 1: sólo el formato y el número del título
for n in range(*SECOND_SET):
    if kind(n) == 'p' and re.match(r'^US-\d+ — ', T(n).strip()):
        put(n, title_par(T(n)), 'titulo segundo juego')

# =================================================================
# 2. Títulos y texto corrido
# =================================================================
RENAME = {'Historias de Usuario': '1.2 Historias de Usuario',
          '2.2.1. Componentes y artefactos generados': '2.2.1 Componentes y artefactos generados',
          '2.3.1. Plan de pruebas (criterios de aceptación)': '2.3.1 Plan de pruebas (criterios de aceptación)',
          '2.3.1. Plan de pruebas (criterios de aceptación - Caja Negra)': '2.3.1 Plan de pruebas (criterios de aceptación - Caja Negra)',
          '2.1.1.4 nivel 4: Diagrama de Código': '2.1.1.4 Nivel 4: Diagrama de Código',
          '2.1.4 Diseño de procesos': '2.1.4 Diseño de procesos'}
S2_PROC = {'Diagrama de análisis de clase': '2.1.4.1 Diagrama de análisis de clase',
           'Diagrama de secuencia': '2.1.4.2 Diagrama de secuencia',
           'Diagrama de estados (solo procesos y transacciones)': '2.1.4.3 Diagrama de estados (solo procesos y transacciones)',
           'Diagrama de tiempo (procesos en general)': '2.1.4.4 Diagrama de tiempo (procesos en general)',
           'Diagrama de navegacion': '2.1.4.5 Diagrama de navegación'}

def set_text(s, new):
    """Pone `new` en el primer run con texto y vacía los demás (títulos de un solo run lógico)."""
    ts = list(re.finditer(r'(<w:t(?:\s[^>]*)?>)([^<]*)(</w:t>)', s))
    first = True
    for m in reversed(ts):
        pass
    out, pos = [], 0
    for i, m in enumerate(ts):
        out.append(s[pos:m.start()])
        out.append(f'<w:t xml:space="preserve">{esc(new)}</w:t>' if i == 0 else '<w:t></w:t>')
        pos = m.end()
    out.append(s[pos:])
    return ''.join(out).replace('<w:br/>', '')

for sp, (a, b) in SPR.items():
    for n in range(a, b):
        if n in ops or kind(n) != 'p':
            continue
        s = S(n)
        m = re.search(r'<w:pStyle w:val="([^"]+)"', s)
        st = m.group(1) if m else None
        if st in ('Titulo2', 'Titulo3', 'Titulo4', 'titulo5'):
            s2 = s
            ppr = re.search(r'<w:pPr>.*?</w:pPr>', s2, re.S).group(0)
            new_style = st
            t = T(n)
            if sp == 2 and t == '2.1.4 Diseño de procesos':
                new_style = 'Titulo4'
            ppr2 = re.sub(r'<w:numPr>.*?</w:numPr>|<w:spacing [^>]*/>|<w:ind [^>]*/>', '', ppr, flags=re.S)
            ppr2 = ppr2.replace(f'<w:pStyle w:val="{st}"/>', f'<w:pStyle w:val="{new_style}"/>'
                                + ('<w:ind w:left="708"/>' if new_style == 'titulo5' else ''))
            s2 = s2.replace(ppr, ppr2, 1).replace('<w:color w:val="auto"/>', '')
            if t in RENAME and RENAME[t] != t:
                s2 = set_text(s2, RENAME[t])
            elif sp == 2 and t in S2_PROC:
                s2 = set_text(s2, S2_PROC[t])
            if s2 != s:
                put(n, s2, 'titulo normalizado')
            continue
        if st is not None or has_img(s) or not T(n).strip():
            continue
        if 'w:fill="121314"' in s:          # bloque de código SQL: ya es homogéneo
            continue
        # texto corrido: interlineado 1,15 (276), sangría de primera línea del estilo (284)
        ppr_m = re.search(r'<w:pPr>.*?</w:pPr>', s, re.S)
        s2 = s
        if ppr_m:
            ppr = ppr_m.group(0)
            ppr2 = re.sub(r'<w:spacing [^>]*/>', '', ppr)
            ppr2 = re.sub(r'<w:ind [^>]*/>', '', ppr2)
            ppr2 = ppr2.replace('<w:pPr>', '<w:pPr><w:spacing w:line="276" w:lineRule="auto"/>', 1) \
                if '<w:numPr>' not in ppr2 else re.sub(r'(</w:numPr>)', r'\1<w:spacing w:line="276" w:lineRule="auto"/>', ppr2, 1)
            s2 = s2.replace(ppr, ppr2, 1)
        else:
            s2 = re.sub(r'^(<w:p[^>]*>)', r'\1<w:pPr><w:spacing w:line="276" w:lineRule="auto"/></w:pPr>', s2, 1)
        s2 = s2.replace('<w:color w:val="auto"/>', '')
        if s2 != s:
            put(n, s2, 'texto corrido normalizado')

# =================================================================
# 3. Tablas
# =================================================================
G_CU = [846, 1843, 1701, 4438]
G_BACKLOG = scale([695, 1764, 1016, 1363, 1497, 1352, 1251], PAGE_W)
G_TEAM = [2263, 3261, 3304]
G_REV = [4413, 4415]
G_RETRO = [2942, 2939, 2940, 7]
G_COMP = [1613, 4919, 2296]
G_SBL = [4414, 4414]
DD_TPL = None
for sp, (a, b) in SPR.items():
    for n in range(a, b):
        if n in ops or kind(n) != 'tbl':
            continue
        if SECOND_SET[0] <= n < SECOND_SET[1]:
            continue
        s = S(n)
        assert not has_img(s), n
        rs = rows(s)
        h = txt(rs[0])
        grid = get_grid(s)
        if h.startswith('IDCaso de Uso'):
            s2 = set_widths(s, G_CU, tblw=PAGE_W); why = 'tabla casos de uso del sprint'
        elif h == 'Sprint Backlog':
            s2 = bold_labels(set_widths(s, G_SBL, tblw=PAGE_W)); why = 'tabla cabecera backlog'
        elif h.startswith('IDTarea'):
            s2 = set_widths(s, G_BACKLOG, tblw=PAGE_W)
            s2 = re.sub(r'<w:rFonts [^>]*w:ascii="(?:system-ui|Calibri)"[^>]*/>', '', s2)
            why = 'tabla sprint backlog'
        elif h.startswith('RolMiembros'):
            s2 = set_widths(s, G_TEAM, tblw=PAGE_W); why = 'tabla equipo scrum'
        elif h.startswith('Daily Scrum'):
            g = DAILY_GRID9 if len(grid) == 9 else scale(grid, DAILY_W)
            s2 = set_widths(s, g, tblw=DAILY_W, ind=DAILY_IND); why = 'tabla daily'
        elif h.startswith('REVISION DE SPRINT'):
            s2 = set_widths(s, G_REV, tblw=PAGE_W); why = 'tabla review'
        elif h.startswith('RETROSPECTIVA'):
            s2 = set_widths(s, G_RETRO, tblw=PAGE_W); why = 'tabla retro'
        elif h.startswith('HistoriaComponentes'):
            s2 = set_widths(s, G_COMP, tblw=PAGE_W); why = 'tabla componentes'
        elif h.startswith('Convención de identificadores'):
            s2 = set_widths(s, [PAGE_W], tblw=PAGE_W); why = 'tabla convención'
        elif h.startswith('ColumnaTipoRestricción'):
            # diseño de datos (Sprint 2): se pasa al estilo de las tablas de pruebas
            if DD_TPL is None:
                DD_TPL = next(S(k) for k in range(*SPR[1]) if kind(k) == 'tbl' and txt(rows(S(k))[0]).startswith('IDAcción'))
            data = [[html.unescape(txt(c)) for c in cells(tr)] for tr in rs[1:]]
            s2 = clone_table(DD_TPL, [(0, ['Columna', 'Tipo', 'Restricción'])], data, 1)
            s2 = test_style(set_widths(s2, scale([2321, 1834, 5109], PAGE_W), tblw=PAGE_W))
            why = 'tabla diseño de datos (a estilo pruebas)'
        elif re.findall(r'w:fill="(\w+)"', rs[0])[:1] == [HDR_TEST]:
            s2 = test_style(set_widths(s, scale(grid, PAGE_W), tblw=PAGE_W)); why = 'tabla de pruebas'
        else:
            print('SIN REGLA', n, h[:60], grid); continue
        if s2 != s:
            put(n, s2, why)

# 3b. sangría 0 en todas las celdas (como las tablas del Sprint 0)
for sp, (a, b) in SPR.items():
    for n in range(a, b):
        if SECOND_SET[0] <= n < SECOND_SET[1]:
            continue
        cur = ops.get(n, S(n))
        if '<w:tbl>' not in cur:
            continue
        new = cell_ind0(cur)
        if new != cur:
            if n in ops: ops[n] = new
            else: ops[n] = new; log['celdas sangría 0 (sin otro cambio)'] += 1

# =================================================================
# aplicar
# =================================================================
guardar(args.entrada, aplicar(x, E, ops), args.salida)
for k, v in sorted(log.items()):
    print(f'{v:4d}  {k}')
