"""US-46 — Las vistas de «mis comprobantes»: interpretar la frase y listar.

Dos pasos, como el reporte por voz del personal:

1. `POST .../interpret/` traduce la frase a una consulta y **la propone**; no
   devuelve datos. Quien habló la ve y confirma.
2. `GET ...` revalida la consulta y devuelve la lista, o el PDF con los QR.

Los dos exigen sesión, `appointments.appointment.read` y **perfil de
paciente**: el personal del centro no usa esta pantalla, y sin perfil no hay
a quién acotar la consulta.
"""

from django.http import HttpResponse
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.permissions import CanReadAppointments
from audit import services as bitacora
from audit.actions import Action
from reporting import exporters

from . import mine, mine_voice
from .permissions import IsPatientProfile


class InterpretSerializer(serializers.Serializer):
    # El tope es el de una frase dictada; una más larga no es una consulta.
    text = serializers.CharField(max_length=300, allow_blank=True, trim_whitespace=True)


class MyReceiptsInterpretView(APIView):
    """`POST /api/payments/mine/receipts/interpret/` — de la frase a la consulta.

    Siempre responde 200 con las mismas claves, aunque no haya entendido nada.
    En la bitácora queda el hecho y lo que se interpretó, **nunca la frase**:
    un pedido hablado puede nombrar a una persona.
    """

    permission_classes = [IsAuthenticated, CanReadAppointments, IsPatientProfile]

    def post(self, request):
        datos = InterpretSerializer(data=request.data)
        datos.is_valid(raise_exception=True)

        resultado = mine_voice.interpretar_consulta(
            datos.validated_data["text"], request.user,
        )
        consulta = resultado["consulta"] or {}
        bitacora.record(
            request, Action.PATIENT_VOICE_QUERY, "payments", "",
            {
                "understood": resultado["understood"],
                "tipo": consulta.get("tipo"),
                "filtros": sum(
                    consulta.get(c) is not None
                    for c in ("cantidad", "desde", "hasta", "especialidad")
                ),
                "agrupar": consulta.get("agrupar"),
                "generated_by": resultado["generated_by"],
            },
        )
        return Response(resultado)


class MyReceiptsView(APIView):
    """`GET /api/payments/mine/receipts/` — la lista, o el PDF con los QR.

    `?tipo=pagos|fichas&cantidad=&desde=&hasta=&especialidad=&agrupar=&formato=`
    (`agrupar` es `mes`, `sucursal` o `especialidad`; `formato`, `json` o
    `pdf`). El parámetro se llama `formato` y no `format` porque DRF reserva
    `?format=` para elegir el renderizador y respondería 404.

    Agrupar es solo cómo se presenta: `items` sigue siendo la lista completa y
    `groups` la reparte, con el total de cada grupo. El PDF abre cada grupo con
    una fila de encabezado.
    """

    permission_classes = [IsAuthenticated, CanReadAppointments, IsPatientProfile]

    def get(self, request):
        consulta, errores = mine.parse_consulta(
            request.query_params, request.user.organization,
        )
        formato = request.query_params.get("formato") or "json"
        if formato not in mine.FORMATOS:
            errores = {**errores, "formato": ["Tiene que ser «json» o «pdf»."]}
        if errores:
            return Response(
                {"code": "consulta_invalida",
                 "detail": "La consulta no es válida.", "errors": errores},
                status=status.HTTP_400_BAD_REQUEST,
            )

        titular = request.user.patient_profile
        objetos, truncado = mine.listar(request.user, consulta)
        items = [mine.serializar(o, consulta.tipo, titular) for o in objetos]
        grupos = mine.agrupar_items(items, consulta.agrupar)
        resumen = mine_voice.resumen(self._como_dict(consulta))

        if formato == "pdf":
            return self._pdf(request, consulta, items, grupos, truncado, resumen)

        return Response({
            "tipo": consulta.tipo, "count": len(items),
            "limit": consulta.limite, "truncated": truncado,
            "summary": resumen, "agrupar": consulta.agrupar,
            "groups": grupos, "items": items,
        })

    @staticmethod
    def _como_dict(consulta):
        """La consulta en la forma que lee `mine_voice.resumen`."""
        from catalog.models import Specialty

        nombre = None
        if consulta.especialidad:
            nombre = (Specialty.objects.filter(id=consulta.especialidad)
                      .values_list("name", flat=True).first())
        return {
            "tipo": consulta.tipo, "cantidad": consulta.cantidad,
            "desde": consulta.desde.isoformat() if consulta.desde else None,
            "hasta": consulta.hasta.isoformat() if consulta.hasta else None,
            "especialidad_nombre": nombre, "agrupar": consulta.agrupar,
        }

    @staticmethod
    def _pdf(request, consulta, items, grupos, truncado, resumen):
        contenido, mime, nombre = exporters.export(
            "pdf", mine.ENCABEZADOS_PDF, mine.filas_del_pdf(items, grupos),
            mine.titulo_del_pdf(consulta), subtitle=resumen, truncated=truncado,
        )
        bitacora.record(
            request, Action.PATIENT_RECEIPTS_EXPORT, "payments", "",
            {"tipo": consulta.tipo, "rows": len(items),
             "filtros": consulta.filtros, "agrupar": consulta.agrupar},
        )
        respuesta = HttpResponse(contenido, content_type=mime)
        respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
        # El navegador necesita verlas para leerlas desde `fetch`.
        respuesta["X-Report-Rows"] = str(len(items))
        respuesta["X-Report-Truncated"] = "1" if truncado else "0"
        respuesta["Access-Control-Expose-Headers"] = (
            "Content-Disposition, X-Report-Rows, X-Report-Truncated"
        )
        return respuesta
