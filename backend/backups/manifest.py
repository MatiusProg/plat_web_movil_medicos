"""Característica general 6 — Qué entra en una copia de seguridad y en qué orden.

La consigna pide «funciones para posibilitar las copias de seguridad y
restauración de todo el sistema». En un sistema multi-inquilino eso son **dos
cosas distintas**, y confundirlas es el error que este archivo evita:

1. **La copia de toda la instalación** —el `pg_dump` de la base entera— es
   trabajo del administrador de la plataforma, no de la aplicación. Está en el
   comando de gestión ``manage.py dump_database`` y en la documentación del
   despliegue: una aplicación que se respalda a sí misma entera no sobrevive a
   que se caiga la base, que es justamente el caso para el que existe un
   respaldo.
2. **La copia de una organización** —lo que hay acá— es lo que un cliente de un
   SaaS necesita y no puede pedirle al proveedor: llevarse *sus* datos, poder
   restaurarlos, y poder irse. Es una copia lógica, en JSON, que cruza
   versiones de PostgreSQL porque no depende del formato binario de nadie.

**El orden de esta lista es el orden de restauración** y no es alfabético: una
fila no se puede insertar antes que aquella a la que apunta. Se restaura de
arriba hacia abajo y se borra de abajo hacia arriba.

**Lo que NO se restaura, y por qué.** Cinco tablas se exportan pero están
marcadas ``restore=False``. Las tres primeras porque volver atrás borraría
evidencia; las dos últimas porque no son del inquilino:

- ``audit_log`` — la bitácora. ``app_user`` no tiene ``UPDATE`` ni ``DELETE``
  sobre ella (US-06, RNF-18), así que una restauración no podría borrar lo
  existente ni aunque quisiera; y si sólo agregara, la bitácora quedaría con
  los asientos duplicados. Una bitácora que se puede reescribir con un archivo
  que trajo el usuario deja de ser una bitácora: la restauración sería la forma
  de borrar el rastro de lo que uno hizo. Se incluye en la copia —quien se
  lleva sus datos se lleva su bitácora— y se niega a volver.
- ``login_attempts`` y ``password_reset_tokens`` — evidencia de seguridad y
  credenciales en curso. Reponer tokens de restablecimiento viejos es revivir
  enlaces que ya se habían consumido.
- ``subscriptions`` y ``usage_metrics`` — la relación comercial. El detalle
  está en el comentario de su bloque, más abajo.
"""

from dataclasses import dataclass


#  Cómo se limpia una tabla antes de reponerla desde el archivo.
#
#  `PURGE` borra las filas y las vuelve a escribir. Es lo normal.
#
#  `DEACTIVATE` no borra nada: repone lo que el archivo trae y **desactiva** lo
#  que el archivo no menciona. Existe por `users`, y la razón es de la propia
#  plataforma: `audit_log` y `login_attempts` apuntan a un usuario con
#  `SET_NULL`, y `app_user` no tiene `UPDATE` sobre ninguna de las dos
#  —US-06 y RNF-18, la bitácora es inalterable—. Borrar un usuario que dejó un
#  asiento es, literalmente, imposible en esta base, y está bien que lo sea.
#
#  Desactivar no es un rodeo al problema: es la misma decisión que US-10 tomó
#  para los pacientes —«baja lógica y nunca física»— aplicada acá. Una cuenta
#  creada después del respaldo queda sin poder entrar, que es lo que
#  «volver a ese momento» significa en términos de acceso, y la cadena de
#  auditoría no se rompe.
PURGE = "purge"
DEACTIVATE = "deactivate"


@dataclass(frozen=True)
class Table:
    """Una tabla de la copia.

    ``label`` es lo que ve el usuario en el resumen. ``restore`` dice si la
    restauración la toca; ``strategy``, cómo. Ver el porqué de cada uno en el
    encabezado del módulo y en el comentario de arriba.
    """

    app: str
    model: str
    label: str
    restore: bool = True
    strategy: str = PURGE

    @property
    def key(self) -> str:
        """``accounts.User`` — la clave con la que viaja en el archivo."""
        return f"{self.app}.{self.model}"


# Orden de dependencia: cada tabla sólo apunta a tablas que están más arriba,
# o a sí misma. Las dos autorreferencias —`patients.guardian` y
# `roles`— se resuelven desactivando la comprobación de claves durante la
# transacción de restauración; ver `services._restore_table`.
TABLES: tuple[Table, ...] = (
    # ---------- Identidad y autorización ----------
    Table("accounts", "Role", "Roles"),
    Table("accounts", "RolePermission", "Permisos de cada rol"),
    Table("accounts", "User", "Usuarios", strategy=DEACTIVATE),
    Table("accounts", "UserRole", "Roles asignados"),

    # ---------- Catálogo ----------
    Table("catalog", "Branch", "Sucursales"),
    Table("catalog", "BranchHours", "Horarios de sucursal"),
    Table("catalog", "Specialty", "Especialidades"),
    Table("catalog", "Practitioner", "Profesionales"),
    Table("catalog", "PractitionerSpecialty", "Especialidad de cada profesional"),
    Table("catalog", "PractitionerBranch", "Sucursal de cada profesional"),

    # ---------- Agendas ----------
    Table("scheduling", "Schedule", "Agendas médicas"),
    Table("scheduling", "ScheduleBlock", "Bloqueos de agenda"),

    # ---------- Pacientes ----------
    Table("patients", "Patient", "Pacientes"),
    Table("patients", "PatientHistoryEntry", "Antecedentes"),

    # ---------- Reportes ----------
    Table("reporting", "SavedReport", "Reportes guardados"),

    # ---------- Sólo copia, nunca restauración ----------
    # La organización en sí no entra en ninguna de las dos listas: es el
    # recipiente, no el contenido. Una restauración vuelca datos DENTRO de una
    # organización que ya existe.
    Table("accounts", "AuditLog", "Bitácora", restore=False),
    Table("accounts", "LoginAttempt", "Intentos de acceso", restore=False),
    Table("accounts", "PasswordResetToken", "Tokens de restablecimiento",
          restore=False),
    # La suscripción y el consumo son la **relación comercial**, no los datos
    # del inquilino. Sus políticas RLS lo dicen con todas las letras:
    # `tenant_reads_itself` es sólo `FOR SELECT`, y escribir exige
    # `app_is_platform_admin()`. Restaurarlas sería que un cliente se
    # reasignara su propio plan volviendo a un archivo viejo —o se repusiera
    # las métricas de uso con las que se le factura—. Entran en la copia
    # porque el cliente puede leerlas y le corresponde llevárselas; no
    # vuelven. Cambiar de plan es US-44 y pasa por el superadministrador.
    Table("tenancy", "Subscription", "Suscripciones", restore=False),
    Table("tenancy", "UsageMetric", "Métricas de uso", restore=False),
)

RESTORABLE = tuple(table for table in TABLES if table.restore)

BY_KEY = {table.key: table for table in TABLES}
