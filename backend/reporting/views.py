"""Característica general 5 — La API del constructor de reportes.

    GET    /api/reporting/datasets/          qué se puede reportar y con qué filtros
    POST   /api/reporting/run/               ejecutar una definición suelta
    GET    /api/reporting/reports/           los reportes guardados que puedo ver
    POST   /api/reporting/reports/           guardar uno
    GET    /api/reporting/reports/{id}/      uno
    PATCH  /api/reporting/reports/{id}/      editarlo (sólo el dueño)
    DELETE /api/reporting/reports/{id}/      borrarlo (sólo el dueño)
    POST   /api/reporting/reports/{id}/run/  ejecutar uno guardado

``run`` es un ``POST`` y no un ``GET`` aunque no escriba nada. La razón es
práctica: la definición es un objeto anidado —columnas, filtros con operador y
valor, orden— y meterlo en la query string obliga a serializarlo a mano en el
cliente y a parsearlo a mano acá, con el límite de longitud de una URL encima.
Queda anotado que no es idempotente en el sentido de REST y sí en el de
efectos: ejecutar un reporte no cambia nada.

**Toda ejecución deja asiento en la bitácora.** No es una exigencia de la
consigna 5 sino de la 3, y es la que las cruza: exportar el padrón de pacientes
a un Excel es sacar datos del sistema, y eso es exactamente lo que una bitácora
tiene que poder contar después. Se registra qué conjunto, con qué filtros,
cuántas filas y a qué formato — no las filas en sí, que serían la base entera
dentro de la bitácora.
"""

from django.db.models import Q
from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit import services as bitacora
from audit.actions import Action

from . import datasets, delivery, exporters, query
from .models import SavedReport
from .permissions import CanRunReports, CanSaveReports, CanShareReports
from .serializers import (
    DatasetSerializer,
    RunSerializer,
    SavedReportSerializer,
)

UUID_REGEX = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


class DatasetListView(APIView):
    """Qué puede reportar quien pregunta, con columnas, filtros y operadores.

    Es lo primero que pide el constructor al abrirse, y lo único que necesita
    para dibujarse entero.
    """

    permission_classes = [IsAuthenticated, CanRunReports]

    def get(self, request):
        disponibles = datasets.available_for(request.user)
        return Response({
            "datasets": DatasetSerializer(disponibles, many=True).data,
            "formats": list(exporters.FORMATS),
            "max_rows": query.MAX_ROWS,
        })


class RunReportView(APIView):
    """Ejecuta una definición suelta: la que el usuario acaba de armar."""

    permission_classes = [IsAuthenticated, CanRunReports]

    def post(self, request):
        serializer = RunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return _run(request, serializer.validated_data)


class SavedReportViewSet(viewsets.ModelViewSet):
    """Los reportes guardados de la organización.

    Se ven los propios y los que alguien compartió. **Se editan y se borran
    sólo los propios**, incluso siendo administrador: un reporte compartido que
    otro puede reescribir sin avisar deja de ser confiable para quien lo corre
    todos los lunes. Para sacar de circulación el reporte de otro está quitarle
    el permiso de compartir, que es una decisión explícita.
    """

    serializer_class = SavedReportSerializer
    permission_classes = [IsAuthenticated, CanRunReports]
    lookup_value_regex = UUID_REGEX

    def get_permissions(self):
        """Guardar exige un permiso más que ejecutar."""
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), CanRunReports(), CanSaveReports()]
        return super().get_permissions()

    def get_queryset(self):
        organization = getattr(self.request.user, "organization", None)
        if organization is None:
            return SavedReport.objects.none()

        queryset = (
            SavedReport.objects
            .filter(organization=organization)
            .filter(Q(owner=self.request.user) | Q(is_shared=True))
            .select_related("owner")
        )
        if codigo := self.request.query_params.get("dataset"):
            queryset = queryset.filter(dataset=codigo)
        return queryset

    def perform_create(self, serializer):
        self._check_sharing(serializer.validated_data)
        report = serializer.save()
        self._audit(report, Action.REPORT_SAVE)

    def perform_update(self, serializer):
        if serializer.instance.owner_id != self.request.user.id:
            self.permission_denied(
                self.request,
                message="Sólo el dueño puede editar este reporte.",
            )
        self._check_sharing(serializer.validated_data)
        report = serializer.save()
        self._audit(report, Action.REPORT_SAVE)

    def _check_sharing(self, datos):
        """Compartir exige su propio permiso.

        Se comprueba acá y no en ``get_permissions`` porque depende del
        *cuerpo* de la petición, no del verbo: guardar un reporte privado lo
        puede hacer cualquiera con ``report.save``; ponerlo a la vista de toda
        la organización, no.
        """
        if datos.get("is_shared") and not CanShareReports().has_permission(
            self.request, self
        ):
            self.permission_denied(
                self.request,
                message="No tenés permiso para compartir reportes con el "
                        "resto de la organización.",
            )

    def perform_destroy(self, instance):
        if instance.owner_id != self.request.user.id:
            self.permission_denied(
                self.request,
                message="Sólo el dueño puede eliminar este reporte.",
            )
        self._audit(instance, Action.REPORT_DELETE)
        instance.delete()

    def _audit(self, report, accion):
        bitacora.record(
            self.request, accion, "saved_reports", report.id,
            {"name": report.name, "dataset": report.dataset,
             "is_shared": report.is_shared},
        )

    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        """Ejecuta un reporte guardado.

        Los filtros y el formato del cuerpo **se superponen** a los guardados,
        para el caso normal: el reporte guardado es «pacientes activos por
        sucursal» y cada mes se corre cambiándole el mes. Guardar un reporte
        por cada período sería absurdo.
        """
        report = self.get_object()

        definicion = dict(report.definition or {})
        definicion["dataset"] = report.dataset

        serializer = RunSerializer(data={**definicion, **request.data})
        serializer.is_valid(raise_exception=True)

        datos = serializer.validated_data
        datos.setdefault("title", report.name)
        if not datos.get("title"):
            datos["title"] = report.name
        return _run(request, datos, saved_report=report)


def _run(request, datos, saved_report=None):
    """El camino común de las dos formas de ejecutar.

    Vive fuera de las vistas porque es exactamente el mismo trabajo se haya
    pedido con una definición suelta o con una guardada, y duplicarlo era
    garantizar que un arreglo entrara en una sola de las dos.
    """
    definicion = {
        "dataset": datos["dataset"],
        "columns": datos.get("columns") or [],
        "filters": datos.get("filters") or [],
        "order_by": datos.get("order_by") or [],
    }

    try:
        report = query.build(definicion, request.user)
    except query.DefinitionError as error:
        return Response(
            {"code": error.code, "detail": error.detail},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except PermissionError as error:
        return Response(
            {"code": "sin_permiso_sobre_el_conjunto",
             "detail": "No tenés permiso para consultar estos datos. "
                       f"Hace falta «{error.args[0]}»."},
            status=status.HTTP_403_FORBIDDEN,
        )

    formato = datos.get("format", "json")
    titulo = (datos.get("title") or report.dataset.label).strip()

    if formato == "json":
        # La vista previa del constructor: pocas filas y sin generar archivo.
        filas, truncado = report.rows(limit=datos.get("preview_rows", 50))
        _audit_run(request, report, definicion, formato, len(filas),
                   saved_report)
        return Response({
            "dataset": report.dataset.code,
            "title": titulo,
            "columns": [
                {"code": c.code, "label": c.label, "kind": c.kind}
                for c in report.columns
            ],
            "rows": filas,
            "truncated": truncado,
        })

    filas, truncado = report.rows()
    contenido, mime, nombre = exporters.export(
        formato, report.headers, filas, titulo,
        subtitle=_subtitulo(report, definicion), truncated=truncado,
    )

    destinatarios = datos.get("recipients") or []
    if destinatarios:
        try:
            enviados = delivery.send(
                request.user, destinatarios,
                subject=f"Reporte · {titulo}",
                body=_cuerpo_del_correo(request.user, titulo, len(filas),
                                        truncado),
                filename=nombre, content=contenido, mime=mime,
            )
        except delivery.DeliveryError as error:
            return Response(
                {"code": error.code, "detail": error.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        _audit_run(request, report, definicion, formato, len(filas),
                   saved_report, recipients=enviados)
        return Response({
            "sent": True, "recipients": enviados,
            "filename": nombre, "rows": len(filas), "truncated": truncado,
        })

    _audit_run(request, report, definicion, formato, len(filas), saved_report)

    respuesta = HttpResponse(contenido, content_type=mime)
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    # El navegador necesita verlas para poder leerlas desde `fetch`: sin esto,
    # el frontend no puede saber el nombre del archivo ni avisar del truncado.
    respuesta["X-Report-Rows"] = str(len(filas))
    respuesta["X-Report-Truncated"] = "1" if truncado else "0"
    respuesta["Access-Control-Expose-Headers"] = (
        "Content-Disposition, X-Report-Rows, X-Report-Truncated"
    )
    return respuesta


def _subtitulo(report, definicion) -> str:
    """Los criterios aplicados, en una línea, para la cabecera del archivo.

    Un reporte exportado se reenvía y se imprime, y fuera del sistema nadie
    recuerda con qué filtros salió. Sin esto, dos PDF del mismo reporte con
    criterios distintos son indistinguibles.
    """
    criterios = []
    for criterio in definicion.get("filters") or []:
        filtro = report.dataset.filter(str(criterio.get("field") or ""))
        if filtro is None:
            continue
        valor = criterio.get("value")
        if valor in (None, "", []):
            continue
        if filtro.choices:
            valor = filtro.choices.get(str(valor), valor)
        criterios.append(f"{filtro.label}: {valor}")

    if not criterios:
        return "Sin criterios de selección — todos los registros."
    return "Criterios — " + " · ".join(criterios)


def _cuerpo_del_correo(user, titulo, filas, truncado) -> str:
    cuerpo = (
        f"Hola,\n\n"
        f"{user.first_name or user.email} generó el reporte «{titulo}» desde "
        f"la plataforma y te lo comparte adjunto.\n\n"
        f"Filas incluidas: {filas}.\n"
    )
    if truncado:
        cuerpo += (
            "\nATENCIÓN: el reporte se truncó porque superaba el máximo de "
            "filas. No está completo.\n"
        )
    cuerpo += (
        "\nEste mensaje se envió automáticamente; no hace falta responderlo.\n"
    )
    return cuerpo


def _audit_run(request, report, definicion, formato, filas, saved_report,
               recipients=None):
    """El asiento de una ejecución. Característica general 3.

    **No se guardan las filas**, sólo con qué se pidieron y cuántas salieron:
    una bitácora que copie el contenido de cada reporte termina siendo una
    segunda base de datos con los mismos datos y ninguna de las protecciones.
    Lo que interesa auditar es quién sacó qué y cuándo.
    """
    detalle = {
        "dataset": report.dataset.code,
        "columns": [c.code for c in report.columns],
        "filters": definicion.get("filters") or [],
        "format": formato,
        "rows": filas,
    }
    if saved_report is not None:
        detalle["saved_report"] = str(saved_report.id)
        detalle["saved_report_name"] = saved_report.name
    if recipients:
        detalle["recipients"] = recipients

    bitacora.record(
        request,
        Action.REPORT_EMAIL if recipients else Action.REPORT_RUN,
        "reports", report.dataset.code, detalle,
    )
