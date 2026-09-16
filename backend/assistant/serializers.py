"""Entrada y salida de ``POST /api/assistant/suggest/``."""

from rest_framework import serializers


class SuggestRequestSerializer(serializers.Serializer):
    """Lo que manda el móvil.

    El tope de 1.000 caracteres no es decorativo: cada consulta se vectoriza,
    y el largo del texto es lo que consume la cuota del proveedor. Sin tope,
    una sola petición con un texto pegado puede agotarla.
    """

    question = serializers.CharField(
        max_length=1000, trim_whitespace=True,
        error_messages={"blank": "Contanos qué te pasa para poder orientarte."},
    )


class FragmentSerializer(serializers.Serializer):
    """Un fragmento recuperado, tal como viaja al cliente.

    **Esto es lo que hace auditable la respuesta.** Sin la lista de fragmentos
    no hay forma de demostrar que el asistente no alucinó, que es el criterio
    con el que se muestra US-31 el 16/09. No es información de depuración: es
    parte del contrato del endpoint.
    """

    id = serializers.CharField()
    text = serializers.CharField()
    source_type = serializers.CharField()
    source_id = serializers.CharField()
    source_name = serializers.CharField()
    similarity = serializers.FloatField()


class SpecialtySuggestionSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    similarity = serializers.FloatField()
