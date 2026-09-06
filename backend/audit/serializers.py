"""US-06 (b) y (e) — Cómo se lee un asiento.

Sólo lectura: todos los campos son ``read_only``. No es una precaución
decorativa —la vista tampoco expone verbos de escritura, punto (f)— sino la
segunda cerradura: si mañana alguien registra este serializer en un
``ModelViewSet`` completo por descuido, sigue sin poder escribir.
"""

from rest_framework import serializers

from accounts.models import AuditLog

from .actions import label


class AuditActorSerializer(serializers.Serializer):
    """Quién. Se anida en vez de devolver sólo el uuid: la pantalla lista
    asientos, y resolver un nombre por fila sería una consulta por fila."""

    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, user):
        return f"{user.first_name} {user.last_name}".strip()


class AuditLogSerializer(serializers.ModelSerializer):
    actor = AuditActorSerializer(source="user", read_only=True)
    action_label = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "action",
            "action_label",
            "entity",
            "entity_id",
            "detail",
            "ip_address",
            "user_agent",
            "occurred_at",
        ]
        read_only_fields = fields

    def get_action_label(self, entry):
        """El texto que la pantalla muestra. Un asiento cuya acción nadie
        declaró se muestra con su código, no en blanco: la bitácora nunca
        rechaza un asiento, así que tampoco puede esconderlo."""
        return label(entry.action)
