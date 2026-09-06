"""US-07 — Pacientes dependientes: los familiares a cargo de un titular.

**La distinción que hace posible el caso:** un dependiente es un paciente del
catálogo, no un usuario que inicia sesión. Se le crea la ficha demográfica y
nada más — sin correo, sin contraseña, sin fila en ``users``. Si el dependiente
tuviera que ser un usuario, un recién nacido necesitaría una cuenta de correo
para poder ser atendido.

**De quién son los dependientes se resuelve desde el token, nunca desde un
identificador que mande el cliente.** Es la misma regla que US-05 aplica al
perfil, y acá pesa más: un ``guardian_id`` en el cuerpo de la petición
convertiría este endpoint en una forma de colgarse de la ficha de cualquiera y
leerle el historial.

Lo que exporta para las demás historias es ``patient_options`` — el selector de
*"¿para quién es esta ficha?"*—, que US-08 usa en este sprint y la reserva del
Sprint 2 volverá a usar. Está publicado a propósito, no es una parte privada de
la pantalla de dependientes.
"""

import datetime as dt
import unicodedata

from django.conf import settings
from django.db import transaction
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Role, User, UserRole
from audit import services as bitacora
from audit.actions import Action

from .models import Patient
from .permissions import CanReadDependents, CanWriteDependents

UUID_REGEX = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


# --------------------------------------------------------------------------
#  Ayudas
# --------------------------------------------------------------------------

def normalizar(texto: str) -> str:
    """Sin tildes, sin mayúsculas y sin espacios de más.

    Se usa para comparar nombres al vincular una ficha que ya existe, donde
    "José" y "Jose" tienen que dar lo mismo: quien vincula está tipeando de
    memoria el nombre de un familiar, no copiándolo de un registro.
    """
    plano = unicodedata.normalize("NFKD", texto or "")
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    return " ".join(plano.lower().split())


def edad_en_anios(birth_date, hoy=None):
    if birth_date is None:
        return None
    hoy = hoy or dt.date.today()
    return (
        hoy.year - birth_date.year
        - ((hoy.month, hoy.day) < (birth_date.month, birth_date.day))
    )


def titular_de(user):
    """La ficha de paciente de quien hace la petición, o ``None``.

    Un administrador tiene cuenta pero no ficha: para él, "mis dependientes" no
    significa nada, y el endpoint lo dice en vez de devolver una lista vacía
    que parecería un problema de datos.
    """
    return Patient.objects.filter(user=user, is_active=True).first()


# --------------------------------------------------------------------------
#  Serializers
# --------------------------------------------------------------------------

class DependentSerializer(serializers.ModelSerializer):
    """La ficha de un dependiente. Punto (a).

    ``document_number`` es opcional porque un recién nacido todavía no tiene
    documento — es la restricción ``ck_patient_doc_or_guardian`` del modelo, que
    admite ficha sin documento **si** hay un titular que responda por ella.
    """

    age = serializers.SerializerMethodField()
    relationship_label = serializers.CharField(
        source="get_relationship_display", read_only=True,
    )

    class Meta:
        model = Patient
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "document_type",
            "document_number",
            "birth_date",
            "age",
            "sex",
            "phone",
            "relationship",
            "relationship_label",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "full_name", "is_active", "created_at"]
        extra_kwargs = {
            "relationship": {"required": True, "allow_blank": False},
            "document_number": {"required": False, "allow_null": True},
        }

    def get_age(self, patient):
        return edad_en_anios(patient.birth_date)


class DependentCreateSerializer(DependentSerializer):
    """El alta, con la confirmación de vínculo del punto (c).

    Cuando el documento ya existe en la organización, el alta se rechaza y se
    ofrece vincular la ficha existente en vez de duplicarla. Confirmar exige
    reenviar la misma petición con ``confirm_link``.
    """

    confirm_link = serializers.BooleanField(write_only=True, default=False)

    class Meta(DependentSerializer.Meta):
        fields = DependentSerializer.Meta.fields + ["confirm_link"]


class PromotionSerializer(serializers.Serializer):
    """El paso a titular del punto (f): la cuenta de acceso que no tenía."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirmation = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirmation"):
            raise serializers.ValidationError({
                "password_confirmation": "Las contraseñas no coinciden.",
            })
        return attrs


class PatientOptionSerializer(serializers.Serializer):
    """Una opción del selector de *"¿para quién es esta ficha?"*."""

    id = serializers.UUIDField()
    full_name = serializers.CharField()
    relationship = serializers.CharField()
    relationship_label = serializers.CharField()
    is_self = serializers.BooleanField()
    birth_date = serializers.DateField(allow_null=True)


def patient_options(user):
    """El titular y sus dependientes, en el orden en que se muestran.

    **Widget compartido, no parte privada de esta pantalla.** Lo consume US-08
    para elegir de quién son los antecedentes, y la reserva del Sprint 2 para
    elegir de quién es la ficha. Que la lista se arme en un solo lugar es lo que
    evita que dentro de dos sprints haya tres versiones distintas de "para
    quién", cada una con su propio criterio sobre qué dependiente mostrar.

    El titular va primero y siempre: el caso más común es reservar para uno
    mismo, y obligarlo a buscarse en una lista sería absurdo.
    """
    titular = titular_de(user)
    if titular is None:
        return []

    opciones = [{
        "id": titular.id,
        "full_name": titular.full_name,
        "relationship": "",
        "relationship_label": "Yo",
        "is_self": True,
        "birth_date": titular.birth_date,
    }]
    opciones.extend(
        {
            "id": dependiente.id,
            "full_name": dependiente.full_name,
            "relationship": dependiente.relationship,
            "relationship_label": dependiente.get_relationship_display(),
            "is_self": False,
            "birth_date": dependiente.birth_date,
        }
        for dependiente in titular.dependents.filter(is_active=True)
    )
    return opciones


# --------------------------------------------------------------------------
#  Vista
# --------------------------------------------------------------------------

class DependentViewSet(viewsets.ModelViewSet):
    """`/api/patients/dependents/` — los familiares a cargo de quien pregunta."""

    lookup_value_regex = UUID_REGEX
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    permission_classes_by_action = {
        "list": [CanReadDependents],
        "retrieve": [CanReadDependents],
        "options_for_selector": [CanReadDependents],
        "create": [CanWriteDependents],
        "partial_update": [CanWriteDependents],
        "destroy": [CanWriteDependents],
        "promote": [CanWriteDependents],
    }

    def get_permissions(self):
        clases = self.permission_classes_by_action.get(
            self.action, [CanReadDependents],
        )
        return [IsAuthenticated()] + [clase() for clase in clases]

    def get_serializer_class(self):
        if self.action == "create":
            return DependentCreateSerializer
        return DependentSerializer

    def titular(self):
        return titular_de(self.request.user)

    def get_queryset(self):
        """Sólo los dependientes de quien pregunta.

        Punto (d) al revés: el titular ve a los suyos y a nadie más. RLS ya
        acota a la organización; esto acota a la familia.
        """
        titular = self.titular()
        if titular is None:
            return Patient.objects.none()
        return titular.dependents.filter(is_active=True)

    # ---------- Alta (puntos a, b, c y g) -------------------------------

    def create(self, request, *args, **kwargs):
        titular = self.titular()
        if titular is None:
            return _sin_ficha()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = dict(serializer.validated_data)
        confirmar = datos.pop("confirm_link", False)

        # Punto (g): el tope existe para que el alta de dependientes no sea una
        # puerta abierta a inflar el padrón desde una cuenta cualquiera.
        if titular.dependents.filter(is_active=True).count() >= settings.PATIENT_MAX_DEPENDENTS:
            return Response(
                {"code": "limite_de_dependientes",
                 "detail": "Llegaste al máximo de personas a cargo "
                           f"({settings.PATIENT_MAX_DEPENDENTS}). "
                           "Pedí ayuda en el centro médico."},
                status=status.HTTP_409_CONFLICT,
            )

        documento = datos.get("document_number") or None
        existente = None
        if documento:
            existente = Patient.objects.filter(
                organization=titular.organization,
                document_type=datos.get("document_type", Patient.DocumentType.CI),
                document_number=documento,
            ).first()

        if existente is not None:
            return self._vincular(request, titular, existente, datos, confirmar)

        with transaction.atomic():
            dependiente = Patient.objects.create(
                organization=titular.organization,
                guardian=titular,
                **datos,
            )

        bitacora.record(
            request,
            action=Action.PATIENT_UPDATE,
            entity="patients",
            entity_id=dependiente.id,
            detail={"alta": "dependiente",
                    "relationship": dependiente.relationship,
                    "guardian_id": str(titular.id)},
        )
        return Response(
            DependentSerializer(dependiente).data,
            status=status.HTTP_201_CREATED,
        )

    def _vincular(self, request, titular, existente, datos, confirmar):
        """Punto (c): el documento ya está en el padrón. Se vincula, no se duplica.

        **Por qué el vínculo pide confirmar con los datos coincidiendo.** Dejar
        que cualquiera se cuelgue de una ficha existente sabiendo sólo el número
        de documento convertiría este endpoint en una forma de leerle el
        historial a un desconocido: el punto (d) le da al titular el mismo
        alcance sobre su dependiente que sobre sí mismo. Por eso se exige que
        nombre, apellido y fecha de nacimiento coincidan con lo que la ficha ya
        tiene — quien vincula a un familiar los sabe; quien está probando
        números de documento, no—. Y por eso la respuesta del primer intento
        **no dice de quién es la ficha**: sería el mismo oráculo, servido más
        rápido.
        """
        if existente.id == titular.id:
            return Response(
                {"code": "documento_propio",
                 "detail": "Ese es tu propio documento."},
                status=status.HTTP_409_CONFLICT,
            )
        if existente.guardian_id == titular.id:
            return Response(
                {"code": "ya_es_dependiente",
                 "detail": "Esa persona ya figura entre las que tenés a cargo."},
                status=status.HTTP_409_CONFLICT,
            )
        if existente.user_id is not None:
            return Response(
                {"code": "ficha_con_cuenta",
                 "detail": "Esa persona ya tiene su propia cuenta y no puede "
                           "quedar a cargo de otra."},
                status=status.HTTP_409_CONFLICT,
            )
        if existente.guardian_id is not None:
            return Response(
                {"code": "ficha_a_cargo_de_otro",
                 "detail": "Esa persona ya está a cargo de otro titular. "
                           "Resolvelo en el centro médico."},
                status=status.HTTP_409_CONFLICT,
            )

        if not confirmar:
            return Response(
                {"code": "documento_existente",
                 "detail": "Ya hay una ficha con ese documento en el centro "
                           "médico. Si es la persona que querés agregar, "
                           "confirmá y se vincula la ficha que ya existe en "
                           "lugar de crear una nueva.",
                 "can_link": True},
                status=status.HTTP_409_CONFLICT,
            )

        coincide = (
            normalizar(datos.get("first_name", "")) == normalizar(existente.first_name)
            and normalizar(datos.get("last_name", "")) == normalizar(existente.last_name)
            and datos.get("birth_date") == existente.birth_date
        )
        if not coincide:
            # Mensaje deliberadamente parejo con el de arriba: decir cuál de los
            # tres datos falló sería ir revelándolos de a uno.
            return Response(
                {"code": "datos_no_coinciden",
                 "detail": "Los datos no coinciden con la ficha que ya existe. "
                           "Revisalos o acercate al centro médico."},
                status=status.HTTP_409_CONFLICT,
            )

        with transaction.atomic():
            existente.guardian = titular
            existente.relationship = datos["relationship"]
            existente.is_active = True
            existente.save(update_fields=[
                "guardian", "relationship", "is_active", "updated_at",
            ])

        bitacora.record(
            request,
            action=Action.PATIENT_UPDATE,
            entity="patients",
            entity_id=existente.id,
            detail={"vinculo": "alta", "relationship": existente.relationship,
                    "guardian_id": str(titular.id)},
        )
        return Response(DependentSerializer(existente).data, status=status.HTTP_200_OK)

    # ---------- Baja del vínculo (punto e) ------------------------------

    def destroy(self, request, *args, **kwargs):
        """Punto (e): se corta el vínculo, **no** se borra la ficha.

        La historia clínica es longitudinal y sobrevive al vínculo: el hijo que
        deja de estar a cargo sigue teniendo sus atenciones, sus antecedentes y
        su ficha.

        Con una excepción que impone la base: una ficha sin documento **y** sin
        titular no puede existir (``ck_patient_doc_or_guardian``), porque nadie
        respondería por ella. Desvincular a un menor sin documento se rechaza
        con esa explicación en vez de reventar con un error de integridad.
        """
        dependiente = self.get_object()

        if not dependiente.document_number:
            return Response(
                {"code": "sin_documento",
                 "detail": "No se puede desvincular una ficha sin documento: "
                           "quedaría sin nadie que responda por ella. Cargale "
                           "el documento primero."},
                status=status.HTTP_409_CONFLICT,
            )

        with transaction.atomic():
            dependiente.guardian = None
            dependiente.relationship = ""
            dependiente.save(update_fields=[
                "guardian", "relationship", "updated_at",
            ])

        bitacora.record(
            request,
            action=Action.PATIENT_UPDATE,
            entity="patients",
            entity_id=dependiente.id,
            detail={"vinculo": "baja"},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ---------- Paso a titular (punto f) --------------------------------

    @action(detail=True, methods=["post"])
    def promote(self, request, pk=None):
        """Le crea la cuenta de acceso y le corta el vínculo, conservando todo.

        La ficha es la misma —mismo uuid, mismos antecedentes, mismas
        atenciones—: lo único que cambia es que ahora tiene con qué entrar y ya
        no está a cargo de nadie. Si se creara una ficha nueva, el historial
        quedaría partido en dos justo en el cumpleaños número dieciocho.
        """
        dependiente = self.get_object()
        titular = self.titular()

        edad = edad_en_anios(dependiente.birth_date)
        if edad is None:
            return Response(
                {"code": "sin_fecha_de_nacimiento",
                 "detail": "Cargá la fecha de nacimiento antes de pasar la "
                           "ficha a titular."},
                status=status.HTTP_409_CONFLICT,
            )
        if edad < settings.PATIENT_MAJORITY_AGE:
            return Response(
                {"code": "menor_de_edad",
                 "detail": f"Todavía no cumple {settings.PATIENT_MAJORITY_AGE} años."},
                status=status.HTTP_409_CONFLICT,
            )
        if not dependiente.document_number:
            return Response(
                {"code": "sin_documento",
                 "detail": "Una cuenta de acceso necesita documento."},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = PromotionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        organization = titular.organization
        if User.objects.filter(
            organization=organization, email__iexact=email,
        ).exists():
            return Response(
                {"code": "correo_en_uso",
                 "detail": "Ya hay una cuenta con ese correo en el centro médico."},
                status=status.HTTP_409_CONFLICT,
            )
        if User.objects.filter(
            organization=organization,
            document_number=dependiente.document_number,
        ).exists():
            return Response(
                {"code": "documento_en_uso",
                 "detail": "Ya hay una cuenta con ese documento en el centro médico."},
                status=status.HTTP_409_CONFLICT,
            )

        role = Role.objects.filter(
            organization=organization, code="patient", is_active=True,
        ).first()
        if role is None:
            return Response(
                {"code": "sin_rol_paciente",
                 "detail": "El centro médico no tiene configurado el rol Paciente."},
                status=status.HTTP_409_CONFLICT,
            )

        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                password=serializer.validated_data["password"],
                organization=organization,
                first_name=dependiente.first_name,
                last_name=dependiente.last_name,
                document_type=dependiente.document_type,
                document_number=dependiente.document_number,
                birth_date=dependiente.birth_date,
                phone=dependiente.phone,
            )
            UserRole.objects.create(
                user=user, role=role, organization=organization,
            )
            dependiente.user = user
            dependiente.guardian = None
            dependiente.relationship = ""
            dependiente.save(update_fields=[
                "user", "guardian", "relationship", "updated_at",
            ])

        bitacora.record(
            request,
            action=Action.USER_CREATE,
            entity="patients",
            entity_id=dependiente.id,
            detail={"promocion": "dependiente_a_titular",
                    "email": email,
                    "guardian_id": str(titular.id)},
        )
        return Response(
            {"id": str(dependiente.id), "user_id": str(user.id), "email": email},
            status=status.HTTP_201_CREATED,
        )

    # ---------- Selector compartido (punto h) ---------------------------

    @action(detail=False, methods=["get"], url_path="patient-options")
    def options_for_selector(self, request):
        """`GET .../dependents/patient-options/` — "¿para quién es esta ficha?".

        Lo consume US-08 y lo va a consumir la reserva del Sprint 2. Se publica
        como endpoint propio y no como un campo del listado porque lo que
        necesita quien elige es el titular **más** los dependientes, y el
        listado de dependientes por definición no trae al titular.
        """
        return Response(PatientOptionSerializer(patient_options(request.user), many=True).data)

    # ---------- Edición ---------------------------------------------------

    def perform_update(self, serializer):
        dependiente = serializer.save()
        bitacora.record(
            self.request,
            action=Action.PATIENT_UPDATE,
            entity="patients",
            entity_id=dependiente.id,
            detail={"edicion": "dependiente"},
        )

    def list(self, request, *args, **kwargs):
        if self.titular() is None:
            return _sin_ficha()
        return super().list(request, *args, **kwargs)


def _sin_ficha():
    """Quien pregunta tiene cuenta pero no ficha de paciente.

    Le pasa al administrador que se dio a sí mismo el permiso. Devolver una
    lista vacía haría pensar que se perdieron los datos.
    """
    return Response(
        {"code": "sin_ficha_de_paciente",
         "detail": "Tu cuenta no tiene ficha de paciente, así que no puede "
                   "tener personas a cargo."},
        status=status.HTTP_409_CONFLICT,
    )
