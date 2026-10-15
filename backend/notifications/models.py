"""US-28 — Los teléfonos a los que se les puede mandar un push.

Firebase Cloud Messaging (FCM) le da a **cada instalación** de la app un
token: la «dirección» de ese teléfono. La app lo registra al iniciar sesión y
lo borra al cerrarla; el backend lo usa para avisar de la ficha. Es un token
**por dispositivo, no por persona**: quien tiene la app en dos teléfonos
recibe el aviso en los dos.

El token es único **por organización**, no en toda la tabla: con RLS, una
organización no ve las filas de otra, así que una unicidad global haría
fallar el registro sin poder saber contra qué fila chocó. Si el mismo
teléfono pasa a otra cuenta de la misma organización, el registro mueve el
token a la cuenta nueva.
"""

import uuid

from django.db import models


class DeviceToken(models.Model):

    class Platform(models.TextChoices):
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"
        WEB = "web", "Web"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE,
        related_name="device_tokens",
    )
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE,
        related_name="device_tokens",
    )
    token = models.TextField()
    platform = models.CharField(
        max_length=10, choices=Platform.choices, default=Platform.ANDROID,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    # La última vez que la app lo registró. Un token que no se renueva en
    # meses es de una instalación que ya no existe.
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "device_tokens"
        verbose_name = "token de dispositivo"
        verbose_name_plural = "tokens de dispositivo"
        constraints = [
            models.UniqueConstraint(
                fields=["id", "organization"], name="uq_device_token_id_org",
            ),
            models.UniqueConstraint(
                fields=["organization", "token"], name="uq_device_token_org",
            ),
        ]

    def __str__(self):
        return f"{self.user_id} · {self.platform} · {self.token[:12]}…"
