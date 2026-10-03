"""Actualiza el capítulo del Sprint 2 con US-32 integrada (PR #47, 02/10/26).

Uso:
    python actualizar_us32.py ENTRADA.docx SALIDA.docx

Es un script de contenido, propio de este documento: cada cambio se ubica por el
texto que ya tiene el Sprint 2 (no por índices) y se detiene si no lo encuentra.
Formato: reusa las tablas y párrafos vecinos (mismo modelo que el resto del sprint).
"""
import sys, html, re
from comun import *

ent, sal = sys.argv[1], sys.argv[2]
x = abrir(ent)
E = elements(x)
L = limites_sprints(x, E)
A, B = L[2]
S = lambda n: x[E[n][1]:E[n][2]]
T = lambda n: html.unescape(txt(S(n))).strip()

def donde(prefijo, tipo='p', desde=A, hasta=B):
    for n in range(desde, hasta):
        if E[n][0] == tipo and (T(n) if tipo == 'p' else html.unescape(txt(S(n)))).startswith(prefijo):
            return n
    sys.exit(f'PARADO: no encontré {prefijo!r} en el Sprint 2.')

def tabla_tras(n_label):
    n = n_label + 1
    assert E[n][0] == 'tbl', n
    return n

def parrafo(n, texto):
    """Mismo pPr del párrafo original; texto nuevo (**negrita**)."""
    s = S(n)
    ppr = re.search(r'<w:pPr>.*?</w:pPr>', s, re.S)
    return f'<w:p>{ppr.group(0) if ppr else BODY_PPR}{runs(texto)}</w:p>'

def con_texto(n, viejo, nuevo):
    t = T(n)
    assert viejo in t, (n, viejo)
    return t.replace(viejo, nuevo)

def fila_set(tbl, clave, col, valor):
    for tr in rows(tbl):
        cs = cells(tr)
        if html.unescape(txt(cs[0])).strip() == clave:
            vals = [None] * len(cs); vals[col] = valor
            return tbl.replace(tr, set_row(tr, vals), 1)
    sys.exit(f'PARADO: no encontré la fila {clave!r}.')

ops = {}
def put(n, xml):
    assert n not in ops, n
    ops[n] = xml

# 1. Sprint Backlog: T-34 completada
nb = donde('IDTarea', 'tbl')
put(nb, fila_set(S(nb), 'T-34', 5, 'Completado'))

# 2. Estado al 02/10/26
ne = donde('Estado al 02/10/26.')
put(ne, parrafo(ne, '**Estado al 02/10/26.** Están integradas en la rama principal cinco historias: '
                    'US-17 y US-20 (PR #45, 16/09), US-31 (PR #41, 16/09), US-34 (PR #46, 30/09) y US-32 '
                    '(PR #47, 02/10). La tarea T-36 tiene terminado el Modelo C4 y los diagramas de lógica de '
                    'negocio de US-31; los diagramas de estado, navegación y tiempo todavía no se hicieron. '
                    'Las demás historias no tienen código en el repositorio a esta fecha.'))

# 3. Tabla de la historia US-32
nt = donde('US-32 — Consultas administrativas al asistente')
ntt = tabla_tras(nt)
d = parse_story(S(ntt))
d['func'] = [f for f in d['func'] if not f.startswith('g)')] + [
    'g) 22 pruebas en tests/test_us32.py; la suite completa del backend queda en 418.',
    'h) Pantalla web /servicios (ABM de servicios) con el botón «Actualizar asistente», que llama a POST /api/assistant/reindex/.']
d['resp'] = ['Web: Luis Mateo Hurtado (backend y pantalla /servicios)',
             'Móvil: reutiliza la pantalla del asistente de US-31']
put(ntt, story_table(S(ntt), d))

# 4. Diseño de datos
nf = donde('Fragmento del catálogo (assistant_catalog_fragments).')
put(nf, parrafo(nf, '**' + 'Fragmento del catálogo (assistant_catalog_fragments).' + '**' +
                 con_texto(nf, 'una especialidad hoy; una sucursal o un servicio cuando entre US-32',
                           'una especialidad, una sede, un servicio o la política de cancelación, '
                           'las tres últimas desde US-32')[len('Fragmento del catálogo (assistant_catalog_fragments).'):]))
no = donde('Organización suma el parámetro')
put(no, S(no) + P('**Servicio (services).** Desde US-32 el catálogo guarda los servicios y estudios de cada '
                  'organización —consulta, estudio o procedimiento— con su precio, opcional (si falta, el '
                  'asistente responde «a consultar»), y la preparación previa. Puede colgar de una especialidad '
                  'de la misma organización, por clave foránea compuesta.'))
nfl = donde('assistant_catalog_fragments —')
nft = tabla_tras(nfl)
put(nft, fila_set(S(nft), 'source_type', 2, 'specialty, branch, service o policy'))
norg = donde('organizations — se agrega')
nbk = donde('backup_records —')
tpl_dd = S(tabla_tras(nbk))
servicios = [
    ['id', 'uuid', 'PK'],
    ['organization_id', 'uuid', 'FK organizations, NOT NULL'],
    ['name', 'varchar(120)', 'Único por organización'],
    ['kind', 'varchar(20)', 'consultation, study o procedure (study por defecto)'],
    ['specialty_id', 'uuid', 'FK compuesta a specialties (id, organization_id); opcional'],
    ['description / preparation', 'text', 'Descripción y preparación previa'],
    ['price', 'numeric(10,2)', 'NULL = «a consultar»; si viene, ≥ 0'],
    ['currency', 'varchar(3)', 'BOB por defecto'],
    ['is_active', 'boolean', 'Baja lógica'],
]
put(norg, P('**services** — servicios y estudios (US-32)')
    + test_style(clone_table(tpl_dd, [(0, None)], servicios, 1)) + EMPTY() + S(norg))
nsc = donde('El script reúne lo que crean las migraciones del sprint')
put(nsc, parrafo(nsc, con_texto(nsc, 'assistant 0001 a 0003', 'assistant 0001 a 0004, catalog 0005 a 0007')))
nais = donde('-- Aislamiento: el mismo bloque para las cuatro tablas')
sql = '''CREATE TABLE "services" (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL REFERENCES organizations (id),
    name varchar(120) NOT NULL,
    kind varchar(20) NOT NULL DEFAULT 'study',
    specialty_id uuid NULL,
    description text NOT NULL DEFAULT '',
    preparation text NOT NULL DEFAULT '',
    price numeric(10,2) NULL,
    currency varchar(3) NOT NULL DEFAULT 'BOB',
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT uq_service_name UNIQUE (organization_id, name),
    CONSTRAINT uq_service_id_org UNIQUE (id, organization_id),
    CONSTRAINT ck_service_price CHECK (price IS NULL OR price >= 0)
);
-- más la FK compuesta (specialty_id, organization_id) a specialties

-- Aislamiento: el mismo bloque para las cinco tablas'''
put(nais, ''.join(CODE(l) for l in sql.split('\n')))

# 5. Componentes y artefactos
ni = donde('Durante el Sprint 2 se incorporaron a la rama principal')
put(ni, parrafo(ni, con_texto(ni, 'y las características generales 5 y 6.',
                              'las características generales 5 y 6 y, con US-32, la tabla de servicios del '
                              'catálogo y la pantalla web /servicios.')))
nc = donde('HistoriaComponentes', 'tbl')
tc = S(nc); rs = rows(tc)
fila32 = set_row(rs[1], ['US-32 — Consultas administrativas',
                         'catalog/models.py (Service), catalog/service_views.py, migraciones catalog 0005 a 0007; '
                         'assistant/corpus.py, reindex_views.py, migración assistant 0004; seed_catalog; '
                         'frontend/src/paginas/Servicios.tsx y api/servicios.ts',
                         'GET y POST /api/catalog/services/, /services/{id}/ y /deactivate/; POST /api/assistant/reindex/. '
                         'El asistente responde horarios, precios, preparación y política de cancelación por el mismo '
                         'POST /api/assistant/suggest/, e indica el tipo en kind.'])
ult = rs[-1]
assert html.unescape(txt(cells(ult)[0])).startswith('US-05, US-09'), txt(ult)[:60]
ult2 = set_row(ult, ['US-05, US-09, US-10, US-18, US-19, US-21, US-22, US-24 y US-25', None, None])
put(nc, tc.replace(ult, fila32 + ult2, 1))

# 6. Plan de pruebas
npi = donde('El plan define entradas, acciones y salidas esperadas')
put(npi, parrafo(npi, con_texto(npi, 'que ya tienen código y la de US-32, que se implementa a continuación.',
                                'que ya tienen código, US-32 incluida.')))
ncov = donde('Caso de usoHistoriaEscenarios', 'tbl')
put(ncov, test_style(fila_set(S(ncov), 'CU33 · Consulta de Información mediante Chatbot', 2, '10')))
ncu = donde('CU33 — Consulta de Información mediante Chatbot')
ninfo = tabla_tras(ncu)
put(ninfo, test_style(fila_set(S(ninfo), 'Historia de usuario', 1, 'US-32 · Móvil y web (/servicios)')))
ncp = donde('IDAcción / escenarioResultado esperadoCP-32-01', 'tbl')
nuevos_cp = [
    ['CP-32-07', 'Preguntar cómo cancelar una ficha', 'Responde con la política de cancelación de US-20, no con una regla inventada.'],
    ['CP-32-08', 'Registrar, editar y dar de baja un servicio desde /servicios', 'Se guarda dentro de la organización; sin permiso, o con precio negativo, se rechaza.'],
    ['CP-32-09', 'Actualizar el asistente desde la web', 'El servicio nuevo llega al asistente; reindexar exige su permiso y no duplica fragmentos.'],
    ['CP-32-10', 'Describir un síntoma en vez de una consulta administrativa', 'Sigue el camino de US-31, sin evidencia administrativa.'],
]
tp = S(ncp)
put(ncp, test_style(clone_table(tp, [(i, None) for i in range(len(rows(tp)))], nuevos_cp, 1)))

# 7. Reporte de pruebas
nev = donde('Evidencia global acreditada:')
put(nev, parrafo(nev, '**Evidencia global acreditada:** según el registro de integración de US-34 (commit 3ee2b84, '
                      '30/09/26), la suite completa del backend terminó con 396 pruebas aprobadas; tras integrar US-32 '
                      '(PR #47, 02/10/26) terminó con 418. Para esta versión del documento la suite no se volvió a ejecutar.'))
nres = donde('CUHistoriaResponsableSituación del reporte', 'tbl')
put(nres, test_style(fila_set(S(nres), 'CU33', 3, 'Integrada (PR #47). 22 pruebas automatizadas; evidencia de interfaz por completar.')))
# bloque de CU33, clonado del de CU35
n35 = donde('Prueba de caso de uso CU35:')
npend = donde('Pendiente: el reporte de CU33')
bloque = list(range(n35, npend))
kinds = [E[k][0] for k in bloque]
assert kinds == ['p', 'tbl', 'p', 'tbl', 'p', 'p', 'p', 'p', 'p', 'p', 'p', 'tbl', 'p'], kinds
pasos = [
    ('CP-32-01', 'Preguntar el horario de una sucursal', 'Responde con el horario de esa sucursal y el fragmento que lo respalda.', True,
     'test_preguntar_el_horario_de_una_sede_devuelve_el_de_esa_sede; test_el_horario_se_agrupa_por_tramos_de_dias_iguales; test_con_gemini_la_consulta_administrativa_usa_su_propio_prompt'),
    ('CP-32-02', 'Preguntar por una sucursal entre varias', 'Se recupera la sucursal pedida y no las otras.', True,
     'test_cada_sede_entra_en_sus_propios_fragmentos_y_cada_uno_se_basta_solo'),
    ('CP-32-03', 'Preguntar el costo o la preparación de un estudio', 'Responde con el servicio correspondiente.', True,
     'test_preguntar_un_precio_devuelve_el_del_servicio; test_preguntar_la_preparacion_devuelve_la_del_estudio; test_el_precio_se_escribe_como_en_bolivia'),
    ('CP-32-04', 'Preguntar algo que no está cargado', 'Responde que no sabe; no inventa.', False, '— (sin prueba específica)'),
    ('CP-32-05', 'Preguntar desde otra organización', 'No se recuperan sucursales ni servicios ajenos.', True,
     'test_lo_administrativo_tampoco_cruza_organizaciones; test_un_servicio_no_puede_colgar_de_la_especialidad_de_otra_organizacion; test_no_se_acepta_la_especialidad_de_otra_organizacion'),
    ('CP-32-06', 'Mencionar una urgencia en una consulta administrativa', 'Igual deriva a emergencia (US-34).', True,
     'test_la_barrera_de_urgencia_va_antes_que_la_pregunta_administrativa; test_con_gemini_la_marca_de_urgencia_tambien_deriva_en_lo_administrativo'),
] + [(c[0], c[1], c[2], True, t) for c, t in zip(nuevos_cp, [
    'test_preguntar_como_cancelar_devuelve_la_politica; test_la_politica_dice_lo_que_hace_us20_y_no_una_regla_inventada',
    'test_el_administrador_registra_edita_y_desactiva_un_servicio; test_sin_permiso_no_se_registran_servicios; test_un_precio_negativo_no_se_guarda; test_la_migracion_le_da_los_permisos_al_administrador_y_lectura_a_recepcion',
    'test_reindexar_desde_la_web_hace_llegar_el_servicio_al_asistente; test_reindexar_exige_su_permiso; test_reindexar_reescribe_y_no_duplica',
    'test_un_sintoma_sigue_el_camino_de_us31_sin_evidencia_administrativa'])]
cub = sum(1 for s in pasos if s[3])
b = [S(k) for k in bloque]
nuevo = (parrafo(bloque[0], 'Prueba de caso de uso CU33: Consulta de Información mediante Chatbot')
         + test_style(clone_table(b[1], [(0, None),
                                         (1, [None, 'CU33 · US-32 · Móvil y web (/servicios)']),
                                         (2, [None, 'El paciente consulta horarios de sucursal, costos, preparación previa a estudios y la política de cancelación por el mismo punto de entrada del asistente.']),
                                         (3, [None, 'Catálogo con sedes con horario y servicios con costo y preparación, indexado con embed_catalog; dos organizaciones para el aislamiento.']),
                                         (4, [None, 'Luis Mateo Hurtado Castro'])], [], 1))
         + b[2]
         + test_style(clone_table(b[3], [(0, None)], [[str(i + 1), s[1], s[2], 'Cubierto por prueba automatizada' if s[3] else 'Pendiente'] for i, s in enumerate(pasos)], 1))
         + b[4] + b[5]
         + parrafo(bloque[6], f'**Resultado general:** {cub} de los {len(pasos)} escenarios están cubiertos por pruebas automatizadas del backend, que pasan dentro de la suite completa (418). CP-32-04 no tiene una prueba específica. Falta la evidencia de interfaz.')
         + parrafo(bloque[7], '**Archivo de pruebas revisado:** backend/tests/test_us32.py. Se identificaron 22 funciones de prueba. Su existencia no se utiliza como sustituto de la evidencia funcional de la interfaz.')
         + b[8] + b[9] + b[10]
         + test_style(clone_table(b[11], [(0, None)], [[s[0], s[4]] for s in pasos], 1))
         + b[12])
put(npend, nuevo + parrafo(npend, '**Pendiente:** el reporte de las historias restantes se agrega cuando cada una se integre a la rama principal.'))

out = aplicar(x, E, ops)
guardar(ent, out, sal)
print('cambios:', len(ops), '->', sal)
