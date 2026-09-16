"""Lo que entra al asistente.

Poca cosa: una pregunta y, opcionalmente, a qué parte del corpus acotarla. La
validación interesante es el largo mínimo, que no es una formalidad — ver el
docstring de ``validate_question``.
"""

from rest_framework import serializers

from .models import KnowledgeChunk


class SuggestSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=2000)
    # US-32: «¿a qué hora abren?» no debería recuperar una descripción
    # clínica. La pantalla del chat no lo manda; lo usa el asistente
    # administrativo de mostrador, que ya sabe de qué está preguntando.
    source_types = serializers.ListField(
        child=serializers.ChoiceField(choices=KnowledgeChunk.Source.choices),
        required=False, allow_empty=True,
    )

    def validate_question(self, valor):
        """Una pregunta de tres letras no se puede vectorizar con sentido.

        El proveedor local descarta las palabras de menos de tres caracteres y
        las vacías, así que «hola» produce el vector nulo y la búsqueda
        devuelve cualquier cosa ordenada al azar. Es mejor pedir que escriba
        que contestar con el primer fragmento que salga.
        """
        limpio = (valor or "").strip()
        if len(limpio) < 8:
            raise serializers.ValidationError(
                "Contame un poco más para poder orientarte: al menos unas "
                "palabras sobre lo que te pasa o lo que querés consultar.",
            )
        return limpio
