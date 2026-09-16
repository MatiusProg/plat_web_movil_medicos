"""Característica general 5 — El catálogo de lo que se puede reportar.

La consigna de la materia pide que el usuario **construya sus propios
reportes**, eligiendo qué columnas, con qué criterios de selección y en qué
orden. Eso obliga a decidir una cosa antes que ninguna otra: **de dónde salen
las columnas que se le ofrecen**.

Había dos caminos y el que no se tomó explica el diseño de este archivo:

1. *Reflexión sobre los modelos* — recorrer ``Model._meta.fields`` y ofrecer
   todo. Es menos código y es una puerta abierta: ``password`` es un campo de
   ``User``, ``guardian__user__password`` es una ruta válida del ORM, y el día
   que alguien agregue un campo sensible a un modelo queda publicado sin que
   nadie lo decida.
2. **Una lista blanca declarativa** — lo que está acá se puede pedir y nada
   más. Es lo que se hace.

Con la lista blanca, el constructor de reportes del frontend no necesita saber
nada del modelo de datos: pide ``GET /api/reporting/datasets/`` y recibe las
columnas, los filtros y sus tipos, que es exactamente lo que necesita para
dibujar el formulario previo a generar —el otro pedido de la consigna: «todo
reporte antes de generar debe haber una interface para posibilitar filtrar»—.

**Cada conjunto declara el permiso que exige.** Un reporte no es una puerta
lateral: quien no puede leer pacientes por la API tampoco puede sacarlos en un
Excel. El permiso es el mismo código que ya usan las vistas del módulo dueño
del dato, no uno nuevo de ``reporting``.

**Cada conjunto filtra por organización explícitamente**, además de RLS, por la
misma razón que ``audit.views``: el día que un reporte se genere desde un
comando de gestión sin contexto de inquilino, la lista tiene que salir vacía y
no completa.
"""

from dataclasses import dataclass, field
from typing import Any, Callable

from accounts.models import AuditLog
from catalog.models import Branch, Practitioner, Specialty
from patients.models import Patient
from scheduling.models import Schedule

# --------------------------------------------------------------------------
#  Tipos de dato que el constructor sabe dibujar
# --------------------------------------------------------------------------
#  No son los tipos de Django: son los del formulario. El frontend usa esto
#  para decidir si pinta un campo de texto, un selector de fecha o un
#  desplegable, y para saber qué operadores de comparación ofrecer.
TEXT = "text"
NUMBER = "number"
DATE = "date"
DATETIME = "datetime"
BOOLEAN = "boolean"
CHOICE = "choice"

# Qué operadores tiene sentido ofrecer para cada tipo, y a qué lookup del ORM
# corresponde cada uno. La clave es lo que viaja en el JSON de la petición.
OPERATORS: dict[str, dict[str, str]] = {
    TEXT: {
        "eq": "iexact",
        "contains": "icontains",
        "starts": "istartswith",
    },
    NUMBER: {
        "eq": "exact", "lt": "lt", "lte": "lte", "gt": "gt", "gte": "gte",
    },
    DATE: {
        "eq": "exact", "lt": "lt", "lte": "lte", "gt": "gt", "gte": "gte",
    },
    # Un instante se compara por su fecha: quien escribe 06/09 en un
    # formulario espera que ese día entre entero, no hasta las 00:00.
    DATETIME: {
        "eq": "date", "lt": "date__lt", "lte": "date__lte",
        "gt": "date__gt", "gte": "date__gte",
    },
    BOOLEAN: {"eq": "exact"},
    CHOICE: {"eq": "exact", "in": "in"},
}


@dataclass(frozen=True)
class Column:
    """Una columna que el usuario puede elegir.

    ``path`` es la ruta del ORM y **no** se le muestra al usuario: el cliente
    manda ``code`` y acá se traduce. Así, renombrar un campo del modelo no
    rompe los reportes ya guardados.
    """

    code: str
    label: str
    path: str
    kind: str = TEXT
    # Para las columnas con ``choices``: el valor guardado es ``M`` y lo que
    # hay que imprimir es «Masculino». Sin esto el Excel sale en códigos.
    choices: dict[str, str] | None = None


@dataclass(frozen=True)
class Filter:
    """Un criterio de selección ofrecido para este conjunto.

    ``path`` puede diferir del de la columna homónima: se filtra por
    ``branch_id`` (un uuid que el desplegable ya tiene) y se muestra
    ``branch__name``.
    """

    code: str
    label: str
    path: str
    kind: str = TEXT
    choices: dict[str, str] | None = None


@dataclass(frozen=True)
class Dataset:
    """Un origen de datos reportable."""

    code: str
    label: str
    description: str
    permission: str
    model: Any
    columns: tuple[Column, ...]
    filters: tuple[Filter, ...]
    default_columns: tuple[str, ...]
    default_order: tuple[str, ...] = ()
    # Cómo se acota el conjunto a la organización de quien pregunta. Se declara
    # por conjunto porque la ruta no siempre es ``organization``.
    scope: Callable[[Any, Any], Any] = field(default=None, repr=False)

    def column(self, code: str) -> Column | None:
        return _by_code(self.columns, code)

    def filter(self, code: str) -> Filter | None:
        return _by_code(self.filters, code)

    def base_queryset(self, user):
        """El universo del reporte para este usuario, ya acotado.

        Devuelve vacío para el Superadministrador de Plataforma: su alcance no
        incluye los datos internos de ningún inquilino, y un reporte no es la
        excepción.
        """
        organization = getattr(user, "organization", None)
        if organization is None:
            return self.model.objects.none()
        if self.scope is not None:
            return self.scope(self.model.objects, organization)
        return self.model.objects.filter(organization=organization)


def _by_code(items, code):
    for item in items:
        if item.code == code:
            return item
    return None


def _labels(choices_class) -> dict[str, str]:
    """El mapa valor → etiqueta de un ``TextChoices``."""
    return {value: str(label) for value, label in choices_class.choices}


# El día de la semana se guarda como entero (0 = lunes, como `isoweekday - 1`)
# y ningún ``TextChoices`` lo nombra: la convención vive en un comentario de
# `scheduling.models`. Un reporte con una columna «Día» que dice `2` no se
# puede leer, así que el mapa se declara acá. Las claves son cadenas porque es
# como viajan en el JSON del filtro.
WEEKDAYS = {
    "0": "Lunes", "1": "Martes", "2": "Miércoles", "3": "Jueves",
    "4": "Viernes", "5": "Sábado", "6": "Domingo",
}


# --------------------------------------------------------------------------
#  Los conjuntos
# --------------------------------------------------------------------------
#  Se declaran los del Sprint 1, que son los que tienen datos cargados. Los del
#  Sprint 2 —fichas, pagos, atenciones— se agregan acá cuando existan sus
#  modelos: un conjunto nuevo es un bloque en esta lista y nada más. Ése es el
#  punto de que la lista sea declarativa.

PATIENTS = Dataset(
    code="patients",
    label="Pacientes",
    description=(
        "El padrón de la organización, con sus titulares y sus pacientes a "
        "cargo."
    ),
    permission="patients.patient.read",
    model=Patient,
    columns=(
        Column("document_type", "Tipo de documento", "document_type", CHOICE,
               _labels(Patient.DocumentType)),
        Column("document_number", "Documento", "document_number", TEXT),
        Column("last_name", "Apellidos", "last_name", TEXT),
        Column("first_name", "Nombres", "first_name", TEXT),
        Column("birth_date", "Fecha de nacimiento", "birth_date", DATE),
        Column("sex", "Sexo", "sex", CHOICE, _labels(Patient.Sex)),
        Column("phone", "Teléfono", "phone", TEXT),
        Column("email", "Correo", "user__email", TEXT),
        Column("guardian", "Titular", "guardian__last_name", TEXT),
        Column("relationship", "Parentesco", "relationship", CHOICE,
               _labels(Patient.Relationship)),
        Column("is_active", "Activo", "is_active", BOOLEAN),
        Column("created_at", "Alta", "created_at", DATETIME),
    ),
    filters=(
        Filter("last_name", "Apellidos", "last_name", TEXT),
        Filter("document_number", "Documento", "document_number", TEXT),
        Filter("sex", "Sexo", "sex", CHOICE, _labels(Patient.Sex)),
        Filter("relationship", "Parentesco", "relationship", CHOICE,
               _labels(Patient.Relationship)),
        Filter("birth_date", "Fecha de nacimiento", "birth_date", DATE),
        Filter("is_active", "Activo", "is_active", BOOLEAN),
        Filter("created_at", "Fecha de alta", "created_at", DATETIME),
    ),
    default_columns=("document_number", "last_name", "first_name",
                     "birth_date", "phone", "is_active"),
    default_order=("last_name", "first_name"),
)

PRACTITIONERS = Dataset(
    code="practitioners",
    label="Profesionales",
    description="El directorio médico, con su matrícula y sus especialidades.",
    permission="catalog.professional.read",
    model=Practitioner,
    columns=(
        Column("last_name", "Apellidos", "last_name", TEXT),
        Column("first_name", "Nombres", "first_name", TEXT),
        Column("license_number", "Matrícula", "license_number", TEXT),
        Column("specialty", "Especialidad", "specialties__name", TEXT),
        Column("branch", "Sucursal", "branches__name", TEXT),
        Column("email", "Correo", "user__email", TEXT),
        Column("is_active", "Activo", "is_active", BOOLEAN),
        Column("created_at", "Alta", "created_at", DATETIME),
    ),
    filters=(
        Filter("last_name", "Apellidos", "last_name", TEXT),
        Filter("license_number", "Matrícula", "license_number", TEXT),
        Filter("specialty", "Especialidad", "specialties__name", TEXT),
        Filter("branch", "Sucursal", "branches__name", TEXT),
        Filter("is_active", "Activo", "is_active", BOOLEAN),
    ),
    default_columns=("last_name", "first_name", "license_number",
                     "specialty", "is_active"),
    default_order=("last_name", "first_name"),
)

SPECIALTIES = Dataset(
    code="specialties",
    label="Especialidades",
    description="El catálogo de especialidades y su descripción.",
    permission="catalog.specialty.read",
    model=Specialty,
    columns=(
        Column("name", "Especialidad", "name", TEXT),
        Column("description", "Descripción", "description", TEXT),
        Column("is_active", "Activa", "is_active", BOOLEAN),
        Column("created_at", "Alta", "created_at", DATETIME),
    ),
    filters=(
        Filter("name", "Especialidad", "name", TEXT),
        Filter("is_active", "Activa", "is_active", BOOLEAN),
    ),
    default_columns=("name", "description", "is_active"),
    default_order=("name",),
)

BRANCHES = Dataset(
    code="branches",
    label="Sucursales",
    description="Las sedes de la organización y sus datos de contacto.",
    permission="catalog.branch.read",
    model=Branch,
    columns=(
        Column("name", "Sucursal", "name", TEXT),
        Column("address", "Dirección", "address", TEXT),
        Column("phone", "Teléfono", "phone", TEXT),
        Column("timezone", "Zona horaria", "timezone", TEXT),
        Column("is_active", "Activa", "is_active", BOOLEAN),
        Column("created_at", "Alta", "created_at", DATETIME),
    ),
    filters=(
        Filter("name", "Sucursal", "name", TEXT),
        Filter("is_active", "Activa", "is_active", BOOLEAN),
    ),
    default_columns=("name", "address", "phone", "is_active"),
    default_order=("name",),
)

SCHEDULES = Dataset(
    code="schedules",
    label="Agendas médicas",
    description=(
        "Las agendas cargadas por profesional y sucursal, con su franja "
        "horaria y su duración de turno."
    ),
    permission="scheduling.schedule.read",
    model=Schedule,
    columns=(
        Column("practitioner", "Profesional", "practitioner__last_name", TEXT),
        Column("branch", "Sucursal", "branch__name", TEXT),
        Column("weekday", "Día", "weekday", CHOICE, WEEKDAYS),
        Column("start_time", "Desde", "start_time", TEXT),
        Column("end_time", "Hasta", "end_time", TEXT),
        Column("slot_minutes", "Minutos por turno", "slot_minutes", NUMBER),
        Column("capacity", "Cupo por franja", "capacity", NUMBER),
        Column("valid_from", "Vigente desde", "valid_from", DATE),
        Column("valid_until", "Vigente hasta", "valid_until", DATE),
        Column("is_active", "Activa", "is_active", BOOLEAN),
    ),
    filters=(
        Filter("practitioner", "Profesional", "practitioner__last_name", TEXT),
        Filter("branch", "Sucursal", "branch__name", TEXT),
        Filter("weekday", "Día de la semana", "weekday", CHOICE, WEEKDAYS),
        Filter("valid_from", "Vigente desde", "valid_from", DATE),
        Filter("is_active", "Activa", "is_active", BOOLEAN),
    ),
    default_columns=("practitioner", "branch", "weekday",
                     "start_time", "end_time", "slot_minutes"),
    default_order=("practitioner__last_name", "weekday"),
)

AUDIT = Dataset(
    code="audit",
    label="Bitácora",
    description=(
        "Los asientos de auditoría. Exige el mismo permiso que la pantalla de "
        "la bitácora: un reporte no es una puerta lateral."
    ),
    permission="audit.log.read",
    model=AuditLog,
    columns=(
        Column("occurred_at", "Fecha y hora", "occurred_at", DATETIME),
        Column("actor", "Usuario", "user__email", TEXT),
        Column("action", "Acción", "action", TEXT),
        Column("entity", "Entidad", "entity", TEXT),
        Column("entity_id", "Identificador", "entity_id", TEXT),
        Column("ip_address", "Dirección IP", "ip_address", TEXT),
        Column("user_agent", "Agente", "user_agent", TEXT),
    ),
    filters=(
        Filter("actor", "Usuario", "user__email", TEXT),
        Filter("action", "Acción", "action", TEXT),
        Filter("entity", "Entidad", "entity", TEXT),
        Filter("occurred_at", "Fecha", "occurred_at", DATETIME),
        Filter("ip_address", "Dirección IP", "ip_address", TEXT),
    ),
    default_columns=("occurred_at", "actor", "action", "entity", "ip_address"),
    default_order=("-occurred_at",),
)


REGISTRY: dict[str, Dataset] = {
    dataset.code: dataset
    for dataset in (PATIENTS, PRACTITIONERS, SPECIALTIES, BRANCHES,
                    SCHEDULES, AUDIT)
}


def get(code: str) -> Dataset | None:
    return REGISTRY.get(code)


def available_for(user) -> list[Dataset]:
    """Los conjuntos que este usuario puede reportar.

    El constructor sólo ofrece lo que la persona puede pedir: un desplegable
    con seis opciones de las que cuatro devuelven 403 no ayuda a nadie.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return []
    return [
        dataset for dataset in REGISTRY.values()
        if user.has_permission(dataset.permission)
    ]
