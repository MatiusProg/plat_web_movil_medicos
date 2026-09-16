"""Clases de permiso de la app `reporting`.

**Hay dos cerraduras y las dos hacen falta.** Éstas autorizan *usar el
constructor de reportes*; las de ``datasets.Dataset.permission`` autorizan *ver
ese dato*, y se comprueban en ``query.build`` contra quien ejecuta.

La razón de separarlas es que responden preguntas distintas. «¿Esta persona
puede armarse reportes?» es una decisión de la organización sobre sus usuarios
—una recepcionista quizá sí, un paciente no—. «¿Puede ver la bitácora?» ya
estaba contestada por US-06 y no se vuelve a contestar acá. Con una sola
cerradura habría que elegir cuál de las dos preguntas se pierde:

- si sólo valiera ``reporting.report.run``, el reporte sería la puerta lateral
  para leer datos que la pantalla correspondiente niega;
- si sólo valiera el permiso del conjunto, cualquiera que pueda ver pacientes
  podría exportar el padrón entero a un Excel, que no es lo mismo que mirarlo
  de a una ficha por pantalla.

``reporting.report.share`` es aparte de ``save`` porque compartir cambia a
quién le aparece el reporte, y eso es una decisión de la organización, no del
autor.
"""

from rest_framework.permissions import BasePermission


class RequiresPermission(BasePermission):
    code = ""
    message = "No tenés permiso para realizar esta acción."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and self.code
            and user.has_permission(self.code)
        )


class CanRunReports(RequiresPermission):
    code = "reporting.report.run"


class CanSaveReports(RequiresPermission):
    code = "reporting.report.save"


class CanShareReports(RequiresPermission):
    code = "reporting.report.share"
