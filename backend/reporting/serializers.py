"""Cómo entra y cómo sale una definición de reporte.

**La definición no se valida acá.** Los serializers comprueban la *forma* —que
``columns`` sea una lista de cadenas, que el formato esté entre los cuatro—, y
``query.build`` comprueba el *contenido* contra el catálogo. La división no es
caprichosa: un reporte guardado en marzo puede mencionar una columna que en
septiembre ya no existe, así que la validación contra el catálogo tiene que
correr **al ejecutar**, no al guardar. Si estuviera en el serializer, un
reporte guardado sería imposible de editar el día que su conjunto cambia: no
pasaría la validación ni para arreglarlo.
"""

from rest_framework import serializers

from . import datasets, exporters
from .models import SavedReport


class ColumnSerializer(serializers.Serializer):
    """Una columna, como la ve el constructor del frontend."""

    code = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    kind = serializers.CharField(read_only=True)
    choices = serializers.SerializerMethodField()

    def get_choices(self, column):
        """Las opciones del desplegable, ya en el orden en que se muestran.

        Se devuelven como lista de objetos y no como el diccionario: un objeto
        JSON no garantiza el orden de sus claves, y «Masculino, Femenino, Otro»
        tiene un orden que el formulario debe respetar.
        """
        if not column.choices:
            return None
        return [
            {"value": valor, "label": etiqueta}
            for valor, etiqueta in column.choices.items()
        ]


class FilterSerializer(ColumnSerializer):
    """Un criterio de selección. Lleva además los operadores aplicables."""

    operators = serializers.SerializerMethodField()

    def get_operators(self, filtro):
        return sorted(datasets.OPERATORS[filtro.kind])


class DatasetSerializer(serializers.Serializer):
    """Todo lo que el constructor necesita para dibujar el formulario.

    Es el endpoint que hace que el frontend no sepa nada del modelo de datos:
    con esto arma el selector de columnas, el de orden y el formulario de
    filtros previo a generar.
    """

    code = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    columns = ColumnSerializer(many=True, read_only=True)
    filters = FilterSerializer(many=True, read_only=True)
    default_columns = serializers.ListField(
        child=serializers.CharField(), read_only=True,
    )


class DefinitionSerializer(serializers.Serializer):
    """La forma de una definición. El contenido lo valida ``query.build``."""

    dataset = serializers.CharField()
    columns = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True,
    )
    filters = serializers.ListField(
        child=serializers.DictField(), required=False, allow_empty=True,
    )
    order_by = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True,
    )


class RunSerializer(DefinitionSerializer):
    """Una definición más cómo se quiere el resultado.

    ``format`` ausente significa JSON: es lo que pide la vista previa del
    constructor, que muestra las primeras filas antes de exportar nada. Los
    cuatro formatos de archivo son los de la consigna.
    """

    format = serializers.ChoiceField(
        choices=[("json", "json")] + [(f, f) for f in exporters.FORMATS],
        required=False, default="json",
    )
    title = serializers.CharField(required=False, allow_blank=True,
                                  max_length=120)
    # Sólo para la vista previa: cuántas filas devolver en el JSON. No se
    # aplica a los archivos, que salen completos hasta el tope de `query`.
    preview_rows = serializers.IntegerField(
        required=False, min_value=1, max_value=500, default=50,
    )
    # Si viene, el resultado se manda por correo en vez de descargarse.
    recipients = serializers.ListField(
        child=serializers.EmailField(), required=False, allow_empty=True,
    )

    def validate(self, datos):
        """Mandar por correo un JSON no es un caso: hay que elegir formato.

        Sin esta comprobación, pedir destinatarios sin formato adjunta un
        archivo `.json` que el destinatario no puede abrir con nada.
        """
        if datos.get("recipients") and datos.get("format", "json") == "json":
            raise serializers.ValidationError({
                "format": "Para enviar por correo hay que elegir un formato de "
                          "archivo: csv, xlsx, html o pdf.",
            })
        return datos


class SavedReportSerializer(serializers.ModelSerializer):
    """Un reporte guardado, para la lista y para el alta."""

    definition = DefinitionSerializer()
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    is_mine = serializers.SerializerMethodField()
    # El nombre legible del conjunto. La lista lo muestra y resolverlo en el
    # frontend obligaría a cruzarla contra el catálogo fila por fila.
    dataset_label = serializers.SerializerMethodField()

    class Meta:
        model = SavedReport
        fields = [
            "id", "name", "description", "dataset", "dataset_label",
            "definition", "is_shared", "owner_email", "is_mine",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "dataset", "dataset_label", "owner_email",
                            "is_mine", "created_at", "updated_at"]

    def get_is_mine(self, report):
        usuario = self.context["request"].user
        return report.owner_id == usuario.id

    def get_dataset_label(self, report):
        dataset = datasets.get(report.dataset)
        return dataset.label if dataset else report.dataset

    def validate_definition(self, definicion):
        """Que el conjunto exista. Lo demás se valida al ejecutar.

        Ésta sí va acá: guardar un reporte sobre un conjunto que nunca existió
        es un error de tipeo del cliente, no una definición que envejeció.
        """
        codigo = (definicion.get("dataset") or "").strip()
        if datasets.get(codigo) is None:
            raise serializers.ValidationError(
                f"No existe el conjunto de datos «{codigo}».",
            )
        return definicion

    def create(self, validated_data):
        """El dueño y la organización salen de quien pide, nunca del cuerpo.

        Si vinieran del JSON, cualquiera podría guardar un reporte a nombre de
        otro —o en otra organización, que RLS rechazaría con un error de base
        en vez de con un 403 legible—.
        """
        usuario = self.context["request"].user
        validated_data["owner"] = usuario
        validated_data["organization"] = usuario.organization
        validated_data["dataset"] = validated_data["definition"]["dataset"]
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "definition" in validated_data:
            validated_data["dataset"] = validated_data["definition"]["dataset"]
        return super().update(instance, validated_data)
