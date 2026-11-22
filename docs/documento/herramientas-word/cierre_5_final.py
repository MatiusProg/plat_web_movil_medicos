"""Completa el 5 (artefactos finales) y las conclusiones individuales del Word final.

Uso: python cierre_5_final.py ENTRADA.docx SALIDA.docx

- 5.1: quita el aviso «Pendiente», pone la nota de cada miembro en cada sprint,
  agrega la tabla «Descripción de cada nota» y llena la nota final (promedio de
  los cuatro sprints).
- 5.2 y 5.3: actualiza dos frases del Sprint 4 sobre el reentrenamiento, que ya
  quedó programado en producción (PR #134).
- Conclusiones: reemplaza los cinco «[A completar por …]».

Notas de los Sprints 1 a 3: las que sacó cada uno en su revisión. Sprint 4: las
que propuso el equipo, con un promedio de 90, a la espera de la revisión.
"""
import copy
import sys

import docx
from docx.oxml.ns import qn

ENT, SAL = sys.argv[1], sys.argv[2]

KAREN = 'Ortega Mancilla, Karen Paola'
MATEO = 'Hurtado Castro, Luis Mateo'
MIGUEL = 'Aguayo Quiroz, Luis Miguel'
ALEX = 'Osinaga Blanco, Alexander'
DANIEL = 'Iporo Chulque, José Daniel'
MIEMBROS = [KAREN, MATEO, MIGUEL, ALEX, DANIEL]

NOTAS = {
    'Sprint 1': {KAREN: 90, MATEO: 90, MIGUEL: 90, ALEX: 90, DANIEL: 90},
    'Sprint 2': {KAREN: 65, MATEO: 90, MIGUEL: 80, ALEX: 65, DANIEL: 60},
    'Sprint 3': {KAREN: 85, MATEO: 85, MIGUEL: 85, ALEX: 85, DANIEL: 42.5},
    'Sprint 4': {KAREN: 92, MATEO: 95, MIGUEL: 88, ALEX: 90, DANIEL: 85},
}
for s, n in NOTAS.items():
    assert all(v < 100 for v in n.values()), s
assert sum(NOTAS['Sprint 4'].values()) / 5 == 90

DESC = {
    ('Sprint 1', KAREN): 'Entregó US-03 y US-04: recuperación de contraseña y roles y permisos por organización, '
                         'con buena cobertura de los casos de error del enlace de recuperación.',
    ('Sprint 1', MATEO): 'Como Scrum Master organizó el sprint y entregó US-06, US-07 y US-08: la bitácora de '
                         'auditoría, los dependientes desde el móvil y los antecedentes del paciente.',
    ('Sprint 1', MIGUEL): 'Entregó US-13 y US-14: agendas médicas y bloqueos, con el endpoint de disponibilidad '
                          'publicado a tiempo para el resto del equipo.',
    ('Sprint 1', ALEX): 'Como Product Owner priorizó el backlog y entregó el shell de Flutter, US-15 y US-16, '
                        'dentro del tiempo de respuesta exigido (RNF-02).',
    ('Sprint 1', DANIEL): 'Entregó US-11 y US-12: sucursales y catálogo de especialidades y profesionales.',
    ('Sprint 2', KAREN): 'Entregó US-31, US-34 y US-05: la sugerencia de especialidad, la derivación a emergencia '
                         'y la edición del perfil. La evidencia visual y parte de los criterios quedaron para el '
                         'final del sprint.',
    ('Sprint 2', MATEO): 'Como Scrum Master coordinó el sprint y la documentación, y entregó US-32, US-24 y US-25: '
                         'el asistente administrativo, la atención con firma y enmiendas y el historial clínico.',
    ('Sprint 2', MIGUEL): 'Entregó US-17 y US-20: la reserva es estable y está respaldada por pruebas. Faltó '
                          'reforzar los mensajes cuando la ficha ya no se puede modificar.',
    ('Sprint 2', ALEX): 'Como Product Owner entregó US-18, US-19 y US-21. Faltó validar el pago de punta a punta '
                        'con el proveedor y estabilizar el formato del QR, del que dependía el check-in.',
    ('Sprint 2', DANIEL): 'Entregó US-22, US-09 y US-10 con pruebas, pero el check-in quedó sin enlazar al QR '
                          'definitivo y el arrastre del Sprint 1 se cerró tarde.',
    ('Sprint 3', KAREN): 'Como Product Owner priorizó el sprint y entregó US-33: la reserva conversacional, que no '
                         'reserva sin confirmación y pasa primero por la barrera de urgencias.',
    ('Sprint 3', MATEO): 'Entregó US-26 y US-27: la receta respeta la firma también en la base y el paciente la '
                         'descarga en PDF en la web y en el móvil. Llevó además la documentación del sprint.',
    ('Sprint 3', MIGUEL): 'Como Scrum Master siguió la ruta crítica y entregó US-29: los indicadores se calculan '
                          'en la base y coinciden con el panel de inicio.',
    ('Sprint 3', ALEX): 'Entregó US-28 y US-30: las notificaciones se probaron en un teléfono real y los reportes '
                        'dan los mismos números que el panel.',
    ('Sprint 3', DANIEL): 'Entregó US-23 el último día de desarrollo, sin pruebas automatizadas propias de la '
                          'reserva en mostrador.',
    ('Sprint 4', KAREN): 'Como Scrum Master del sprint entregó US-39, US-42, US-48 y US-49: los textos de la IA '
                         'llegan al paciente sólo aprobados por el médico, y la calificación y los recordatorios '
                         'de medicamentos se probaron en el celular contra producción.',
    ('Sprint 4', MATEO): 'Entregó cuatro historias, US-40, US-41, US-47 y US-53, con pruebas de bordes verificadas '
                         'por mutación, más el diagrama de redes, los diagramas del Sprint 4 y la documentación '
                         'del cierre.',
    ('Sprint 4', MIGUEL): 'Entregó US-35 y US-52: el modelo de inasistencia le gana a la línea base y la lista de '
                          'espera ofrece el cupo liberado al siguiente. La puesta en marcha del modelo en '
                          'producción se completó al cierre.',
    ('Sprint 4', ALEX): 'Entregó US-36, US-46 y US-50: el recordatorio reforzado, y los comprobantes y las '
                        'finanzas consultados por voz con la ganancia neta después de los gastos.',
    ('Sprint 4', DANIEL): 'Como Product Owner entregó US-37, US-38 y US-51. La proyección y el reentrenamiento '
                          'funcionan con pocas pruebas automatizadas propias, y el plus de la compra se completó '
                          'al cierre.',
}

CAMBIOS = [
    ('Falta programar el reentrenamiento en producción.',
     'El reentrenamiento quedó programado en producción una vez al día.'),
    ('Las tareas programadas de producción, como el reentrenamiento, quedaron sin configurar.',
     'Las tareas programadas de producción, como el reentrenamiento, se configuraron recién al cierre.'),
    ('Pendiente: las notas se completan con las de cada revisión. Los casos de uso salen del paquete 3.10: '
     'cada historia corresponde a su caso de uso.',
     'Los casos de uso salen del paquete 3.10: cada historia corresponde a su caso de uso. La descripción de '
     'cada nota está en la tabla que sigue.'),
]

CONCLUSIONES = {
    'Karen Paola Ortega Mancilla': [
        'Trabajé sobre todo en lo que el sistema le dice al paciente: la recuperación de contraseña y los roles '
        'del primer sprint, el asistente que sugiere la especialidad y deriva las urgencias, la reserva por '
        'conversación y, en el último sprint, los textos de la IA que el médico valida, la calificación de la '
        'atención y los recordatorios de medicamentos.',
        'Lo que más aprendí es que una IA en salud no puede hablarle sola al paciente: tiene que haber reglas que '
        'corran antes que el modelo y un médico que apruebe lo que se genera. También aprendí a cerrar cada '
        'historia con sus capturas y sus pruebas, porque en el Sprint 2 dejarlas para el final me costó nota. '
        'Como Scrum Master del Sprint 4 vi lo importante que es coordinar a tiempo las dependencias entre '
        'historias.',
    ],
    'Luis Mateo Hurtado Castro': [
        'Me tocó la parte clínica del sistema —los antecedentes, la atención con firma y enmiendas, el historial, '
        'la receta, el chat con el médico y los signos vitales— y la documentación del proyecto, con los '
        'diagramas y el documento de cada sprint, además de ser Scrum Master en los dos primeros sprints.',
        'Aprendí que los datos clínicos se protegen en la propia base de datos, no sólo en la aplicación: la firma, '
        'la inmutabilidad y el aislamiento entre organizaciones se sostienen con restricciones y triggers, y se '
        'prueban intentando romperlos, con pruebas por mutación. También aprendí que coordinar un equipo pide un '
        'reparto escrito y fechas claras, y que la documentación rinde más cuando sale del mismo código que se '
        'entrega.',
    ],
    'Luis Miguel Aguayo Quiroz': [
        'Desarrollé las agendas médicas y sus bloqueos, la reserva y la cancelación de fichas, el panel de '
        'indicadores, el modelo de riesgo de inasistencia y la lista de espera, y fui Scrum Master en el '
        'Sprint 3.',
        'Lo que más me enseñó el proyecto fue el modelo de inasistencia: un modelo sólo sirve si le gana a una '
        'regla simple como «siempre asiste», y para saberlo hay que medirlo con datos que no vio al entrenar. '
        'También aprendí que la inasistencia y la lista de espera son dos caras del mismo problema, porque el '
        'turno que se pierde se puede volver a ocupar. Como Scrum Master aprendí a seguir la ruta crítica para '
        'que nadie quede esperando a otro.',
    ],
    'Alexander Osinaga Blanco': [
        'Me encargué de lo que tiene que ver con el dinero y los avisos: el pago en línea, el comprobante con QR, '
        'la confirmación de asistencia, las notificaciones push y por correo, los reportes, el recordatorio '
        'reforzado, las transacciones por voz del paciente y la contabilidad, además del shell de Flutter y de '
        'ser Product Owner en los dos primeros sprints.',
        'Aprendí que integrar proveedores externos como la pasarela de pago o Firebase exige probar de punta a '
        'punta y que una caída del proveedor no frene al sistema. También aprendí que en las finanzas las cuentas '
        'tienen que cuadrar a mano, y que la voz sólo traduce el pedido: los números salen siempre de la base. '
        'Como Product Owner entendí cuánto pesa priorizar bien el backlog.',
    ],
    'José Daniel Iporo Chulque': [
        'Trabajé en las sucursales y el catálogo, el check-in en recepción, la búsqueda y el registro de '
        'pacientes, la ficha asistida en el mostrador, la proyección de demanda, el reentrenamiento del modelo y '
        'el plus en la compra de la ficha, y fui Product Owner en el Sprint 4.',
        'Este proyecto me dejó claro que una historia no está terminada sin sus pruebas: en el Sprint 3 entregar '
        'el mostrador sin pruebas propias y al último día bajó mi nota, y en el Sprint 4 me esforcé en mejorar. '
        'Aprendí a trabajar sobre módulos que dependen de otros compañeros y a avisar a tiempo el avance. Como '
        'Product Owner vi el sistema completo y entendí cómo cada parte se apoya en las demás.',
    ],
}


def texto(el):
    return ''.join(t.text or '' for t in el.iter(qn('w:t')))


def limpiar(el):
    for e in el.iter():
        for a in list(e.attrib):
            if a.endswith('}paraId') or a.endswith('}textId'):
                del e.attrib[a]
    return el


def poner(p, valor, rpr_de=None):
    """Deja el párrafo con una sola run con ese texto (formato de su primera run, o de rpr_de)."""
    runs = [r for r in p.iter(qn('w:r')) if r.find(qn('w:t')) is not None]
    base = runs[0] if runs else rpr_de
    nueva = p.makeelement(qn('w:r'), {})
    if base is not None and base.find(qn('w:rPr')) is not None:
        nueva.append(copy.deepcopy(base.find(qn('w:rPr'))))
    t = nueva.makeelement(qn('w:t'), {})
    t.text = valor
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    nueva.append(t)
    for hijo in list(p):
        if hijo.tag not in (qn('w:pPr'),):
            p.remove(hijo)
    p.append(nueva)


def celda(tc, valor, rpr_de=None):
    ps = tc.findall(qn('w:p'))
    for extra in ps[1:]:
        tc.remove(extra)
    poner(ps[0], valor, rpr_de)


def num(v):
    return (f'{v:.2f}'.rstrip('0').rstrip('.')).replace('.', ',')


doc = docx.Document(ENT)
body = doc.element.body
els = list(body.iterchildren())
i5 = next(i for i, e in enumerate(els) if texto(e).strip().startswith('5.1 Calificación miembros'))
tablas = [e for e in els[i5:] if e.tag == qn('w:tbl')]
t_notas, t_final = tablas[0], tablas[1]
h_final = next(e for e in els[i5:] if texto(e).strip().startswith('Nota final de cada miembro'))

# 5.1 — nota por sprint
rpr_miembro = None
for tr in t_notas.findall(qn('w:tr'))[1:]:
    tcs = tr.findall(qn('w:tc'))
    sprint, miembro = texto(tcs[0]).strip(), texto(tcs[1]).strip()
    rpr_miembro = next(r for r in tcs[1].iter(qn('w:r')) if r.find(qn('w:t')) is not None)
    celda(tcs[3], num(NOTAS[sprint][miembro]), rpr_miembro)

# 5.1 — tabla «Descripción de cada nota» (la de notas sin Rol, HU, CU ni Tiempo)
t_desc = limpiar(copy.deepcopy(t_notas))
quitar = [2, 5, 6]  # queda Sprint, Miembro, Nota y la de Historia, que pasa a Descripción
grid = t_desc.find(qn('w:tblGrid'))
cols = grid.findall(qn('w:gridCol'))
total_w = sum(int(c.get(qn('w:w'))) for c in cols)
for k in sorted(quitar, reverse=True):
    grid.remove(cols[k])
anchos = [int(total_w * f) for f in (0.13, 0.27, 0.09, 0.51)]
for c, w in zip(grid.findall(qn('w:gridCol')), anchos):
    c.set(qn('w:w'), str(w))
filas = t_desc.findall(qn('w:tr'))
for tr in filas:
    tcs = tr.findall(qn('w:tc'))
    for k in sorted(quitar, reverse=True):
        tr.remove(tcs[k])
    for tc, w in zip(tr.findall(qn('w:tc')), anchos):
        tcw = tc.find(qn('w:tcPr')).find(qn('w:tcW')) if tc.find(qn('w:tcPr')) is not None else None
        if tcw is not None:
            tcw.set(qn('w:w'), str(w))
            tcw.set(qn('w:type'), 'dxa')
celda(filas[0].findall(qn('w:tc'))[3], 'Descripción')
for tr in filas[1:]:
    tcs = tr.findall(qn('w:tc'))
    sprint, miembro = texto(tcs[0]).strip(), texto(tcs[1]).strip()
    celda(tcs[3], DESC[(sprint, miembro)], rpr_miembro)
h_desc = limpiar(copy.deepcopy(h_final))
poner(h_desc, 'Descripción de cada nota:')
blanco = limpiar(copy.deepcopy(h_final.getprevious()))
h_final.addprevious(h_desc)
h_final.addprevious(t_desc)
h_final.addprevious(blanco)

# 5.1 — nota final
for tr in t_final.findall(qn('w:tr'))[1:]:
    tcs = tr.findall(qn('w:tc'))
    miembro = texto(tcs[0]).strip()
    notas = [NOTAS[f'Sprint {k}'][miembro] for k in range(1, 5)]
    rpr = next(r for r in tcs[0].iter(qn('w:r')) if r.find(qn('w:t')) is not None)
    for tc, v in zip(tcs[1:5], notas):
        celda(tc, num(v), rpr)
    celda(tcs[5], num(sum(notas) / 4), rpr)

# 5.2, 5.3 y el aviso del 5.1
hechos = 0
for p in body.iter(qn('w:p')):
    t = texto(p)
    for viejo, nuevo in CAMBIOS:
        if viejo in t:
            poner(p, t.replace(viejo, nuevo))
            hechos += 1
assert hechos >= len(CAMBIOS), hechos  # las del Sprint 4 también están en su revisión y su retrospectiva (capítulo 4)

# Conclusiones individuales
for nombre, parrafos in CONCLUSIONES.items():
    marca = f'[A completar por {nombre}.]'
    p = next(p for p in body.iter(qn('w:p')) if texto(p).strip() == marca)
    poner(p, parrafos[0])
    ancla = p
    for extra in parrafos[1:]:
        q = limpiar(copy.deepcopy(p))
        poner(q, extra)
        ancla.addnext(q)
        ancla = q

doc.save(SAL)
for m in MIEMBROS:
    print(m, [NOTAS[f'Sprint {k}'][m] for k in range(1, 5)], num(sum(NOTAS[f'Sprint {k}'][m] for k in range(1, 5)) / 4))
print('->', SAL)
