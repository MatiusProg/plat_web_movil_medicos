"""Característica general 6 — La API de copias de seguridad y restauración.

    GET  /api/backups/records/    el historial: qué se respaldó y qué se restauró
    GET  /api/backups/policy/     qué permite el plan y cuándo es la próxima copia
    POST /api/backups/create/     genera la copia y la descarga (según el plan)
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
import uuid

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit import services as bitacora
from audit.actions import Action

from . import automatic, manifest, services
from .models import BackupRecord
from .permissions import CanCreateBackup, CanRestoreBackup
from .policy import backup_policy
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
            .select_related("performed_by", "stored")
            .defer("stored__content")
        )

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """Baja una copia automática guardada, descifrada."""
        record = self.get_object()
        try:
            documento = automatic.read(record)
        except services.BackupError as error:
            return Response({"code": error.code, "detail": error.detail},
                            status=status.HTTP_404_NOT_FOUND)

        contenido = services.to_bytes(documento)
        bitacora.record(
            request, Action.BACKUP_DOWNLOAD, "backup_records", str(record.pk),
            {"filename": record.filename, "size_bytes": len(contenido)},
        )
        respuesta = HttpResponse(contenido, content_type="application/json")
        respuesta["Content-Disposition"] = (
            f'attachment; filename="{record.filename}"'
        )
        respuesta["X-Backup-Checksum"] = record.checksum
        respuesta["Access-Control-Expose-Headers"] = (
            "Content-Disposition, X-Backup-Checksum"
        )
        return respuesta


class CreateBackupView(APIView):
    """Genera la copia de la organización y la devuelve como descarga."""

    permission_classes = [IsAuthenticated, CanCreateBackup]

    def post(self, request):
        organization = _organization_or_error(request)
        if isinstance(organization, Response):
            return organization

        # La frecuencia que permite el plan (ver policy.py). 429 y no 403:
        # tiene permiso, lo que no tiene es cuota hasta la fecha que se informa.
        politica = backup_policy(organization)
        if not politica.allowed_now:
            return Response(
                {
                    "detail": _limite(politica),
                    "code": "backup_limit",
                    "next_available_at": politica.next_available_at,
                    "policy": _politica(politica),
                },
                status=(status.HTTP_429_TOO_MANY_REQUESTS if politica.plan_code
                        else status.HTTP_403_FORBIDDEN),
            )

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


class BackupPolicyView(APIView):
    """Qué permite el plan y cuándo se puede generar la próxima copia.

    Es lo que la pantalla muestra junto al botón, para que nadie lo toque y
    se entere recién por el error.
    """

    permission_classes = [IsAuthenticated, CanCreateBackup]

    def get(self, request):
        organization = _organization_or_error(request)
        if isinstance(organization, Response):
            return organization
        return Response(_politica(backup_policy(organization), organization))


def _politica(politica, organization=None):
    datos = {
        "plan_code": politica.plan_code,
        "plan_name": politica.plan_name,
        "interval_hours": politica.interval_hours,
        "last_backup_at": politica.last_backup_at,
        "next_available_at": politica.next_available_at,
        "allowed_now": politica.allowed_now,
        "description": politica.describe(),
    }
    if organization is not None:
        auto = automatic.schedule(organization)
        datos["automatic"] = {
            "enabled": auto.enabled,
            "interval_hours": auto.interval_hours,
            "retention": auto.retention,
            "last_at": auto.last_at,
            "next_at": auto.next_at,
            "description": auto.describe(),
        }
    return datos


def _limite(politica):
    if politica.plan_code is None:
        return politica.describe()
    cuando = timezone.localtime(politica.next_available_at).strftime("%d/%m/%Y %H:%M")
    return f"{politica.describe()} La próxima se puede generar desde el {cuando}."


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

        nombre = _nombre_del_origen(request)

        try:
            resultado = services.restore(documento, organization,
                                         keep_user=request.user)
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
             "kept": resultado["kept"],
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
    record_id = request.data.get("record")
    if record_id:
        record = _copia_guardada(request, record_id)
        if isinstance(record, Response):
            return record
        try:
            return automatic.read(record)
        except services.BackupError as error:
            return Response({"code": error.code, "detail": error.detail},
                            status=status.HTTP_404_NOT_FOUND)

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
         "detail": "Falta el respaldo: subilo en «file», mandalo en «backup» "
                   "o elegí una copia guardada en «record»."},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _copia_guardada(request, record_id):
    """El registro de una copia automática de **la propia** organización.

    El filtro por organización es la segunda cerradura, además de RLS: el id
    de la copia de otro centro médico tiene que dar 404, igual que uno que no
    existe, y no revelar que existe.
    """
    organization = getattr(request.user, "organization", None)
    record = (
        BackupRecord.objects
        .filter(organization=organization, pk=record_id,
                kind=BackupRecord.Kind.BACKUP)
        .first()
        if organization is not None and _es_uuid(record_id) else None
    )
    if record is None:
        return Response(
            {"code": "copia_no_encontrada",
             "detail": "No existe esa copia en tu organización."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return record


def _es_uuid(valor) -> bool:
    try:
        uuid.UUID(str(valor))
    except ValueError:
        return False
    return True


def _nombre_del_origen(request):
    """El nombre que queda en el registro de la restauración."""
    archivo = request.FILES.get("file")
    if archivo is not None:
        return archivo.name or ""
    record_id = request.data.get("record")
    if record_id and _es_uuid(record_id):
        nombre = (
            BackupRecord.objects.filter(pk=record_id)
            .values_list("filename", flat=True).first()
        )
        return nombre or ""
    return ""
