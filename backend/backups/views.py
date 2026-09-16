"""Característica general 6 — La API de copias de seguridad y restauración.

    GET  /api/backups/records/    el historial: qué se respaldó y qué se restauró
    POST /api/backups/create/     genera la copia y la descarga
    POST /api/backups/inspect/    lee un archivo subido y dice qué contiene
    POST /api/backups/restore/    reemplaza los datos con los del archivo

**El flujo son dos pasos y no uno, a propósito.** ``inspect`` no escribe nada:
devuelve de qué organización es el archivo, de cuándo y cuántas filas trae por
tabla. La pantalla lo muestra y pide confirmación antes de llamar a
``restore``. Un único endpoint que reciba el archivo y reemplace todo es una
pérdida de datos a un clic de distancia, y el clic siempre termina ocurriendo.

**``restore`` pide confirmación explícita en el cuerpo.** ``confirm: true`` no
es burocracia: es lo que impide que un `POST` armado a mano —o una llamada
repetida por un reintento del navegador— reemplace la organización.
"""

import json

from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit import services as bitacora
from audit.actions import Action

from . import manifest, services
from .models import BackupRecord
from .permissions import CanCreateBackup, CanRestoreBackup
from .serializers import BackupRecordSerializer

# Tope del archivo que se acepta subir. Por encima, lo razonable es restaurar
# por consola con `manage.py restore_organization`, no por HTTP: una petición
# de medio giga ocupa el proceso entero durante minutos.
MAX_UPLOAD_BYTES = 64 * 1024 * 1024


class BackupRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """El historial. Sólo lectura: un registro de respaldo no se edita."""

    serializer_class = BackupRecordSerializer
    permission_classes = [IsAuthenticated, CanCreateBackup]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        organization = getattr(self.request.user, "organization", None)
        if organization is None:
            return BackupRecord.objects.none()
        return (
            BackupRecord.objects
            .filter(organization=organization)
            .select_related("performed_by")
        )


class CreateBackupView(APIView):
    """Genera la copia de la organización y la devuelve como descarga."""

    permission_classes = [IsAuthenticated, CanCreateBackup]

    def post(self, request):
        organization = _organization_or_error(request)
        if isinstance(organization, Response):
            return organization

        documento = services.create(organization)
        contenido = services.to_bytes(documento)
        nombre = services.filename(organization, documento["generated_at"])

        BackupRecord.objects.create(
            organization=organization,
            kind=BackupRecord.Kind.BACKUP,
            performed_by=request.user,
            filename=nombre,
            size_bytes=len(contenido),
            row_counts=documento["counts"],
            checksum=documento["checksum"],
            ip_address=bitacora.client_ip(request),
        )
        bitacora.record(
            request, Action.BACKUP_CREATE, "backup_records", "",
            {"filename": nombre, "size_bytes": len(contenido),
             "rows": sum(documento["counts"].values())},
        )

        respuesta = HttpResponse(contenido, content_type="application/json")
        respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
        respuesta["X-Backup-Checksum"] = documento["checksum"]
        respuesta["Access-Control-Expose-Headers"] = (
            "Content-Disposition, X-Backup-Checksum"
        )
        return respuesta


class InspectBackupView(APIView):
    """Lee el archivo subido y dice qué contiene. No escribe nada."""

    permission_classes = [IsAuthenticated, CanRestoreBackup]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        documento = _leer_archivo(request)
        if isinstance(documento, Response):
            return documento

        try:
            resumen = services.inspect(documento)
        except services.BackupError as error:
            return Response({"code": error.code, "detail": error.detail},
                            status=status.HTTP_400_BAD_REQUEST)

        organization = getattr(request.user, "organization", None)
        propio = organization is not None and str(
            (resumen["organization"] or {}).get("id")
        ) == str(organization.id)

        return Response({
            **resumen,
            # Lo que la pantalla necesita para decidir si habilita el botón y
            # qué advertencia mostrar antes de habilitarlo.
            "belongs_to_my_organization": propio,
            "labels": {t.key: t.label for t in manifest.TABLES},
        })


class RestoreBackupView(APIView):
    """Reemplaza los datos de la organización con los del archivo."""

    permission_classes = [IsAuthenticated, CanRestoreBackup]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        organization = _organization_or_error(request)
        if isinstance(organization, Response):
            return organization

        if str(request.data.get("confirm", "")).lower() not in ("true", "1"):
            return Response(
                {"code": "confirmacion_requerida",
                 "detail": "La restauración reemplaza todos los datos de la "
                           "organización. Enviá «confirm: true» para "
                           "confirmar que es lo que querés."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        documento = _leer_archivo(request)
        if isinstance(documento, Response):
            return documento

        nombre = getattr(request.FILES.get("file"), "name", "") or ""

        try:
            resultado = services.restore(documento, organization)
        except services.BackupError as error:
            return Response({"code": error.code, "detail": error.detail},
                            status=status.HTTP_400_BAD_REQUEST)

        BackupRecord.objects.create(
            organization=organization,
            kind=BackupRecord.Kind.RESTORE,
            performed_by=request.user,
            filename=nombre,
            row_counts=resultado["written"],
            checksum=documento.get("checksum", ""),
            ip_address=bitacora.client_ip(request),
        )
        # El asiento más importante de esta app. Va con el detalle completo
        # porque una restauración es irreversible y la pregunta que se hace
        # después es siempre la misma: quién, cuándo y con qué archivo.
        bitacora.record(
            request, Action.BACKUP_RESTORE, "backup_records", "",
            {"filename": nombre,
             "generated_at": resultado["generated_at"],
             "deleted": resultado["deleted"],
             "deactivated": resultado["deactivated"],
             "written": resultado["written"],
             "skipped": resultado["skipped"]},
        )

        return Response(resultado)


def _organization_or_error(request):
    """La organización de quien pide, o un 400 explicando que no tiene.

    El Superadministrador de Plataforma cae acá: no pertenece a ninguna
    organización y su alcance no incluye los datos de ninguna, así que no puede
    respaldar ni restaurar una. Para la copia de toda la instalación está
    ``manage.py dump_database``, que es trabajo de consola.
    """
    organization = getattr(request.user, "organization", None)
    if organization is None:
        return Response(
            {"code": "sin_organizacion",
             "detail": "Esta operación es de una organización. El "
                       "superadministrador respalda la instalación completa "
                       "desde la consola, no desde acá."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return organization


def _leer_archivo(request):
    """El documento del respaldo, venga como archivo o como JSON en el cuerpo.

    Se aceptan las dos formas porque la pantalla sube un archivo y las pruebas
    —y quien use la API desde un script— mandan el JSON directo. Un archivo que
    no es JSON válido devuelve 400 con el motivo, y no un 500: subir el archivo
    equivocado es lo más normal del mundo.
    """
    archivo = request.FILES.get("file")
    if archivo is not None:
        if archivo.size > MAX_UPLOAD_BYTES:
            megas = MAX_UPLOAD_BYTES // (1024 * 1024)
            return Response(
                {"code": "archivo_demasiado_grande",
                 "detail": f"El archivo supera los {megas} MB. Restauralo "
                           "desde la consola con «manage.py "
                           "restore_organization»."},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        try:
            return json.loads(archivo.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            return Response(
                {"code": "archivo_ilegible",
                 "detail": f"El archivo no es un JSON válido: {error}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    documento = request.data.get("backup")
    if isinstance(documento, dict):
        return documento

    return Response(
        {"code": "sin_archivo",
         "detail": "Falta el respaldo: subilo en «file» o mandalo en «backup»."},
        status=status.HTTP_400_BAD_REQUEST,
    )
