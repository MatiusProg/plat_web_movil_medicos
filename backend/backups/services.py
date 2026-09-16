"""Característica general 6 — Generar y restaurar la copia de una organización.

El formato es un JSON único con esta forma::

    {
      "format": "plataforma-medica-backup",
      "version": 1,
      "generated_at": "2026-09-15T22:40:00-04:00",
      "organization": {"id": "...", "slug": "kolping", "name": "..."},
      "counts": {"accounts.User": 12, "patients.Patient": 340, ...},
      "checksum": "<sha256 del payload canónico>",
      "payload": {"accounts.User": [...], ...}
    }

Tres decisiones que valen más que el código:

**1. Copia lógica en JSON, no un volcado binario.** Un `pg_dump -Fc` sólo lo
lee un PostgreSQL de versión compatible, y no se puede acotar a un inquilino
sin escribir un `WHERE` por tabla a mano. Éste se abre con cualquier cosa, se
revisa a ojo, y es *de la organización*: es lo que un cliente de un SaaS puede
exigir llevarse. El volcado de la instalación entera existe igual, en
``manage.py dump_database``, para el otro caso.

**2. El archivo no se guarda en la base.** Se genera y se descarga. Guardarlo
duplicaría dentro del sistema todos los datos que el sistema protege —con RLS
sobre la tabla que los contiene, pero en claro dentro de un JSON— y convertiría
la tabla de respaldos en el lugar más rentable para atacar. Lo que queda
registrado es **que** se hizo la copia, quién y de cuánto: eso es
``BackupRecord``.

**3. La restauración reemplaza, no fusiona.** Se borra lo que hay y se escribe
lo del archivo, todo dentro de una transacción. La alternativa —insertar lo que
falte— suena más prudente y es peor: deja la organización en un estado que no
es ni el de antes ni el del archivo, y que nadie puede describir. Restaurar es
volver a un momento; si el archivo no tiene una fila, es porque en ese momento
no existía.
"""

import datetime as dt
import hashlib
import json
import logging

from django.apps import apps
from django.core import serializers
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from tenancy.context import tenant_context

from . import manifest

logger = logging.getLogger(__name__)

FORMAT = "plataforma-medica-backup"
VERSION = 1


class BackupError(Exception):
    """Algo impide generar o restaurar. ``code`` distingue qué, para el mensaje."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


# --------------------------------------------------------------------------
#  Copia
# --------------------------------------------------------------------------
def create(organization) -> dict:
    """Arma la copia de una organización y la devuelve como diccionario.

    Corre dentro de ``tenant_context``, así que RLS ya garantiza que no se
    lleve una fila ajena. El ``filter(organization=...)`` de cada consulta es
    la segunda cerradura, por la misma razón que en ``audit.views``: si algún
    día esto se llama sin contexto, la copia tiene que salir vacía y no con la
    base entera.
    """
    payload: dict[str, list] = {}
    counts: dict[str, int] = {}

    with tenant_context(organization.id):
        for table in manifest.TABLES:
            model = apps.get_model(table.app, table.model)
            queryset = model.objects.filter(organization=organization)
            # `serialize` devuelve una cadena JSON; se vuelve a cargar para
            # poder anidarla en el documento en vez de pegarla como texto.
            filas = json.loads(serializers.serialize("json", queryset.iterator()))
            payload[table.key] = filas
            counts[table.key] = len(filas)

    documento = {
        "format": FORMAT,
        "version": VERSION,
        "generated_at": timezone.localtime().isoformat(),
        "organization": {
            "id": str(organization.id),
            "slug": organization.slug,
            "name": organization.name,
        },
        "counts": counts,
        "checksum": checksum(payload),
        "payload": payload,
    }
    return documento


def checksum(payload: dict) -> str:
    """El SHA-256 del contenido, para detectar un archivo alterado o cortado.

    ``sort_keys`` y separadores fijos no son cosmética: sin una forma canónica,
    el mismo contenido serializado dos veces da hashes distintos según el orden
    en que Python recorrió los diccionarios, y la comprobación fallaría siempre.

    No es una firma: quien edite el archivo puede recalcular el hash. Sirve
    contra la corrupción y la descarga incompleta, que es el caso que de verdad
    ocurre. Una firma exigiría una clave y está anotado en la documentación.
    """
    canonico = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, default=str)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def to_bytes(documento: dict) -> bytes:
    """El archivo tal como se descarga: JSON legible, con acentos de verdad."""
    return json.dumps(documento, ensure_ascii=False, indent=2,
                      default=str).encode("utf-8")


def filename(organization, generated_at=None) -> str:
    """``respaldo-kolping-20260915-2240.json``.

    El slug y el instante en el nombre porque estos archivos terminan todos en
    la carpeta de descargas: sin eso, el segundo se llama ``respaldo (1).json``
    y nadie sabe cuál es de cuándo.
    """
    momento = generated_at or timezone.localtime()
    if isinstance(momento, str):
        momento = dt.datetime.fromisoformat(momento)
    return f"respaldo-{organization.slug}-{momento:%Y%m%d-%H%M}.json"


# --------------------------------------------------------------------------
#  Restauración
# --------------------------------------------------------------------------
def inspect(documento) -> dict:
    """Comprueba el archivo y devuelve su resumen, sin escribir nada.

    Es lo que alimenta la pantalla de confirmación: antes de reemplazar la
    organización con un archivo hay que poder ver de qué organización es, de
    cuándo, y cuántas filas por tabla. Restaurar a ciegas es cómo se pierden
    los datos que el respaldo venía a proteger.
    """
    if not isinstance(documento, dict):
        raise BackupError("archivo_invalido",
                          "El archivo no es un respaldo de esta plataforma.")

    if documento.get("format") != FORMAT:
        raise BackupError(
            "formato_desconocido",
            "El archivo no es un respaldo de esta plataforma.",
        )

    version = documento.get("version")
    if version != VERSION:
        raise BackupError(
            "version_incompatible",
            f"El respaldo es de la versión {version} y este sistema lee la "
            f"{VERSION}.",
        )

    payload = documento.get("payload")
    if not isinstance(payload, dict):
        raise BackupError("archivo_invalido",
                          "El respaldo no trae contenido.")

    esperado = documento.get("checksum")
    calculado = checksum(payload)
    if esperado and esperado != calculado:
        raise BackupError(
            "checksum_no_coincide",
            "El contenido del respaldo no coincide con su suma de "
            "verificación: el archivo está incompleto o fue modificado.",
        )

    desconocidas = sorted(set(payload) - set(manifest.BY_KEY))
    if desconocidas:
        raise BackupError(
            "tabla_desconocida",
            "El respaldo trae tablas que este sistema no conoce: "
            f"{', '.join(desconocidas)}.",
        )

    return {
        "organization": documento.get("organization") or {},
        "generated_at": documento.get("generated_at"),
        "counts": documento.get("counts") or {
            clave: len(filas) for clave, filas in payload.items()
        },
        "restorable": [t.key for t in manifest.RESTORABLE if t.key in payload],
        "skipped": [
            t.key for t in manifest.TABLES
            if not t.restore and t.key in payload
        ],
    }


def restore(documento, organization) -> dict:
    """Reemplaza los datos de ``organization`` con los del archivo.

    Todo o nada: una sola transacción. Si algo falla a mitad, la organización
    queda como estaba — que es el único comportamiento aceptable para algo que
    empieza borrando.

    **Los usuarios se desactivan, no se borran.** Es la única tabla con
    tratamiento propio y el porqué está en ``manifest``: la bitácora es
    inalterable, así que borrar un usuario que dejó un asiento es imposible en
    esta base. Se repone lo que el archivo trae y se da de baja lógica lo que
    no menciona.

    **El archivo tiene que ser de esta organización.** Restaurar el respaldo de
    otra dentro de la propia importaría el padrón de pacientes de un centro
    médico ajeno, con sus antecedentes: exactamente lo que el aislamiento
    multi-inquilino existe para impedir. RLS no alcanzaría por sí solo —las
    filas se insertarían bajo el ``organization_id`` correcto, el de acá— así
    que la comprobación es de la aplicación y va antes de tocar nada.
    """
    resumen = inspect(documento)

    origen = (resumen["organization"] or {}).get("id")
    if str(origen) != str(organization.id):
        raise BackupError(
            "organizacion_distinta",
            "El respaldo pertenece a otra organización. No se puede restaurar "
            "acá: los datos de un centro médico no entran en otro.",
        )

    payload = documento["payload"]
    borradas: dict[str, int] = {}
    desactivadas: dict[str, int] = {}
    escritas: dict[str, int] = {}

    try:
        with tenant_context(organization.id):
            with transaction.atomic():
                # Las claves foráneas se comprueban al final de la transacción y
                # no fila por fila. Hace falta por dos motivos: las
                # autorreferencias —el titular de un paciente— cuyo orden dentro
                # de la misma tabla no se puede garantizar, y el hecho de que
                # `users` se repone antes que `branches`, a la que apunta.
                with connection.constraint_checks_disabled():
                    # Se limpia de abajo hacia arriba: primero lo que apunta.
                    for table in reversed(manifest.RESTORABLE):
                        if table.strategy != manifest.PURGE:
                            continue
                        model = apps.get_model(table.app, table.model)
                        cantidad, _ = (
                            model.objects
                            .filter(organization=organization)
                            .delete()
                        )
                        borradas[table.key] = cantidad

                    # Y se escribe de arriba hacia abajo.
                    for table in manifest.RESTORABLE:
                        filas = payload.get(table.key) or []
                        escritas[table.key] = _write(table, filas, organization)
                        if table.strategy == manifest.DEACTIVATE:
                            desactivadas[table.key] = _deactivate_absent(
                                table, filas, organization,
                            )

                # Fuera del bloque pero dentro de la transacción: acá PostgreSQL
                # comprueba lo que se dejó pendiente. Si el archivo tenía una
                # referencia rota, salta ahora y la transacción entera se
                # deshace.
                connection.check_constraints()
    except IntegrityError as error:
        # Un archivo con una referencia rota es un archivo malo, no una falla
        # del servidor: 400 con el motivo y no un 500 sin explicación. La
        # transacción ya se deshizo, así que la organización quedó como estaba.
        raise BackupError(
            "referencia_rota",
            "El respaldo tiene referencias que no cierran y no se pudo "
            f"restaurar. No se modificó nada. Detalle: {error}",
        ) from error

    return {
        "organization": str(organization.id),
        "generated_at": resumen["generated_at"],
        "deleted": borradas,
        "deactivated": desactivadas,
        "written": escritas,
        "skipped": resumen["skipped"],
    }


def _deactivate_absent(table, filas, organization) -> int:
    """Desactiva las filas que el archivo no menciona. Ver ``manifest``.

    Devuelve cuántas. Una cuenta creada después del respaldo queda sin poder
    entrar, que es lo que «volver a ese momento» significa para el acceso, sin
    romper la cadena de auditoría que la nombra.
    """
    model = apps.get_model(table.app, table.model)
    presentes = {fila.get("pk") for fila in filas}
    return (
        model.objects
        .filter(organization=organization, is_active=True)
        .exclude(pk__in=presentes)
        .update(is_active=False)
    )


def _write(table, filas, organization) -> int:
    """Escribe las filas de una tabla, forzando la organización de destino.

    ``serializers.deserialize`` reconstruye el objeto con los valores del
    archivo, ``organization_id`` incluido. Se lo pisa igual: un archivo editado
    a mano con otro ``organization_id`` intentaría escribir en otro inquilino,
    y aunque RLS lo rechazaría con un error de base, el mensaje sería
    incomprensible. Acá se corrige antes y el resultado es el correcto.
    """
    if not filas:
        return 0

    escritas = 0
    for objeto in serializers.deserialize("json", json.dumps(filas),
                                          ignorenonexistent=True):
        objeto.object.organization_id = organization.id
        # `save_base` con `raw=True`: escribe la fila tal cual, sin disparar
        # `save()` del modelo. Hace falta porque varios modelos recalculan
        # campos al guardar —`Practitioner.search_name`, por ejemplo— y una
        # restauración tiene que reponer lo que había, no recalcularlo.
        objeto.object.save_base(raw=True, using="default")
        escritas += 1
    return escritas
