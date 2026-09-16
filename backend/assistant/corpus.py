"""US-31 y US-32 — Qué se vectoriza, y con qué granularidad.

El corpus sale del catálogo que ya cargó US-12. No hay texto escrito para el
chatbot: si el asistente contesta algo, es porque está en el catálogo de esa
organización. Eso es lo que hace verificable la respuesta — y lo que hace que
mejorar el asistente sea mejorar el catálogo, no editar un archivo de
*prompts*.

**La granularidad es la decisión importante de este archivo**, y está dicha en
el reparto: «un fragmento por sucursal con su horario completo se recupera
bien; un fragmento con las tres sucursales juntas no distingue cuál pidió el
paciente». La regla general que sale de ahí:

    un fragmento = una cosa sobre la que alguien puede preguntar

Una especialidad es una cosa. Una sucursal con su horario es una cosa. «Las
especialidades de la organización» no lo es: nadie pregunta eso, y el fragmento
que lo contuviera ganaría en toda búsqueda por tener dentro todas las palabras.
"""

from catalog.models import Branch, Practitioner, Specialty

from .models import KnowledgeChunk

# 0 = lunes. Es la convención de `catalog.BranchHours` y de
# `scheduling.Schedule`, documentada sólo en un comentario de esos modelos.
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado",
        "domingo"]


def build(organization, source_types=None) -> list[dict]:
    """Arma los fragmentos del catálogo de una organización.

    Devuelve diccionarios y no filas: quien los guarda es ``embed_catalog``,
    que además tiene que vectorizarlos en lote. Separarlo permite probar el
    corpus sin tocar la base ni el proveedor de embeddings.

    Corre **dentro** del contexto del inquilino; no lo abre él. Es la regla del
    apartado 5 de las convenciones: quien llama decide el contexto, y así un
    comando puede recorrer varias organizaciones sin abrir y cerrar una
    transacción por cada consulta.
    """
    tipos = set(source_types or KnowledgeChunk.Source.values)
    fragmentos: list[dict] = []

    if KnowledgeChunk.Source.SPECIALTY in tipos:
        fragmentos += _specialties(organization)
    if KnowledgeChunk.Source.BRANCH in tipos:
        fragmentos += _branches(organization)
    if KnowledgeChunk.Source.PRACTITIONER in tipos:
        fragmentos += _practitioners(organization)

    return fragmentos


def _specialties(organization) -> list[dict]:
    """Una especialidad, un fragmento. US-31.

    **Sólo las activas.** Una especialidad dada de baja sigue en la tabla
    porque tiene historia asociada, pero sugerirla sería mandar al paciente a
    pedir una ficha que no existe.

    El texto arranca con el nombre repetido en una frase y no sólo como título:
    el vector se calcula sobre el contenido, así que un nombre que aparece una
    sola vez pesa poco frente a una descripción de dos párrafos, y la consulta
    «quiero un cardiólogo» dejaría de encontrar «Cardiología».
    """
    fragmentos = []
    for especialidad in Specialty.objects.filter(
        organization=organization, is_active=True,
    ):
        profesionales = list(
            especialidad.practitioners
            .filter(is_active=True)
            .values_list("first_name", "last_name")
        )
        texto = [
            f"Especialidad: {especialidad.name}.",
            f"En este centro médico, {especialidad.name} atiende lo "
            f"siguiente: {especialidad.description}"
            if especialidad.description
            else f"Este centro médico atiende {especialidad.name}.",
        ]
        if profesionales:
            nombres = ", ".join(f"{n} {a}" for n, a in profesionales)
            texto.append(
                f"Profesionales de {especialidad.name}: {nombres}.",
            )

        fragmentos.append({
            "source_type": KnowledgeChunk.Source.SPECIALTY,
            "source_id": especialidad.id,
            "title": especialidad.name,
            "content": " ".join(texto),
        })
    return fragmentos


def _branches(organization) -> list[dict]:
    """Una sucursal con su horario completo, un fragmento. US-32.

    El horario va **dentro** del mismo fragmento que la sucursal, no en uno
    aparte: «¿a qué hora abre la Sede Norte?» es una sola pregunta, y con el
    horario separado del nombre la recuperación tendría que acertar dos
    fragmentos para contestarla.
    """
    fragmentos = []
    for sucursal in Branch.objects.filter(
        organization=organization, is_active=True,
    ).prefetch_related("hours"):
        texto = [f"Sucursal: {sucursal.name}."]
        if sucursal.address:
            texto.append(f"Dirección de {sucursal.name}: {sucursal.address}.")
        if sucursal.phone:
            texto.append(f"Teléfono de {sucursal.name}: {sucursal.phone}.")

        horarios = _horario(sucursal)
        texto.append(
            f"Horario de atención de {sucursal.name}: {horarios}."
            if horarios
            else f"El horario de {sucursal.name} no está cargado en el "
                 "sistema.",
        )

        fragmentos.append({
            "source_type": KnowledgeChunk.Source.BRANCH,
            "source_id": sucursal.id,
            "title": sucursal.name,
            "content": " ".join(texto),
        })
    return fragmentos


def _horario(sucursal) -> str:
    """«lunes de 08:00 a 12:00 y de 14:00 a 18:00; martes de …».

    Las franjas de un mismo día se juntan en una sola frase por el corte de
    mediodía de US-11: en dos frases separadas, «lunes» aparece dos veces y el
    fragmento se llena de repeticiones que desbalancean el vector.
    """
    por_dia: dict[int, list[str]] = {}
    for franja in sorted(sucursal.hours.all(),
                         key=lambda h: (h.weekday, h.opens_at)):
        por_dia.setdefault(franja.weekday, []).append(
            f"de {franja.opens_at:%H:%M} a {franja.closes_at:%H:%M}",
        )

    return "; ".join(
        f"{DIAS[dia]} {' y '.join(franjas)}"
        for dia, franjas in sorted(por_dia.items())
        if 0 <= dia < len(DIAS)
    )


def _practitioners(organization) -> list[dict]:
    """Un profesional, un fragmento.

    Es lo que contesta «¿quién atiende pediatría en la Sede Norte?» sin tener
    que cruzar dos fragmentos. La matrícula va incluida porque es lo que el
    paciente ve en el comprobante y puede querer verificar.
    """
    fragmentos = []
    for profesional in (
        Practitioner.objects
        .filter(organization=organization, is_active=True)
        .prefetch_related("specialties", "branches")
    ):
        especialidades = [e.name for e in profesional.specialties.all()]
        sucursales = [s.name for s in profesional.branches.all()]

        texto = [f"Profesional: {profesional.full_name}."]
        if especialidades:
            texto.append(
                f"{profesional.full_name} atiende "
                f"{', '.join(especialidades)}.",
            )
        if sucursales:
            texto.append(
                f"{profesional.full_name} atiende en "
                f"{', '.join(sucursales)}.",
            )
        if profesional.license_number:
            texto.append(
                f"Matrícula de {profesional.full_name}: "
                f"{profesional.license_number}.",
            )

        fragmentos.append({
            "source_type": KnowledgeChunk.Source.PRACTITIONER,
            "source_id": profesional.id,
            "title": profesional.full_name,
            "content": " ".join(texto),
        })
    return fragmentos
