"""Segunda tanda de correcciones de la copia final (22/11/26), pedidas por Luis.

Uso:  python completar_final_sprint4_b.py ENTRADA.docx SALIDA.docx BASE.docx DAILY.json NAV.txt SQL.sql

ENTRADA es la v2 (salida de completar_final_sprint4.py); BASE, el maestro completo, del que se
copia el formato del script SQL del Sprint 3. DAILY.json trae el Daily del Sprint 4 día por día;
NAV.txt, los títulos de los diagramas de navegación (uno por línea); SQL.sql, el script físico.

1. 2.1.1 del Sprint 4: vuelve el Modelo C4 con sus cuatro niveles; salen capas y despliegue; el
   diagrama de redes queda como 2.1.1.5.
2. 2.1.4.5: un subtítulo por diagrama de navegación.
3. Roles del Sprint 4: Product Owner José Daniel Iporo Chulque, Scrum Master Karen Paola Ortega
   Mancilla y el resto Developers (1.5 Equipo Scrum, Review, Retrospective y 5.1).
4. Daily Scrum del Sprint 4: del martes 10/11 al domingo 22/11, en dos semanas, con el formato del
   Sprint 3 (sus tablas se usan de modelo).
5. 2.1.2.3 Diseño Físico (Script) del Sprint 4, con el formato del Sprint 3.
"""
import sys, re, html, json
from comun import (abrir, guardar, elements, txt, rows, cells, set_row, esc, strip_ids,
                   buscar, aplicar, tiene_imagen)

ENT, SAL, BASE, DAILY, NAV, SQL = sys.argv[1:7]
x = abrir(ENT)
E = elements(x)
xb = abrir(BASE)
Eb = elements(xb)


def T(xml, Es, i):
    return html.unescape(txt(xml[Es[i][1]:Es[i][2]])).strip()


def clonar(par, texto):
    ppr = re.search(r'<w:pPr>.*?</w:pPr>', par, re.S)
    ppr = ppr.group(0) if ppr else ''
    rpr = re.search(r'<w:r(?:\s[^>]*)?>\s*(<w:rPr>.*?</w:rPr>)', par, re.S)
    rpr = rpr.group(1) if rpr else ''
    if not texto:
        return f'<w:p>{ppr}</w:p>'
    return f'<w:p>{ppr}<w:r>{rpr}<w:t xml:space="preserve">{esc(texto)}</w:t></w:r></w:p>'


def tabla_desde(i, Es=None):
    Es = Es or E
    j = i + 1
    while Es[j][0] != 'tbl':
        j += 1
    return j


ops = {}
s4 = buscar(x, E, 'Sprint 4', 'Titulo11')

# ---------- 1. Arquitectura: Modelo C4 ---------------------------------------------------------
ic = buscar(x, E, '2.1.1.1 Diagrama de capas', desde=s4)
idp = buscar(x, E, '2.1.1.2 Diagrama de despliegue', desde=s4)
ir = buscar(x, E, '2.1.1.3 Diagrama de Redes', desde=s4)
assert ic < idp < ir, 'PARADO: arquitectura'
for k in range(ic + 1, ir):
    assert not tiene_imagen(x[E[k][1]:E[k][2]]), 'PARADO: capas/despliegue tienen imagen'
tit = x[E[ic][1]:E[ic][2]]
vacio = x[E[ic + 1][1]:E[ic + 1][2]]
C4 = ['2.1.1.1 Modelo C4 – Nivel 1: Diagrama de contexto',
      '2.1.1.2 Modelo C4 – Nivel 2: Diagrama de contenedores',
      '2.1.1.3 Modelo C4 – Nivel 3: Diagrama de componentes',
      '2.1.1.4 Modelo C4 – Nivel 4: Diagrama de código']
ops[ic] = ''.join(clonar(tit, t) + vacio for t in C4)
for k in range(ic + 1, ir):
    ops[k] = ''
ops[ir] = clonar(x[E[ir][1]:E[ir][2]], '2.1.1.5 Diagrama de Redes')

# ---------- 2. Navegación: un subtítulo por diagrama ------------------------------------------
inav = buscar(x, E, '2.1.4.5 Diagrama de navegación', desde=s4)
isis = buscar(x, E, 'Sistema', desde=inav)
sub = x[E[isis][1]:E[isis][2]]
vac = x[E[isis + 1][1]:E[isis + 1][2]]
nav = [l.strip() for l in open(NAV, encoding='utf-8') if l.strip()]
ops[isis] = ''.join(clonar(sub, t) + vac for t in nav)
ops[isis + 1] = ''

# ---------- 3. Roles del Sprint 4 --------------------------------------------------------------
ieq = tabla_desde(buscar(x, E, '1.5 Equipo Scrum', desde=s4))
tbl = x[E[ieq][1]:E[ieq][2]]
nuevo = tbl
for tr in rows(tbl):
    rol = html.unescape(txt(cells(tr)[0])).strip()
    if rol == 'PRODUCT OWNER':
        nuevo = nuevo.replace(tr, set_row(tr, [None, 'Iporo Chulque, José Daniel']), 1)
    elif rol == 'SCRUM MASTER':
        nuevo = nuevo.replace(tr, set_row(tr, [None, 'Ortega Mancilla, Karen Paola']), 1)
    elif rol.startswith('TEAM'):
        nuevo = nuevo.replace(tr, set_row(tr, [None, 'Aguayo Quiroz, Luis Miguel\nHurtado Castro, Luis Mateo\nOsinaga Blanco, Alexander']), 1)
ops[ieq] = strip_ids(nuevo)

ROL4 = {'Osinaga Blanco Alexander': 'Developer', 'Hurtado Castro Luis Mateo': 'Developer',
        'Ortega Mancilla Karen Paola': 'Scrum Master', 'Iporo Chulque José Daniel': 'Product Owner',
        'Aguayo Quiroz Luis Miguel': 'Developer'}
irv = tabla_desde(buscar(x, E, '4. Sprint Review', desde=s4))
tbl = x[E[irv][1]:E[irv][2]]
nuevo = tbl
for tr in rows(tbl):
    cs = [html.unescape(txt(c)).strip() for c in cells(tr)]
    if len(cs) == 2 and cs[0] in ROL4:
        nuevo = nuevo.replace(tr, set_row(tr, [None, ROL4[cs[0]]]), 1)
ops[irv] = strip_ids(nuevo)

irt = tabla_desde(buscar(x, E, '5. Sprint Retrospective', desde=s4))
tbl = x[E[irt][1]:E[irt][2]]
nuevo = tbl
for tr in rows(tbl):
    if html.unescape(txt(tr)).startswith('FACILITADOR'):
        nuevo = nuevo.replace(tr, set_row(tr, [None, 'KAREN PAOLA ORTEGA MANCILLA']), 1)
ops[irt] = strip_ids(nuevo)

ROL51 = {'Ortega Mancilla, Karen Paola': 'Scrum Master', 'Hurtado Castro, Luis Mateo': 'Developer',
         'Aguayo Quiroz, Luis Miguel': 'Developer', 'Osinaga Blanco, Alexander': 'Developer',
         'Iporo Chulque, José Daniel': 'Product Owner'}
i51 = tabla_desde(buscar(x, E, '5.1 Calificación miembros de equipo SCRUM'))
tbl = x[E[i51][1]:E[i51][2]]
nuevo = tbl
for tr in rows(tbl):
    cs = [html.unescape(txt(c)).strip() for c in cells(tr)]
    if cs[0] == 'Sprint 4' and cs[1] in ROL51:
        nuevo = nuevo.replace(tr, set_row(tr, [None, None, ROL51[cs[1]]]), 1)
ops[i51] = strip_ids(nuevo)

# ---------- 4. Daily Scrum del Sprint 4 --------------------------------------------------------
s3 = buscar(x, E, 'Sprint 3', 'Titulo11')
d3 = buscar(x, E, '3. Daily Scrum', desde=s3)
modelo = x[E[tabla_desde(d3)][1]:E[tabla_desde(d3)][2]]     # semana 1 del Sprint 3: 7 días
assert 'Semana 1' in txt(modelo) and len(rows(modelo)) == 18, 'PARADO: modelo del Daily'
daily = json.load(open(DAILY, encoding='utf-8'))
DIAS = {1: 'Lun', 2: 'Mar', 3: 'Mie', 4: 'Jue', 5: 'Vie', 6: 'Sáb', 0: 'Dom'}
import datetime as dt


def etiqueta(d):
    f = dt.date.fromisoformat(d)
    return f'{DIAS[f.isoweekday() % 7]}{f.day} – nov.'


ORDEN = ['ALEXANDER OSINAGA BLANCO', 'LUIS MATEO HURTADO CASTRO', 'JOSÉ DANIEL IPORO CHULQUE',
         'KAREN PAOLA ORTEGA MANCILLA', 'LUIS MIGUEL AGUAYO QUIROZ']
semanas = [('Semana 1', '10 noviembre – 16 noviembre', daily['dias'][:7]),
           ('Semana 2', '17 noviembre – 22 noviembre', daily['dias'][7:])]


def semana(nombre, rango, dias):
    rs = rows(modelo)
    pre = modelo[:modelo.find(rs[0])]
    post = modelo[modelo.rfind(rs[-1]) + len(rs[-1]):]
    out = [rs[0]]
    tit = rs[1]
    tc = cells(tit)
    out.append(set_row(tit, [nombre + '\n' + rango] + [None] * (len(tc) - 1)))
    cab = [None, None] + [etiqueta(d) for d in dias] + [''] * (7 - len(dias))
    out.append(set_row(rs[2], cab))
    for k, persona in enumerate(ORDEN):
        for q in range(3):
            tr = rs[3 + k * 3 + q]
            vals = [daily['personas'][persona][d][q] for d in dias] + [''] * (7 - len(dias))
            primera = [persona] if q == 0 else [None]
            out.append(set_row(tr, primera + [None] + vals))
    return strip_ids(pre + ''.join(out) + post)


d4 = buscar(x, E, '3. Daily Scrum', desde=s4)
r4 = buscar(x, E, '4. Sprint Review', desde=d4)
sep = '<w:p/>'
ops[d4 + 1] = semana(*semanas[0]) + sep + semana(*semanas[1])
for k in range(d4 + 2, r4):
    assert not tiene_imagen(x[E[k][1]:E[k][2]]), 'PARADO: el Daily del Sprint 4 tiene una imagen'
    ops[k] = ''

# ---------- 5. 2.1.2.3 Diseño Físico (Script) --------------------------------------------------
s3b = buscar(xb, Eb, 'Sprint 3', 'Titulo11')
f3 = buscar(xb, Eb, '2.1.2.3 Diseño Físico (Script)', desde=s3b)
intro = xb[Eb[f3 + 1][1]:Eb[f3 + 1][2]]
p_vacio = xb[Eb[f3 + 4][1]:Eb[f3 + 4][2]]
p_coment = xb[Eb[f3 + 5][1]:Eb[f3 + 5][2]]
p_codigo = xb[Eb[f3 + 9][1]:Eb[f3 + 9][2]]
assert T(xb, Eb, f3 + 9).startswith('CREATE TABLE') and T(xb, Eb, f3 + 5).startswith('--'), 'PARADO: modelo del script SQL'
lineas = open(SQL, encoding='utf-8').read().split('\n')
cuerpo = []
for l in lineas:
    if not l.strip():
        cuerpo.append(clonar(p_vacio, ''))
    elif l.lstrip().startswith('--'):
        cuerpo.append(clonar(p_coment, l))
    else:
        cuerpo.append(clonar(p_codigo, l))
f4 = buscar(x, E, '2.1.2.3 Diseño Físico (Script)', desde=s4)
ops[f4 + 1] = (clonar(intro, 'El script reúne lo que crean las migraciones del sprint: ai 0001 y 0002, '
                      'noshow 0001 y 0002, messaging 0001 y 0002, appointments 0007 a 0010, encounters 0007 a 0013, '
                      'catalog 0008, reporting 0004 y tenancy 0007 y 0008. Son doce tablas nuevas y dos columnas en '
                      'tablas que ya existían; cada tabla lleva su organización, RLS y una FK compuesta para no '
                      'colgar de otra organización.')
               + clonar(p_vacio, '') + ''.join(cuerpo))

out = aplicar(x, E, ops)
assert len(re.findall(r'<w:drawing>', out)) == len(re.findall(r'<w:drawing>', x)), 'PARADO: cambió una imagen'
guardar(ENT, out, SAL)
print('Listo:', SAL)
print(f'  C4 en 2.1.1; {len(nav)} subtítulos de navegación; roles del Sprint 4; Daily 10–22/11; '
      f'script SQL de {len(lineas)} líneas')
