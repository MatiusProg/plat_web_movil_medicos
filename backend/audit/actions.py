"""US-06 — Catálogo de acciones que la bitácora sabe nombrar.

Las acciones son cadenas y no una tabla a propósito: una acción nueva no
debería exigir una migración. Pero tampoco se escriben a mano en cada llamada,
porque entonces ``role.assign`` y ``role.assigned`` conviven en la misma
columna y el filtro por tipo de acción del punto (e) deja de servir.

**Cómo se agrega una acción.** Se declara acá con su etiqueta, y se usa la
constante en la llamada a ``audit.services.record``. Lo que no está declarado
se acepta igual —la bitácora nunca rechaza un asiento, ver ``services.record``—
pero no aparece en el desplegable del filtro.

Los códigos de US-02, US-03 y US-04 ya estaban en uso antes de que existiera
esta app: se los copia tal cual, sin renombrar nada. Renombrarlos dejaría los
asientos ya escritos fuera de todo filtro.
"""


class Action:
    """Los códigos, agrupados por el módulo que los escribe."""

    # ---------- Identidad — US-03 y US-04 (Karen) ----------------------
    PASSWORD_RESET_REQUEST = "password.reset.request"
    PASSWORD_RESET_COMPLETE = "password.reset.complete"
    ROLE_CREATE = "role.create"
    ROLE_UPDATE = "role.update"
    ROLE_DELETE = "role.delete"
    ROLE_PERMISSIONS_UPDATE = "role.permissions.update"
    ROLE_ASSIGN = "role.assign"
    ROLE_REVOKE = "role.revoke"

    # ---------- Usuarios — el backlog los pide por nombre --------------
    USER_CREATE = "user.create"
    USER_DEACTIVATE = "user.deactivate"

    # ---------- Plataforma — US-43 (Alexander) -------------------------
    ORGANIZATION_CREATE = "organization.create"

    # ---------- Pacientes — US-08 y US-10 ------------------------------
    PATIENT_UPDATE = "patient.update"
    PATIENT_DEACTIVATE = "patient.deactivate"
    PATIENT_MERGE = "patient.merge"
    # Punto (g) de US-08: la lectura de antecedentes por un profesional se
    # audita. La del propio paciente sobre sus datos, no: sería una fila por
    # cada vez que alguien abre su propia pantalla.
    HISTORY_READ = "history.read"

    # ---------- Sprints siguientes -------------------------------------
    # Declarados acá porque el punto (a) los enumera como acciones sensibles.
    # Los escribe el módulo que los provoque, cuando exista.
    RECORD_READ = "record.read"              # historia clínica (Sprint 3)
    APPOINTMENT_CANCEL = "appointment.cancel"  # anulación de ficha (Sprint 2)
    PAYMENT_MOVEMENT = "payment.movement"      # movimiento de pago (Sprint 2)


LABELS = {
    Action.PASSWORD_RESET_REQUEST: "Solicitud de restablecimiento de contraseña",
    Action.PASSWORD_RESET_COMPLETE: "Contraseña restablecida",
    Action.ROLE_CREATE: "Rol creado",
    Action.ROLE_UPDATE: "Rol editado",
    Action.ROLE_DELETE: "Rol eliminado",
    Action.ROLE_PERMISSIONS_UPDATE: "Permisos de un rol modificados",
    Action.ROLE_ASSIGN: "Rol asignado a un usuario",
    Action.ROLE_REVOKE: "Rol revocado a un usuario",
    Action.USER_CREATE: "Usuario dado de alta",
    Action.USER_DEACTIVATE: "Usuario dado de baja",
    Action.ORGANIZATION_CREATE: "Organización dada de alta",
    Action.PATIENT_UPDATE: "Datos de paciente corregidos",
    Action.PATIENT_DEACTIVATE: "Paciente dado de baja",
    Action.PATIENT_MERGE: "Pacientes duplicados fusionados",
    Action.HISTORY_READ: "Antecedentes consultados por un profesional",
    Action.RECORD_READ: "Historia clínica consultada",
    Action.APPOINTMENT_CANCEL: "Ficha anulada",
    Action.PAYMENT_MOVEMENT: "Movimiento de pago",
}


def label(code: str) -> str:
    """La etiqueta legible, o el propio código si nadie lo declaró."""
    return LABELS.get(code, code)
