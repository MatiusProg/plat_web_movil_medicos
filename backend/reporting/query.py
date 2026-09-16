"""Característica general 5 — De una definición de reporte a sus filas.

Una *definición* es lo que el usuario armó en el constructor:

    {
        "dataset": "patients",
        "columns": ["document_number", "last_name", "sex"],
        "filters": [{"field": "is_active", "operator": "eq", "value": true}],
        "order_by": ["last_name", "-created_at"]
    }

Este módulo la valida contra el catálogo de ``datasets.py`` y la convierte en
un ``QuerySet``. Todo lo que no esté declarado en el catálogo se rechaza con un
error que dice qué se pidió y qué había disponible; **nunca se deja pasar en
silencio**, que es el defecto clásico de un filtro dinámico: un criterio mal
escrito que no filtra nada devuelve la tabla entera, y quien lee el reporte
concluye que ése es el dato.

**El límite de filas no es una precaución de rendimiento**, o no sólo. Un
reporte de cien mil filas armado sin querer —un filtro que no filtró— es un
PDF que nadie va a mirar y una petición que ocupa el proceso. Se corta en
``MAX_ROWS`` y la respuesta **dice que se cortó**, porque un reporte truncado
que no avisa es peor que ninguno.
"""

from dataclasses import dataclass

from django.core.exceptions import FieldError

from . import datasets

# Tope de filas de un reporte. 20.000 entra cómodo en un Excel y es más de lo
# que cualquier pantalla de este sistema tiene hoy.
MAX_ROWS = 20_000


class DefinitionError(ValueError):
    """Una definición que el catálogo no admite.

    Lleva ``code`` además del mensaje para que la vista arme la respuesta con
    la misma forma que el resto de la API —``{"code": ..., "detail": ...}``—.
    """

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass
class Report:
    """Una definición ya validada. Lo que sale de ``build``."""

    dataset: datasets.Dataset
    columns: tuple[datasets.Column, ...]
    queryset: object
    order_by: tuple[str, ...]

    @property
    def headers(self) -> list[str]:
        return [column.label for column in self.columns]

    def rows(self, limit: int = MAX_ROWS) -> tuple[list[list], bool]:
        """Las filas ya formateadas, y si hubo que truncar.

        Se piden ``limit + 1`` para saber si sobraba alguna sin contar la tabla
        entera: un ``COUNT(*)`` sobre el mismo filtro es una segunda consulta
        que sólo sirve para escribir un número en una nota al pie.
        """
        paths = [column.path for column in self.columns]
        crudas = list(self.queryset.values_list(*paths)[: limit + 1])
        truncado = len(crudas) > limit
        if truncado:
            crudas = crudas[:limit]
        return [
            [_format(column, valor)
             for column, valor in zip(self.columns, fila)]
            for fila in crudas
        ], truncado


def build(definition: dict, user) -> Report:
    """Valida la definición y devuelve el reporte listo para leer.

    Lanza ``DefinitionError`` si algo no está en el catálogo, y
    ``PermissionError`` si el usuario no puede leer ese conjunto. Los dos casos
    los traduce la vista; acá no se sabe nada de HTTP.
    """
    dataset = datasets.get((definition.get("dataset") or "").strip())
    if dataset is None:
        disponibles = ", ".join(sorted(datasets.REGISTRY))
        raise DefinitionError(
            "conjunto_desconocido",
            f"No existe el conjunto de datos pedido. Disponibles: {disponibles}.",
        )

    if not user.has_permission(dataset.permission):
        raise PermissionError(dataset.permission)

    columns = _columns(dataset, definition.get("columns"))
    queryset = _apply_filters(
        dataset.base_queryset(user), dataset, definition.get("filters") or [],
    )
    order_by = _order(dataset, definition.get("order_by"))

    if order_by:
        queryset = queryset.order_by(*order_by)

    # Una columna que cruza un ``ManyToMany`` —la especialidad de un
    # profesional— multiplica la fila por cada relación. Es lo correcto para un
    # reporte (una línea por profesional y especialidad), pero sin ``distinct``
    # un filtro sobre esa misma relación duplica filas idénticas.
    queryset = queryset.distinct()

    return Report(dataset=dataset, columns=columns,
                  queryset=queryset, order_by=order_by)


def _columns(dataset, pedidas) -> tuple[datasets.Column, ...]:
    """Las columnas elegidas, o las predeterminadas si no eligió ninguna."""
    codigos = [c for c in (pedidas or []) if str(c).strip()]
    if not codigos:
        codigos = list(dataset.default_columns)

    columnas = []
    for codigo in codigos:
        columna = dataset.column(str(codigo).strip())
        if columna is None:
            raise DefinitionError(
                "columna_desconocida",
                f"La columna «{codigo}» no existe en «{dataset.label}».",
            )
        columnas.append(columna)

    # Un reporte sin columnas es un archivo vacío: se corta acá y no en el
    # exportador, donde el error saldría como un Excel de cero columnas.
    if not columnas:
        raise DefinitionError(
            "sin_columnas", "Hay que elegir al menos una columna.",
        )
    return tuple(columnas)


def _apply_filters(queryset, dataset, criterios):
    """Aplica los criterios de selección, uno por uno."""
    if not isinstance(criterios, list):
        raise DefinitionError(
            "filtros_invalidos", "«filters» tiene que ser una lista.",
        )

    for criterio in criterios:
        if not isinstance(criterio, dict):
            raise DefinitionError(
                "filtros_invalidos",
                "Cada filtro es un objeto con «field», «operator» y «value».",
            )

        codigo = str(criterio.get("field") or "").strip()
        filtro = dataset.filter(codigo)
        if filtro is None:
            disponibles = ", ".join(f.code for f in dataset.filters)
            raise DefinitionError(
                "filtro_desconocido",
                f"No se puede filtrar por «{codigo}» en «{dataset.label}». "
                f"Se puede por: {disponibles}.",
            )

        operador = str(criterio.get("operator") or "eq").strip()
        lookups = datasets.OPERATORS[filtro.kind]
        if operador not in lookups:
            raise DefinitionError(
                "operador_invalido",
                f"El operador «{operador}» no se aplica a «{filtro.label}». "
                f"Se puede usar: {', '.join(lookups)}.",
            )

        valor = _coerce(filtro, criterio.get("value"))
        # Un valor vacío es un criterio que el usuario dejó sin llenar en el
        # formulario previo. Se ignora en vez de filtrar por cadena vacía, que
        # devolvería cero filas sin explicar por qué.
        if valor is None or valor == "" or valor == []:
            continue

        expresion = f"{filtro.path}__{lookups[operador]}"
        try:
            queryset = queryset.filter(**{expresion: valor})
        except (FieldError, ValueError, TypeError) as error:
            raise DefinitionError(
                "filtro_invalido",
                f"No se pudo aplicar el filtro «{filtro.label}»: {error}",
            ) from error

    return queryset


def _coerce(filtro, valor):
    """Lleva el valor del JSON al tipo que el ORM espera.

    JSON no distingue ``"true"`` de ``true`` ni ``"2"`` de ``2``, y un
    formulario HTML manda todo como cadena. Sin esto, filtrar por «activo» con
    la cadena ``"false"`` da verdadero —toda cadena no vacía lo es— y el
    reporte sale con los inactivos incluidos.
    """
    if valor is None:
        return None

    if filtro.kind == datasets.BOOLEAN:
        if isinstance(valor, bool):
            return valor
        return str(valor).strip().lower() in ("true", "1", "sí", "si", "on")

    if filtro.kind == datasets.NUMBER:
        try:
            return int(str(valor).strip())
        except ValueError:
            raise DefinitionError(
                "valor_invalido",
                f"«{filtro.label}» espera un número y llegó «{valor}».",
            ) from None

    if isinstance(valor, list):
        return [str(v).strip() for v in valor if str(v).strip()]
    return str(valor).strip()


def _order(dataset, pedido) -> tuple[str, ...]:
    """El orden pedido, traducido a rutas del ORM.

    Se ordena por **columnas declaradas**, no por rutas: dejar pasar una ruta
    arbitraria acá anularía la lista blanca del catálogo, porque
    ``order_by("user__password")`` no devuelve el campo pero sí lo filtra por
    él, y con eso se adivina un valor letra por letra.
    """
    codigos = [c for c in (pedido or []) if str(c).strip()]
    if not codigos:
        return tuple(dataset.default_order)

    rutas = []
    for codigo in codigos:
        crudo = str(codigo).strip()
        descendente = crudo.startswith("-")
        columna = dataset.column(crudo.lstrip("-"))
        if columna is None:
            raise DefinitionError(
                "orden_desconocido",
                f"No se puede ordenar por «{crudo}»: no es una columna de "
                f"«{dataset.label}».",
            )
        rutas.append(f"-{columna.path}" if descendente else columna.path)
    return tuple(rutas)


def _format(columna, valor):
    """El valor tal como se imprime.

    Las tres reglas salen de mirar un Excel mal exportado: los códigos de un
    ``choices`` no se entienden (``M`` en vez de «Masculino»), un booleano sale
    como ``True`` en inglés, y un ``None`` sale como la palabra «None» en vez
    de una celda vacía.
    """
    if valor is None:
        return ""
    if columna.choices:
        return columna.choices.get(str(valor), valor)
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    return valor
