"""US-32 — El corpus administrativo: sedes, servicios y políticas.

US-31 vectoriza **qué atiende** cada especialidad. Esto vectoriza **dónde,
cuándo, cuánto y cómo**: la dirección y el horario de cada sede, quién atiende
en ella, el precio y la preparación de cada servicio, y la política de
cancelación. Va a la misma tabla y al mismo índice que las especialidades, y
lo contesta el mismo endpoint: una sola búsqueda decide si la pregunta es
clínica o administrativa (ver ``views.py``).

El trabajo de esta historia no es el endpoint, es **el texto**. Tres reglas,
las mismas de ``indexing.py`` llevadas a otra clase de dato:

1. **Un fragmento por sede, nunca las tres juntas.** "¿A qué hora abre la
   Sede Norte?" tiene que recuperar el horario de la Norte. Con un solo
   fragmento para las tres el vector queda en el medio, y la respuesta tiene
   que adivinar cuál de los tres horarios era el pedido.

2. **Y dentro de la sede, un fragmento por pregunta.** Dirección, horario y
   quién atiende se preguntan por separado y se parecen a cosas distintas.

3. **Todo fragmento se basta a sí mismo.** Cada uno empieza con el nombre de
   la sede o del servicio. "De 08:00 a 12:00" recuperado solo no dice de
   dónde es, ni al modelo ni al paciente que lo ve como respaldo.

El texto se arma con las palabras que usa quien pregunta —"queda en",
"abre", "cuesta", "tengo que ir en ayunas"— y no con el nombre de la columna.
Con el proveedor local, que compara palabras, eso es lo que hace que
funcione; con Gemini no estorba.

Todo sale de la base: acá no hay ni un dato escrito a mano. Si la sede
cambia de horario, reindexar es volver a correr ``embed_catalog``.
"""

from collections import defaultdict
from decimal import Decimal

from catalog.models import (
    Branch,
    BranchHours,
    PractitionerBranch,
    PractitionerSpecialty,
    Service,
)

from .models import SourceType

WEEKDAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado",
            "domingo"]

CURRENCY_LABELS = {"BOB": "Bs", "USD": "USD"}


# --------------------------------------------------------------------------
#  Sedes
# --------------------------------------------------------------------------

def _hhmm(value) -> str:
    return value.strftime("%H:%M")


def _join(items: list[str]) -> str:
    """'a', 'a y b', 'a, b y c'."""
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " y " + items[-1]


def describe_hours(hours) -> str:
    """El horario semanal en una frase, agrupando los días iguales.

    Cinco días con el mismo horario se dicen "de lunes a viernes", no cinco
    veces: además de leerse mejor, es lo que pregunta la gente ("¿abren los
    sábados?") y la frase tiene que contener esa palabra para parecerse.
    """
    by_day = defaultdict(list)
    for franja in hours:
        by_day[franja.weekday].append((franja.opens_at, franja.closes_at))

    # Días consecutivos con exactamente las mismas franjas forman un tramo.
    tramos = []  # (primer día, último día, franjas)
    for day in range(7):
        franjas = tuple(sorted(by_day.get(day, [])))
        if tramos and tramos[-1][2] == franjas and tramos[-1][1] == day - 1:
            tramos[-1] = (tramos[-1][0], day, franjas)
        else:
            tramos.append((day, day, franjas))

    partes = []
    for first, last, franjas in tramos:
        if first == last:
            dias = f"el {WEEKDAYS[first]}"
        elif last == first + 1:
            dias = f"{WEEKDAYS[first]} y {WEEKDAYS[last]}"
        else:
            dias = f"de {WEEKDAYS[first]} a {WEEKDAYS[last]}"
        if franjas:
            horario = _join([f"de {_hhmm(a)} a {_hhmm(c)}" for a, c in franjas])
            partes.append(f"{dias} abre {horario}")
        else:
            partes.append(f"{dias} no abre, está cerrada")
    texto = "; ".join(partes)
    return texto[0].upper() + texto[1:]


def branch_fragments(branch, hours, staff) -> list[str]:
    """Los fragmentos de una sede.

    ``staff`` es la lista de ``(nombre del profesional, [especialidades])``
    que atienden en ella.
    """
    name = branch.name.strip()
    fragments = []

    contacto = [f"Sucursal: {name}."]
    if branch.address:
        contacto.append(f"Dirección: queda en {branch.address.strip()}.")
    if branch.phone:
        contacto.append(f"Teléfono de contacto: {branch.phone.strip()}.")
    fragments.append(" ".join(contacto))

    if hours:
        fragments.append(
            f"Sucursal: {name}. Horario de atención: {describe_hours(hours)}."
        )
    else:
        # Sin filas no se asume "cerrada" —es la misma regla que BranchHours
        # le aplica a las agendas—, y tampoco se inventa un horario.
        fragments.append(
            f"Sucursal: {name}. Horario de atención: no está cargado; "
            f"conviene llamar a la sucursal antes de ir."
        )

    if staff:
        especialidades = sorted({e for _, sus in staff for e in sus})
        profesionales = [
            f"{nombre} ({_join(sorted(sus))})" if sus else nombre
            for nombre, sus in sorted(staff)
        ]
        fragments.append(
            f"Sucursal: {name}. Especialidades que se atienden en esta sede: "
            f"{_join(especialidades)}. Profesionales que atienden acá: "
            f"{_join(profesionales)}."
        )

    return fragments


# --------------------------------------------------------------------------
#  Servicios
# --------------------------------------------------------------------------

def format_price(price, currency: str) -> str:
    """``Bs 80`` o ``Bs 80,50``. Coma decimal, como se escribe en Bolivia."""
    label = CURRENCY_LABELS.get(currency, currency)
    price = Decimal(price)
    if price == price.to_integral_value():
        return f"{label} {int(price)}"
    return f"{label} {price:.2f}".replace(".", ",")


def service_fragments(service) -> list[str]:
    """Los fragmentos de un servicio: precio, preparación y descripción."""
    # Import diferido: ``indexing`` importa este módulo.
    from .indexing import MIN_FRAGMENT_CHARS, _SENTENCE

    kind = service.get_kind_display()
    head = f"{kind}: {service.name.strip()}."
    if service.specialty_id and service.specialty:
        head += f" De {service.specialty.name}."

    if service.price is None:
        precio = "Precio: a consultar en la sucursal."
    else:
        precio = (
            f"Precio: cuesta {format_price(service.price, service.currency)}."
        )
    fragments = [f"{head} {precio}"]

    preparation = (service.preparation or "").strip()
    # "Qué hacer antes de ir" y "ayunas" son las palabras con que se pregunta;
    # "preparación" casi nadie la escribe.
    prep_head = f"{head} Preparación, qué hacer antes de ir y si hay que ir en ayunas:"
    if preparation:
        fragments.append(f"{prep_head} {preparation}")
    else:
        fragments.append(f"{prep_head} no requiere preparación.")

    for sentence in _SENTENCE.split((service.description or "").strip()):
        sentence = sentence.strip()
        if len(sentence) >= MIN_FRAGMENT_CHARS:
            fragments.append(f"{head} {sentence}")

    return fragments


# --------------------------------------------------------------------------
#  Políticas de la organización
# --------------------------------------------------------------------------

def policy_fragments(organization) -> list[str]:
    """Lo que vale para toda la organización y no es de una sede.

    El texto sigue exactamente lo que hace ``appointments/changes.py``: con
    menos aviso **se puede cancelar igual**, sólo que el pago no se devuelve;
    y reprogramar no tiene plazo. Un asistente que dijera "no se puede
    cancelar con menos de 24 horas" estaría inventando una regla.
    """
    horas = organization.cancellation_notice_hours
    return [
        f"Política de cancelación de {organization.name}: podés cancelar tu "
        f"ficha; si avisás con al menos {horas} horas de anticipación se te "
        f"devuelve el pago, y con menos aviso se cancela igual pero el pago "
        f"no se devuelve. Reprogramar una ficha para otro horario no tiene "
        f"ese plazo.",
    ]


# --------------------------------------------------------------------------
#  Todo junto
# --------------------------------------------------------------------------

def administrative_sources(organization) -> list[tuple]:
    """``[(source_type, source_id, [textos])]`` de toda la organización.

    **Tiene que llamarse dentro de un ``tenant_context()``**, como
    ``index_specialties``: sin contexto, RLS devuelve cero sedes.
    Las consultas filtran además por organización explícitamente, por la
    misma razón que lo hace ``retrieval.py``.
    """
    sources = []

    branches = list(
        Branch.objects.filter(organization=organization, is_active=True)
        .order_by("name")
    )
    hours = defaultdict(list)
    for franja in BranchHours.objects.filter(
        organization=organization, branch__in=branches,
    ):
        hours[franja.branch_id].append(franja)

    # Quién atiende dónde, y de qué. Dos consultas, no una por sede.
    specialties_of = defaultdict(list)
    for link in PractitionerSpecialty.objects.filter(
        organization=organization, specialty__is_active=True,
    ).select_related("specialty"):
        specialties_of[link.practitioner_id].append(link.specialty.name)

    staff = defaultdict(list)
    for link in PractitionerBranch.objects.filter(
        organization=organization, branch__in=branches,
        practitioner__is_active=True,
    ).select_related("practitioner"):
        p = link.practitioner
        staff[link.branch_id].append(
            (f"{p.first_name} {p.last_name}".strip(),
             specialties_of.get(p.id, [])),
        )

    for branch in branches:
        sources.append((
            SourceType.BRANCH, branch.id,
            branch_fragments(branch, hours[branch.id], staff[branch.id]),
        ))

    for service in (
        Service.objects.filter(organization=organization, is_active=True)
        .select_related("specialty").order_by("name")
    ):
        sources.append((SourceType.SERVICE, service.id, service_fragments(service)))

    sources.append((
        SourceType.POLICY, organization.id, policy_fragments(organization),
    ))
    return sources
