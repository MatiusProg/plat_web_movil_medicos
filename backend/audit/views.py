"""US-06 (e), (f), (g) y (h) — La consulta de la bitácora.

``ReadOnlyModelViewSet`` y no ``ModelViewSet``: el punto (f) dice que la
bitácora no expone verbos de escritura ni siquiera al administrador. Además se
declara ``http_method_names`` a mano, que es la cerradura que de verdad manda
—un ``@action(methods=["post"])`` agregado más adelante quedaría fuera igual—.
"""

import datetime as dt

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import AuditLog

from .actions import LABELS
from .permissions import CanReadAuditLog
from .serializers import AuditLogSerializer

UUID_REGEX = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, CanReadAuditLog]
    lookup_value_regex = "[0-9]+"
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        """Los asientos de la organización de quien pregunta, del más reciente
        al más antiguo (punto e).

        El filtro por organización es explícito **además** de RLS. No es
        redundancia por gusto: los asientos de plataforma —el alta de la propia
        organización, que escribe US-43— viajan con ``organization`` en NULL, y
        son de otro dueño. RLS ya los oculta; dejarlo escrito acá evita que el
        día que alguien consulte esta tabla desde un comando de gestión, sin
        contexto, la lista salga distinta.
        """
        organization = self.request.user.organization
        if organization is None:
            # El superadministrador no lee la bitácora de ningún inquilino.
            return AuditLog.objects.none()

        queryset = (
            AuditLog.objects
            .filter(organization=organization)
            .select_related("user")
        )

        params = self.request.query_params

        # Punto (e): por actor.
        if actor := params.get("actor"):
            queryset = queryset.filter(user_id=actor)

        # Punto (e): por tipo de acción. Acepta varias separadas por coma para
        # que la pantalla pueda ofrecer "todo lo de contraseñas" sin pedir una
        # consulta por código.
        if accion := params.get("action"):
            codigos = [c.strip() for c in accion.split(",") if c.strip()]
            queryset = queryset.filter(action__in=codigos)

        if entidad := params.get("entity"):
            queryset = queryset.filter(entity=entidad)

        # Punto (e): por rango de fechas. Se comparan fechas y no instantes
        # para que `date_to=2026-09-06` incluya todo ese día, que es lo que
        # espera quien escribe la fecha en un formulario.
        if desde := _fecha(params.get("date_from")):
            queryset = queryset.filter(occurred_at__date__gte=desde)
        if hasta := _fecha(params.get("date_to")):
            queryset = queryset.filter(occurred_at__date__lte=hasta)

        return queryset

    def list(self, request, *args, **kwargs):
        """Igual que el de DRF, pero rechazando una fecha mal escrita.

        Sin esto, ``date_from=ayer`` devuelve la lista completa como si no se
        hubiera filtrado nada, y quien audita concluye que en ese rango no pasó
        nada raro.
        """
        for parametro in ("date_from", "date_to"):
            valor = request.query_params.get(parametro)
            if valor and _fecha(valor) is None:
                return Response(
                    {"code": "fecha_invalida",
                     "detail": f"{parametro} debe ser una fecha ISO (YYYY-MM-DD)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def actions(self, request):
        """El catálogo de acciones, para el desplegable del filtro.

        Devuelve **las que esta organización tiene registradas**, no las 18 del
        catálogo: un desplegable con quince opciones que no devuelven nada no
        ayuda a auditar. Se ordena por etiqueta, que es como se lee.
        """
        codigos = (
            self.get_queryset()
            .order_by()
            .values_list("action", flat=True)
            .distinct()
        )
        catalogo = [
            {"code": codigo, "label": LABELS.get(codigo, codigo)}
            for codigo in codigos
        ]
        return Response(sorted(catalogo, key=lambda item: item["label"]))


def _fecha(valor):
    """La fecha ISO, o ``None`` si no lo es. Acepta también un instante ISO,
    que es lo que manda un selector de fecha y hora."""
    if not valor:
        return None
    try:
        return dt.date.fromisoformat(valor)
    except ValueError:
        pass
    try:
        instante = dt.datetime.fromisoformat(valor)
    except ValueError:
        return None
    if timezone.is_aware(instante):
        instante = timezone.localtime(instante)
    return instante.date()
