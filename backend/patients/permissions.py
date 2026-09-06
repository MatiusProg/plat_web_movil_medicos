"""Clases de permiso de la app `patients`.

**Archivo compartido.** US-07 y US-08 son del Scrum Master; US-09 y US-10, de
Michael. Cada historia agrega sus clases en su bloque y no toca las de al lado
—la misma regla que `patients/urls.py`—. La base `RequiresPermission` es de
todas y no se toca.

Todas se apoyan en ``user.has_permission("modulo.recurso.accion")``, nunca en
``user.has_perm()``: las tablas de ``django.contrib.auth`` no llevan
``organization_id`` y responderían contra los permisos de todas las
organizaciones.
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


# ---------- US-07 (SM): pacientes dependientes --------------------------

class CanReadDependents(RequiresPermission):
    code = "patients.dependent.read"


class CanWriteDependents(RequiresPermission):
    code = "patients.dependent.write"


# ---------- US-08 (SM): antecedentes del paciente -----------------------

class CanReadHistory(RequiresPermission):
    code = "patients.history.read"


class CanWriteHistory(RequiresPermission):
    code = "patients.history.write"
