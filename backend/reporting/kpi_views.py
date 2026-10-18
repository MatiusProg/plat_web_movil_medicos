"""US-29 — ``GET /api/reporting/kpis/?from=&to=&branch=``: el panel de KPIs.

Ocupación de agenda, inasistencia, demanda por sucursal y especialidad, e
ingresos por fichas. Las definiciones y el contrato están en
``docs/sprints/sprint-3/us-29-indicadores.md``; el cálculo, en
``appointments/kpis.py``, que es lo que también reutiliza US-30.

Sin ``from`` y ``to`` el rango son los últimos 30 días. El administrador ve su
organización y nada más: RLS lo garantiza, y ``calcular`` además filtra por
``organization`` de forma explícita.
"""

import datetime as dt
import uuid
from zoneinfo import ZoneInfo

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments import kpis
from catalog.models import Branch

from .permissions import CanReadKpis

DIAS_POR_DEFECTO = 30


def _error(code, detail):
    return Response({"code": code, "detail": detail}, status=status.HTTP_400_BAD_REQUEST)


def _fecha(valor):
    try:
        return dt.date.fromisoformat(valor)
    except ValueError:
        return None


class KpiView(APIView):
    permission_classes = [IsAuthenticated, CanReadKpis]

    def get(self, request):
        organizacion = getattr(request.user, "organization", None)
        if organizacion is None:
            return Response({"plataforma": True})

        tz = ZoneInfo(organizacion.timezone or "America/La_Paz")
        hoy = timezone.now().astimezone(tz).date()
        crudo_desde = request.query_params.get("from")
        crudo_hasta = request.query_params.get("to")
        hasta = _fecha(crudo_hasta) if crudo_hasta else hoy
        desde = (
            _fecha(crudo_desde) if crudo_desde
            else hasta - dt.timedelta(days=DIAS_POR_DEFECTO - 1) if hasta else None
        )
        if desde is None or hasta is None:
            return _error("invalid_date", "Las fechas deben tener el formato AAAA-MM-DD.")
        if hasta < desde:
            return _error("invalid_range", "El rango de fechas está invertido.")
        if (hasta - desde).days >= kpis.MAX_DIAS:
            return _error("range_too_long", f"El rango no puede superar {kpis.MAX_DIAS} días.")

        branch_id = request.query_params.get("branch") or None
        if branch_id:
            try:
                branch_id = uuid.UUID(branch_id)
            except ValueError:
                return _error("invalid_branch", "La sucursal no es válida.")
            if not Branch.objects.filter(organization=organizacion, pk=branch_id).exists():
                return _error("invalid_branch", "La sucursal no existe en esta organización.")

        return Response(kpis.calcular(organizacion, desde, hasta, branch_id))
