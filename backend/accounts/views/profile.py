"""US-05 — Edición del propio perfil (CU6).

    GET   /api/accounts/users/me/            el perfil de quien está autenticado
    PATCH /api/accounts/users/me/            datos de contacto, guardado parcial
    POST  /api/accounts/users/me/password/   contraseña actual -> nueva

**El usuario sale del token, nunca de la URL ni del cuerpo.** Es el punto (a)
de la historia, y por eso la ruta dice ``me`` y no lleva un identificador: no
hay ningún parámetro que alguien pueda cambiar para editar el perfil de otro.

**Sólo PATCH, no PUT.** El punto (f) pide guardado parcial —editar el teléfono
no obliga a reenviar toda la ficha—, y con un PUT a medio llenar DRF exigiría
los demás campos.

**Cambiar la contraseña no cierra la sesión en curso** (punto c), a diferencia
de la recuperación de US-03: acá la persona ya demostró conocer la actual. Lo
que sí se hace es mandar a la lista negra **las demás** sesiones —un teléfono
perdido, una computadora prestada— y devolver un par de tokens nuevo para la
que hizo el cambio. Es la única forma de distinguirla: el backend no sabe cuál
de los refrescos vigentes es el de esta petición, porque llegó con el acceso.
El cliente guarda el par nuevo y sigue adentro sin volver a escribir nada.
"""

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit import services as bitacora
from audit.actions import Action
from patients.models import Patient

from ..serializers.profile import PasswordChangeSerializer, ProfileSerializer
from ..services.password_reset import revoke_all_sessions
from ..tokens import tokens_for_user

# Lo que se copia a la ficha de paciente titular al editar el perfil. Ver
# `_sincronizar_paciente`.
CAMPOS_DEL_PACIENTE = ("first_name", "last_name", "phone")


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def profile(request):
    """Puntos (a), (b), (d), (e) y (f)."""
    user = request.user

    if request.method == "GET":
        return Response(ProfileSerializer(user).data)

    serializer = ProfileSerializer(user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)

    cambiados = sorted(
        campo for campo, valor in serializer.validated_data.items()
        if getattr(user, campo) != valor
    )
    correo_anterior = user.email

    if cambiados:
        with transaction.atomic():
            serializer.save()
            _sincronizar_paciente(user, cambiados)

        detalle = {"fields": cambiados}
        if "email" in cambiados:
            # El correo es con lo que se entra al sistema. Si alguien se
            # adueña de una sesión y lo cambia, el asiento con el anterior es
            # lo único que permite reconstruir de quién era la cuenta.
            detalle["email"] = {"before": correo_anterior, "after": user.email}
        bitacora.record(
            request, Action.PROFILE_UPDATE, "users", user.id, detail=detalle,
        )

    return Response(ProfileSerializer(user).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Punto (c) — Cambio de contraseña acreditando la actual.

    La contraseña actual equivocada responde con ``Response`` y no con
    ``raise``, por el mismo motivo que el login de US-02: la petición corre en
    la transacción de ``TenantMiddleware``, y con una excepción se perdería el
    asiento que deja el intento fallido.
    """
    user = request.user
    serializer = PasswordChangeSerializer(
        data=request.data, context={"user": user},
    )
    serializer.is_valid(raise_exception=True)
    datos = serializer.validated_data

    if not user.check_password(datos["current_password"]):
        bitacora.record(
            request, Action.PASSWORD_CHANGE, "users", user.id,
            detail={"succeeded": False},
        )
        return Response(
            {"code": "contrasena_actual_incorrecta",
             "current_password": ["La contraseña actual no es correcta."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if user.check_password(datos["password"]):
        return Response(
            {"code": "contrasena_repetida",
             "password": ["La contraseña nueva tiene que ser distinta de la "
                          "actual."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        user.set_password(datos["password"])
        user.save(update_fields=["password", "updated_at"])
        revocadas = revoke_all_sessions(user)
        # Después de revocar, no antes: si no, el par nuevo caería en la
        # misma lista negra que los viejos.
        tokens = tokens_for_user(user)

    bitacora.record(
        request, Action.PASSWORD_CHANGE, "users", user.id,
        detail={"succeeded": True, "sesiones_invalidadas": revocadas},
    )

    return Response(
        {"detail": "Tu contraseña se cambió. Las demás sesiones que tenías "
                   "abiertas se cerraron; ésta sigue activa.",
         **tokens},
        status=status.HTTP_200_OK,
    )


def _sincronizar_paciente(user, cambiados):
    """Copia nombres y teléfono a la ficha de paciente titular, si la tiene.

    El alta de US-01 escribe esos datos dos veces: en la cuenta y en la ficha
    demográfica (``patients``), que es la que ve recepción. Si el perfil sólo
    actualizara la cuenta, el paciente cambiaría su teléfono y el mostrador
    lo seguiría llamando al viejo.

    El correo no se copia porque la ficha no lo tiene. El documento tampoco,
    porque no es editable acá (punto d).
    """
    campos = [campo for campo in cambiados if campo in CAMPOS_DEL_PACIENTE]
    if not campos:
        return
    # `update()` no dispara `auto_now`: la fecha va a mano.
    Patient.objects.filter(user=user).update(
        **{campo: getattr(user, campo) for campo in campos},
        updated_at=timezone.now(),
    )
