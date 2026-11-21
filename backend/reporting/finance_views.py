"""US-50 — Las vistas de la contabilidad.

    GET    /api/reporting/finance/summary/      tarjetas, grupos y comparación
    GET    /api/reporting/finance/series/       los últimos 6 meses
    GET    /api/reporting/finance/export/       la tabla en CSV, Excel o PDF
    POST   /api/reporting/finance/interpret/    de la frase a la cifra
    GET    /api/reporting/finance/expenses/     los gastos del rango
    POST   /api/reporting/finance/expenses/     cargar un gasto
    PATCH  /api/reporting/finance/expenses/{id}/
    DELETE /api/reporting/finance/expenses/{id}/
    GET    /api/reporting/finance/settings/     la comisión de la pasarela
    PUT    /api/reporting/finance/settings/

Todas exigen el permiso ``finance.accounting.read`` (los gastos y la comisión,
además ``finance.expense.manage`` para escribir) y que el plan incluya
``accounting``. El cálculo es de ``finance.py``.
"""

import datetime as dt
import uuid
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit import services as bitacora
from audit.actions import Action
from catalog.models import Practitioner
from tenancy.plans import require_feature

from . import exporters, finance, finance_voice
from .kpi_views import filtros
from .models import Expense
from .permissions import CanManageExpenses, CanReadAccounting

FEATURE = "accounting"
FEATURE_TEXT = "la contabilidad"
FORMATOS = ("csv", "xlsx", "pdf")


def _organizacion(request):
    organizacion = getattr(request.user, "organization", None)
    if organizacion is not None:
        require_feature(organizacion, FEATURE, FEATURE_TEXT)
    return organizacion


def _error(code, detail):
    return Response({"code": code, "detail": detail}, status=status.HTTP_400_BAD_REQUEST)


def _consulta(request, organizacion):
    """``(desde, hasta, filtros_de_calcular, agrupar)`` o la ``Response`` de error."""
    rango = filtros(request, organizacion)
    if isinstance(rango, Response):
        return rango
    desde, hasta, branch_id = rango

    practitioner_id = request.query_params.get("practitioner") or None
    if practitioner_id:
        try:
            practitioner_id = uuid.UUID(practitioner_id)
        except ValueError:
            return _error("invalid_practitioner", "El profesional no es válido.")
        if not Practitioner.objects.filter(
            organization=organizacion, pk=practitioner_id,
        ).exists():
            return _error("invalid_practitioner",
                          "El profesional no existe en esta organización.")

    agrupar = request.query_params.get("group") or None
    if agrupar and agrupar not in finance.AGRUPACIONES:
        return _error("invalid_group",
                      "Agrupa por: " + ", ".join(finance.AGRUPACIONES) + ".")
    return desde, hasta, {"branch_id": branch_id, "practitioner_id": practitioner_id}, agrupar


def _quiere_comparar(request) -> bool:
    return request.query_params.get("compare") in ("1", "true")


class SummaryView(APIView):
    """``GET .../finance/summary/?from=&to=&branch=&practitioner=&group=&compare=1``."""

    permission_classes = [IsAuthenticated, CanReadAccounting]

    def get(self, request):
        organizacion = _organizacion(request)
        if organizacion is None:
            return Response({"plataforma": True})
        consulta = _consulta(request, organizacion)
        if isinstance(consulta, Response):
            return consulta
        desde, hasta, filtros_, agrupar = consulta
        comparar = _quiere_comparar(request)
        calcular = finance.con_comparacion if comparar else finance.calcular
        datos = calcular(organizacion, desde, hasta, agrupar=agrupar, **filtros_)
        bitacora.record(
            request, Action.FINANCE_QUERY, "finance", "",
            {"agrupar": agrupar, "comparar": comparar,
             "from": desde.isoformat(), "to": hasta.isoformat()},
        )
        return Response(datos)


class SeriesView(APIView):
    """``GET .../finance/series/?branch=&practitioner=``: 6 meses, mes a mes."""

    permission_classes = [IsAuthenticated, CanReadAccounting]

    def get(self, request):
        organizacion = _organizacion(request)
        if organizacion is None:
            return Response({"plataforma": True})
        consulta = _consulta(request, organizacion)
        if isinstance(consulta, Response):
            return consulta
        _, _, filtros_, _ = consulta
        tz = ZoneInfo(organizacion.timezone or "America/La_Paz")
        hoy = timezone.now().astimezone(tz).date()
        return Response(finance.serie_de_meses(organizacion, hoy, **filtros_))


class InterpretSerializer(serializers.Serializer):
    # El tope es el de una frase dictada; una más larga no es una consulta.
    text = serializers.CharField(max_length=300, allow_blank=True, trim_whitespace=True)


class InterpretView(APIView):
    """``POST .../finance/interpret/``: la frase, la cifra y una frase de respuesta.

    Siempre 200 con las mismas claves. En la bitácora queda qué se consultó
    (métrica y agrupación), **nunca la frase**: puede nombrar a un profesional.
    """

    permission_classes = [IsAuthenticated, CanReadAccounting]

    def post(self, request):
        organizacion = _organizacion(request)
        if organizacion is None:
            return Response({"plataforma": True})
        datos = InterpretSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        respuesta = finance_voice.interpretar(datos.validated_data["text"], request.user)
        consulta = respuesta["query"] or {}
        bitacora.record(
            request, Action.FINANCE_QUERY, "finance", "",
            {"voz": True, "entendida": respuesta["understood"],
             "metrica": consulta.get("metrica"), "agrupar": consulta.get("agrupar"),
             "comparar": consulta.get("comparar"),
             "generated_by": respuesta["generated_by"]},
        )
        return Response(respuesta)


ENCABEZADOS = ["Grupo", "Moneda", "Ingresos", "Devoluciones", "Comisión",
               "Honorarios", "Gastos", "Utilidad", "Pagos"]


def _fila(etiqueta, moneda, valores):
    return [etiqueta, moneda, valores["ingresos"], valores["devoluciones"],
            valores["comision"], valores["honorarios"], valores["gastos"],
            valores["utilidad"], valores["pagos"]]


def filas_del_archivo(datos: dict):
    """Las filas de la tabla exportada: grupos y, al final de cada moneda, el total."""
    filas = []
    for moneda in datos["currencies"]:
        if datos["group_by"]:
            titulo = f"{moneda['currency']} · por {datos['group_by']}"
            filas.append(exporters.FilaDeGrupo([titulo] + [""] * (len(ENCABEZADOS) - 1)))
            filas.extend(_fila(g["label"], moneda["currency"], g) for g in moneda["groups"])
        filas.append(_fila("Total", moneda["currency"], moneda["totals"]))
    return filas


class ExportView(APIView):
    """``GET .../finance/export/?file=csv|xlsx|pdf`` + los mismos filtros."""

    permission_classes = [IsAuthenticated, CanReadAccounting]

    def get(self, request):
        organizacion = _organizacion(request)
        if organizacion is None:
            return Response({"plataforma": True})
        formato = request.query_params.get("file", "pdf")
        if formato not in FORMATOS:
            return _error("invalid_format", "El formato es csv, xlsx o pdf.")
        consulta = _consulta(request, organizacion)
        if isinstance(consulta, Response):
            return consulta
        desde, hasta, filtros_, agrupar = consulta
        datos = finance.calcular(organizacion, desde, hasta, agrupar=agrupar, **filtros_)
        filas = filas_del_archivo(datos)
        contenido, mime, nombre = exporters.export(
            formato, ENCABEZADOS, filas, "Contabilidad",
            subtitle=f"Del {desde:%d/%m/%Y} al {hasta:%d/%m/%Y}",
        )
        bitacora.record(
            request, Action.FINANCE_EXPORT, "finance", "",
            {"format": formato, "agrupar": agrupar, "rows": len(filas)},
        )
        respuesta = HttpResponse(contenido, content_type=mime)
        respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
        respuesta["Access-Control-Expose-Headers"] = "Content-Disposition"
        return respuesta


# ==========================================================================
#  Gastos
# ==========================================================================
class ExpenseSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True, default=None)
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Expense
        fields = ["id", "branch", "branch_name", "category", "category_label",
                  "amount", "currency", "spent_on", "note", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("El monto tiene que ser mayor a cero.")
        return value

    def validate_currency(self, value):
        valor = (value or "").strip().upper()
        if len(valor) != 3 or not valor.isalpha():
            raise serializers.ValidationError("La moneda es un código de 3 letras, como BOB.")
        return valor

    def validate_branch(self, value):
        organizacion = self.context["request"].user.organization
        if value is not None and value.organization_id != organizacion.id:
            raise serializers.ValidationError("La sucursal no existe en esta organización.")
        return value

    def validate_spent_on(self, value):
        # Un gasto de hace años o de más de un año adelante es un error de tipeo.
        hoy = timezone.localdate()
        if value.year < hoy.year - 5 or value > hoy + dt.timedelta(days=366):
            raise serializers.ValidationError("La fecha del gasto no es razonable.")
        return value


class ExpenseListView(APIView):
    permission_classes = [IsAuthenticated, CanReadAccounting]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), CanManageExpenses()]
        return super().get_permissions()

    def get(self, request):
        organizacion = _organizacion(request)
        if organizacion is None:
            return Response({"plataforma": True})
        rango = filtros(request, organizacion)
        if isinstance(rango, Response):
            return rango
        desde, hasta, branch_id = rango
        gastos = Expense.objects.filter(
            organization=organizacion, spent_on__gte=desde, spent_on__lte=hasta,
        ).select_related("branch")
        if branch_id:
            gastos = gastos.filter(branch_id=branch_id)
        categoria = request.query_params.get("category")
        if categoria:
            gastos = gastos.filter(category=categoria)
        return Response(ExpenseSerializer(gastos, many=True).data)

    def post(self, request):
        organizacion = _organizacion(request)
        if organizacion is None:
            return Response({"plataforma": True})
        datos = ExpenseSerializer(data=request.data, context={"request": request})
        datos.is_valid(raise_exception=True)
        gasto = datos.save(organization=organizacion, created_by=request.user)
        bitacora.record(
            request, Action.FINANCE_EXPENSE_CREATE, "expense", gasto.id,
            {"category": gasto.category, "currency": gasto.currency},
        )
        return Response(ExpenseSerializer(gasto).data, status=status.HTTP_201_CREATED)


class ExpenseDetailView(APIView):
    permission_classes = [IsAuthenticated, CanManageExpenses]

    def _gasto(self, request, pk):
        organizacion = _organizacion(request)
        if organizacion is None:
            return None
        return Expense.objects.filter(organization=organizacion, pk=pk).first()

    def patch(self, request, pk):
        gasto = self._gasto(request, pk)
        if gasto is None:
            return Response({"code": "not_found", "detail": "El gasto no existe."},
                            status=status.HTTP_404_NOT_FOUND)
        datos = ExpenseSerializer(gasto, data=request.data, partial=True,
                                  context={"request": request})
        datos.is_valid(raise_exception=True)
        gasto = datos.save()
        bitacora.record(
            request, Action.FINANCE_EXPENSE_UPDATE, "expense", gasto.id,
            {"category": gasto.category},
        )
        return Response(ExpenseSerializer(gasto).data)

    def delete(self, request, pk):
        gasto = self._gasto(request, pk)
        if gasto is None:
            return Response({"code": "not_found", "detail": "El gasto no existe."},
                            status=status.HTTP_404_NOT_FOUND)
        gasto_id = gasto.id
        gasto.delete()
        bitacora.record(request, Action.FINANCE_EXPENSE_DELETE, "expense", gasto_id, {})
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==========================================================================
#  Comisión de la pasarela
# ==========================================================================
class SettingsSerializer(serializers.Serializer):
    stripe_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, max_value=100,
    )


class SettingsView(APIView):
    permission_classes = [IsAuthenticated, CanReadAccounting]

    def get_permissions(self):
        if self.request.method == "PUT":
            return [IsAuthenticated(), CanManageExpenses()]
        return super().get_permissions()

    def get(self, request):
        organizacion = _organizacion(request)
        if organizacion is None:
            return Response({"plataforma": True})
        ajustes = finance.ajustes_de(organizacion)
        return Response({"stripe_percent": str(finance.redondear(Decimal(ajustes.stripe_percent)))})

    def put(self, request):
        organizacion = _organizacion(request)
        if organizacion is None:
            return Response({"plataforma": True})
        datos = SettingsSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        ajustes = finance.ajustes_de(organizacion)
        ajustes.stripe_percent = datos.validated_data["stripe_percent"]
        ajustes.save(update_fields=["stripe_percent", "updated_at"])
        bitacora.record(
            request, Action.FINANCE_SETTINGS_UPDATE, "finance", "",
            {"stripe_percent": str(finance.redondear(Decimal(ajustes.stripe_percent)))},
        )
        return Response({"stripe_percent": str(finance.redondear(Decimal(ajustes.stripe_percent)))})
