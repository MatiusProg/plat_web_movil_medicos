"""US-08 — Antecedentes del paciente: alergias, condiciones y medicación.

**Cambio de alcance respecto del documento, acordado en el reparto.** La
historia figura como WEB/MÓVIL, pero el actor es el paciente o su titular, y el
paciente no usa la aplicación web. La mitad web se reduce al **endpoint de
lectura** (``highlights/``) que el módulo de atención consumirá en el Sprint 3
para mostrar los antecedentes destacados al abrir la consulta. No hay pantalla
web, y no es un recorte por falta de tiempo: sería una pantalla que ningún
usuario del sistema abriría.

Quién alcanza qué, que es el punto (g):

    el propio paciente        lee y escribe los suyos
    su titular                lee y escribe los del dependiente a su cargo
    un profesional            **sólo lee**, y la lectura queda en la bitácora
    cualquier otro            no existe el paciente, a efectos de este endpoint

La lectura del profesional se audita y la del paciente no, y es deliberado: una
fila de bitácora cada vez que alguien abre su propia pantalla convertiría la
bitácora en un registro de navegación, y el asiento que interesa —quién de
afuera miró la ficha de quién— quedaría enterrado entre miles.
"""

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit import services as bitacora
from audit.actions import Action
from catalog.models import Practitioner

from .dependents import titular_de
from .models import Patient, PatientHistoryEntry
from .permissions import CanReadHistory, CanWriteHistory

UUID_REGEX = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

# Los dos alcances posibles sobre la ficha de otro.
OWN = "own"
PROFESSIONAL = "professional"


def scope_over(user, patient):
    """Qué alcance tiene ``user`` sobre los antecedentes de ``patient``.

    Devuelve ``OWN``, ``PROFESSIONAL`` o ``None``. El orden importa: un médico
    que además es paciente del mismo centro médico tiene alcance propio sobre su
    ficha, y no queremos que su propia consulta le quede auditada como si
    hubiera espiado a un tercero.
    """
    if patient is None:
        return None

    if patient.user_id == user.id:
        return OWN

    # El titular tiene sobre su dependiente el mismo alcance que sobre sí mismo.
    # Es el punto (d) de US-07, y es la razón por la que aquella historia exige
    # confirmar el vínculo con los datos coincidiendo.
    if patient.guardian_id is not None:
        titular = titular_de(user)
        if titular is not None and patient.guardian_id == titular.id:
            return OWN

    # **El permiso no alcanza para decidir esto.** ``patients.history.read`` lo
    # llevan las dos plantillas que leen antecedentes: el Médico, para verlos al
    # abrir la consulta, y el Paciente, para ver los suyos. Si bastara con
    # tenerlo, cualquier paciente podría leer los antecedentes de cualquier otro
    # de su centro médico — RLS no separa ahí, porque los dos son del mismo
    # inquilino—. Lo descubrió `test_un_paciente_no_ve_los_antecedentes_de_su_vecino`.
    #
    # Lo que sí distingue es estar en el catálogo de profesionales: quien
    # atiende pacientes tiene ficha de profesional (US-12), y quien no, no.
    if user.has_permission("patients.history.read") and _es_profesional(user):
        return PROFESSIONAL

    return None


def _es_profesional(user):
    """¿Tiene ficha de profesional activa en el catálogo?

    Es una consulta por petición y no un claim del token a propósito: dar de
    baja a un profesional (US-12 e) tiene que cortarle el acceso a los
    antecedentes en ese momento, no cuando venza su token.
    """
    return Practitioner.objects.filter(user=user, is_active=True).exists()


class HistoryEntrySerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    severity_label = serializers.CharField(
        source="get_severity_display", read_only=True,
    )

    class Meta:
        model = PatientHistoryEntry
        fields = [
            "id",
            "patient",
            "kind",
            "kind_label",
            "description",
            "severity",
            "severity_label",
            "source",
            "recorded_at",
            "is_active",
        ]
        # `source` es de sólo lectura a propósito (punto d): en el Sprint 1 todo
        # lo que entra por acá es declarado por el paciente, y dejar que el
        # cliente lo mandara permitiría que un antecedente se hiciera pasar por
        # registrado por un profesional.
        #
        # `patient` también, aunque el cliente sí lo manda: lo lee la vista, que
        # comprueba con `scope_over` que sea el propio o uno a cargo. Si además
        # fuera un campo escribible, el serializer aceptaría cualquier uuid de la
        # organización y habría dos caminos hasta la misma columna, uno con
        # control y otro sin.
        read_only_fields = ["id", "patient", "source", "recorded_at", "is_active"]

    def validate(self, attrs):
        """Punto (b): la severidad es de las alergias y de nadie más.

        La base lo rechaza igual con `ck_history_severity`, pero un 400 con el
        campo señalado se puede dibujar debajo del input; un error de integridad
        es un 500.
        """
        instancia = self.instance
        kind = attrs.get("kind", getattr(instancia, "kind", None))
        severity = attrs.get("severity", getattr(instancia, "severity", ""))

        if kind != PatientHistoryEntry.Kind.ALLERGY and severity:
            raise serializers.ValidationError({
                "severity": "La severidad se registra sólo en las alergias.",
            })
        if kind == PatientHistoryEntry.Kind.ALLERGY and not severity:
            raise serializers.ValidationError({
                "severity": "Indicá la severidad de la alergia.",
            })
        return attrs


class PatientHistoryViewSet(viewsets.ModelViewSet):
    """`/api/patients/history/` — los antecedentes de un paciente."""

    serializer_class = HistoryEntrySerializer
    lookup_value_regex = UUID_REGEX
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    permission_classes_by_action = {
        "list": [CanReadHistory],
        "retrieve": [CanReadHistory],
        "highlights": [CanReadHistory],
        "create": [CanWriteHistory],
        "partial_update": [CanWriteHistory],
        "destroy": [CanWriteHistory],
    }

    def get_permissions(self):
        clases = self.permission_classes_by_action.get(
            self.action, [CanReadHistory],
        )
        return [IsAuthenticated()] + [clase() for clase in clases]

    # ---------- Resolución del paciente ---------------------------------

    def _paciente_pedido(self, patient_id=None):
        """El paciente sobre el que se trabaja, y el alcance sobre él.

        Sin ``patient`` en la petición se asume la ficha de quien pregunta, que
        es el caso más común desde el móvil.
        """
        user = self.request.user
        if patient_id:
            paciente = Patient.objects.filter(id=patient_id).first()
        else:
            paciente = titular_de(user)

        return paciente, scope_over(user, paciente)

    def get_queryset(self):
        # En las acciones de detalle no hay `?patient=`: el paciente sale de la
        # propia entrada. RLS ya acota a la organización y `scope_over` decide
        # después si esta persona puede tocarla — el filtro por paciente acá
        # haría que abrir el antecedente de un dependiente diera 404.
        if self.detail:
            return PatientHistoryEntry.objects.select_related("patient")

        paciente, alcance = self._paciente_pedido(
            self.request.query_params.get("patient"),
        )
        if alcance is None:
            return PatientHistoryEntry.objects.none()

        queryset = PatientHistoryEntry.objects.filter(patient=paciente)

        # Por omisión sólo lo vigente (punto e): lo dado de baja no se pierde,
        # pero tampoco es lo que se muestra.
        if self.request.query_params.get("include_inactive") not in {"true", "1"}:
            queryset = queryset.filter(is_active=True)

        if kind := self.request.query_params.get("kind"):
            queryset = queryset.filter(kind=kind)

        return queryset

    # ---------- Lectura --------------------------------------------------

    def list(self, request, *args, **kwargs):
        paciente, alcance = self._paciente_pedido(
            request.query_params.get("patient"),
        )
        if alcance is None:
            return _sin_alcance(paciente)

        if alcance == PROFESSIONAL:
            _auditar_lectura(request, paciente, origen="listado")

        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        entrada = self.get_object()
        alcance = scope_over(request.user, entrada.patient)
        if alcance is None:
            return _sin_alcance(entrada.patient)
        if alcance == PROFESSIONAL:
            _auditar_lectura(request, entrada.patient, origen="detalle")
        return Response(self.get_serializer(entrada).data)

    @action(detail=False, methods=["get"])
    def highlights(self, request):
        """`GET .../history/highlights/?patient=<id>` — el conjunto vigente.

        Es la mitad web de la historia (punto f): lo que el módulo de atención
        del Sprint 3 muestra destacado al abrir la consulta. Devuelve los tres
        tipos ya agrupados, porque así es como se dibuja, y con las alergias
        primero —ordenadas de más grave a menos— que es el dato que cambia una
        receta.

        No pagina: son los antecedentes vigentes de una persona, no un listado.
        Paginarlos escondería una alergia anafiláctica en la página dos.
        """
        paciente, alcance = self._paciente_pedido(
            request.query_params.get("patient"),
        )
        if alcance is None:
            return _sin_alcance(paciente)

        if alcance == PROFESSIONAL:
            _auditar_lectura(request, paciente, origen="destacados")

        vigentes = PatientHistoryEntry.objects.filter(
            patient=paciente, is_active=True,
        )

        # De más grave a menos. `severity` es texto, así que el orden no sale
        # solo: se ordena en Python sobre una lista que nunca pasa de unas
        # pocas filas.
        gravedad = {"anaphylactic": 0, "severe": 1, "moderate": 2, "mild": 3}
        alergias = sorted(
            [e for e in vigentes if e.kind == PatientHistoryEntry.Kind.ALLERGY],
            key=lambda e: gravedad.get(e.severity, 9),
        )

        def de_tipo(kind):
            return [e for e in vigentes if e.kind == kind]

        return Response({
            "patient": {
                "id": str(paciente.id),
                "full_name": paciente.full_name,
            },
            "allergies": HistoryEntrySerializer(alergias, many=True).data,
            "conditions": HistoryEntrySerializer(
                de_tipo(PatientHistoryEntry.Kind.CONDITION), many=True,
            ).data,
            "medications": HistoryEntrySerializer(
                de_tipo(PatientHistoryEntry.Kind.MEDICATION), many=True,
            ).data,
            # Punto (d), dicho en la respuesta y no sólo en la documentación: lo
            # que llega acá lo declaró el paciente. Quien dibuje la pantalla del
            # Sprint 3 tiene que poder marcarlo sin ir a leer esta historia.
            "self_reported": True,
        })

    # ---------- Escritura -------------------------------------------------

    def create(self, request, *args, **kwargs):
        """Punto (c): sobre uno mismo o sobre un dependiente, misma pantalla.

        El paciente viene en el cuerpo porque lo elige el selector compartido de
        US-07. Que venga del cliente no lo hace inseguro: `scope_over` comprueba
        que sea el propio o uno a cargo, que es lo mismo que comprobaría si
        viniera por otro lado.
        """
        paciente, alcance = self._paciente_pedido(request.data.get("patient"))
        if alcance is None:
            return _sin_alcance(paciente)
        if alcance != OWN:
            return Response(
                {"code": "solo_lectura",
                 "detail": "Un profesional no registra antecedentes declarados "
                           "por el paciente."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entrada = serializer.save(
            organization=paciente.organization,
            patient=paciente,
            declared_by=request.user,
            source=PatientHistoryEntry.Source.SELF_REPORTED,
        )
        return Response(
            self.get_serializer(entrada).data, status=status.HTTP_201_CREATED,
        )

    def _solo_el_propio(self):
        """Punto (e): editar y dar de baja es del paciente, no del profesional."""
        entrada = self.get_object()
        if scope_over(self.request.user, entrada.patient) != OWN:
            return None, Response(
                {"code": "solo_lectura",
                 "detail": "Sólo el paciente o su titular pueden cambiar lo "
                           "que declararon."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return entrada, None

    def partial_update(self, request, *args, **kwargs):
        entrada, error = self._solo_el_propio()
        if error is not None:
            return error

        serializer = self.get_serializer(entrada, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Baja lógica. El histórico de lo declarado no se pierde: deja de
        estar vigente. Alguien que dejó de ser alérgico sigue habiéndolo sido, y
        el módulo de atención tiene que poder verlo."""
        entrada, error = self._solo_el_propio()
        if error is not None:
            return error

        entrada.is_active = False
        entrada.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


def _auditar_lectura(request, paciente, origen):
    """Punto (g): toda lectura por parte de un profesional queda registrada."""
    bitacora.record(
        request,
        action=Action.HISTORY_READ,
        entity="patient_history_entries",
        entity_id=paciente.id,
        detail={"patient": paciente.full_name, "origen": origen},
    )


def _sin_alcance(paciente):
    """404 y no 403, a propósito.

    Un 403 confirmaría que ese paciente existe en este centro médico. Con un
    404 quien prueba identificadores no aprende nada: la respuesta es la misma
    para un paciente que no existe y para uno que no le corresponde.
    """
    return Response(
        {"code": "paciente_no_encontrado",
         "detail": "No encontramos a esa persona."},
        status=status.HTTP_404_NOT_FOUND,
    )
