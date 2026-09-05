"""US-04 — Amplía el catálogo de permisos con lo que necesita el Sprint 1.

El catálogo del Sprint 0 (``tenancy/0003_seed_catalog``) declaró los permisos
de plataforma, usuarios, pacientes y sucursales. El Sprint 1 agrega
especialidades, profesionales y agendas, y con ellos los permisos que sus
historias van a exigir en ``user.has_permission``.

**Por qué una sola migración y no una por historia.** La regla 5 del reparto
dice que nadie corre ``makemigrations`` sin avisar al Scrum Master: el modelo
del Sprint 0 ya está aplicado en local y en Supabase, y una migración
descoordinada deja las dos bases distintas. Declarar acá el catálogo completo
del sprint hace que la base compartida se toque **una vez**, y que Daniel
(US-11, US-12) y Luis (US-13, US-14) puedan autorizar sus endpoints sin pedir
otra.

**Lo que hace esta migración y el seed del Sprint 0 no hacía.** El seed sólo
escribe las plantillas del sistema (``organization_id`` NULL). Las
organizaciones dadas de alta antes de esta migración ya tienen sus copias
clonadas, y esas copias no se enteran de un permiso nuevo. Por eso acá se
recorre organización por organización, bajo el contexto de cada una, para
sumarle los permisos a los roles que conservan el código de la plantilla.

**El criterio de aceptación que no está en el Product Backlog.** La plantilla
del rol *Paciente* nacía sin ningún permiso. Sin los cuatro de lectura del
catálogo, la aplicación móvil no puede listar sucursales ni buscar
profesionales, y el Sprint 2 no puede reservar. Acá se los lleva.
"""

from django.db import migrations

# Código: <modulo>.<recurso>.<accion>. Sólo los que faltan; los del Sprint 0
# ya están y no se vuelven a declarar.
NEW_PERMISSIONS = [
    # Catálogo — US-11 (sucursales) y US-12 (especialidades y profesionales).
    ("catalog.branch.deactivate", "catalog", "Desactivar una sucursal"),
    ("catalog.specialty.create", "catalog", "Registrar especialidades"),
    ("catalog.specialty.read", "catalog", "Consultar especialidades"),
    ("catalog.specialty.update", "catalog", "Editar especialidades"),
    ("catalog.professional.create", "catalog", "Dar de alta profesionales"),
    ("catalog.professional.read", "catalog", "Consultar profesionales"),
    ("catalog.professional.update", "catalog", "Editar profesionales"),
    # Agendas — US-13 (agendas médicas) y US-14 (bloqueos).
    ("scheduling.schedule.create", "scheduling", "Crear agendas médicas"),
    ("scheduling.schedule.read", "scheduling", "Consultar agendas médicas"),
    ("scheduling.schedule.update", "scheduling", "Editar agendas médicas"),
    ("scheduling.block.create", "scheduling", "Bloquear agenda y cargar feriados"),
    ("scheduling.block.read", "scheduling", "Consultar bloqueos de agenda"),
    ("scheduling.block.update", "scheduling", "Editar o levantar un bloqueo"),
    # El espacio reservable no se administra: se deriva de la agenda. Sólo se
    # lee, y lo lee sobre todo el paciente desde el móvil (US-15, US-16).
    ("scheduling.slot.read", "scheduling", "Consultar espacios disponibles"),
    # Pacientes — US-10 pide baja lógica y fusión de duplicados, que no son un
    # `update` cualquiera: se auditan aparte y se autorizan aparte.
    ("patients.patient.deactivate", "patients", "Dar de baja lógica a un paciente"),
    ("patients.patient.merge", "patients", "Fusionar pacientes duplicados"),
    # Roles — el ABM de US-04 necesita poder dar de baja un rol.
    ("users.role.delete", "users", "Eliminar roles de la organización"),
]

# Qué permisos NUEVOS suma cada plantilla. Se expresa por código y no por
# módulo para que agregar un permiso no se lo regale a nadie sin querer.
GRANTS = {
    "org_admin": {code for code, _module, _description in NEW_PERMISSIONS},
    "practitioner": {
        "catalog.specialty.read",
        "catalog.professional.read",
        "scheduling.schedule.read",
        "scheduling.block.read",
        "scheduling.slot.read",
    },
    "receptionist": {
        "catalog.specialty.read",
        "catalog.professional.read",
        "scheduling.schedule.read",
        "scheduling.block.read",
        "scheduling.slot.read",
        "patients.patient.deactivate",
    },
    # Los cuatro del criterio de aceptación. `catalog.branch.read` viene del
    # Sprint 0, pero la plantilla del paciente nació sin ningún permiso, así
    # que hay que dárselo acá igual.
    "patient": {
        "catalog.branch.read",
        "catalog.specialty.read",
        "catalog.professional.read",
        "scheduling.slot.read",
    },
    # El superadministrador no toca datos de ninguna organización: nada de
    # esto es suyo. Ver el alcance del proyecto y la política de `users`.
    "platform_admin": set(),
}

PLATFORM_ON = "SELECT set_config('app.is_platform_admin', 'on', true)"
PLATFORM_OFF = "SELECT set_config('app.is_platform_admin', '', true)"


def _set_tenant(schema_editor, organization_id):
    """Fija el contexto de un inquilino dentro de la migración.

    Es la regla 4 del reparto: fuera del ciclo HTTP hay que envolver la
    consulta, migraciones de datos incluidas. Sin esto, ``role_permissions``
    devuelve cero filas y el INSERT lo rechaza ``tenant_isolation``.
    """
    schema_editor.execute(PLATFORM_OFF)
    schema_editor.execute(
        "SELECT set_config('app.tenant_id', %s, true)", [str(organization_id)],
    )


def _clear_tenant(schema_editor):
    schema_editor.execute("SELECT set_config('app.tenant_id', '', true)")


def _grant(RolePermission, roles, permissions, organization_id):
    """Suma a cada rol los permisos que le tocan, sin repetir los que ya tiene.

    ``roles`` viene indexado por código. Un rol que el administrador de la
    organización renombró sigue teniendo su código, así que la copia se
    encuentra igual; uno que creó él a mano no está en GRANTS y no se toca,
    que es lo correcto: sus permisos los decide su dueño, no una migración.
    """
    for code, granted_codes in GRANTS.items():
        role = roles.get(code)
        if role is None or not granted_codes:
            continue

        already = set(
            RolePermission.objects
            .filter(role=role)
            .values_list("permission__code", flat=True)
        )
        RolePermission.objects.bulk_create([
            RolePermission(
                role=role,
                permission=permissions[permission_code],
                organization_id=organization_id,
            )
            for permission_code in sorted(granted_codes - already)
        ])


def seed(apps, schema_editor):
    Organization = apps.get_model("tenancy", "Organization")
    Permission = apps.get_model("accounts", "Permission")
    Role = apps.get_model("accounts", "Role")
    RolePermission = apps.get_model("accounts", "RolePermission")

    # El catálogo de permisos es la única tabla del modelo sin RLS, pero las
    # plantillas de rol sí la tienen: su política de escritura exige el
    # contexto de superadministrador.
    schema_editor.execute(PLATFORM_ON)

    for code, module, description in NEW_PERMISSIONS:
        Permission.objects.update_or_create(
            code=code, defaults={"module": module, "description": description},
        )

    # Se indexa el catálogo entero y no sólo lo recién creado:
    # `catalog.branch.read` es del Sprint 0 y la plantilla del paciente lo
    # necesita.
    permissions = {permission.code: permission for permission in Permission.objects.all()}

    templates = {
        role.code: role
        for role in Role.objects.filter(organization__isnull=True, is_system=True)
    }
    _grant(RolePermission, templates, permissions, organization_id=None)

    # Las organizaciones ya dadas de alta tienen sus propias copias de las
    # plantillas, y son ésas las que consulta `has_permission`. Sin este
    # recorrido, el criterio de aceptación se cumpliría sólo para las
    # organizaciones que se den de alta a partir de ahora.
    organization_ids = list(Organization.objects.values_list("id", flat=True))

    for organization_id in organization_ids:
        _set_tenant(schema_editor, organization_id)
        clones = {
            role.code: role
            for role in Role.objects.filter(organization_id=organization_id)
        }
        _grant(RolePermission, clones, permissions, organization_id=organization_id)

    _clear_tenant(schema_editor)
    schema_editor.execute(PLATFORM_ON)


def unseed(apps, schema_editor):
    """Quita del catálogo los permisos que creó esta migración.

    Borrar la fila de ``permissions`` arrastra sus ``role_permissions`` por la
    clave foránea, así que no hace falta limpiarlas una por una. Lo que la
    plantilla del paciente ganó y ya existía —``catalog.branch.read``— se
    queda: revertir no debería devolverle al paciente un rol sin permisos.
    """
    Permission = apps.get_model("accounts", "Permission")

    schema_editor.execute(PLATFORM_ON)
    Permission.objects.filter(
        code__in=[code for code, _module, _description in NEW_PERMISSIONS],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_initial"),
        # Las plantillas del sistema y sus permisos los crea el seed del
        # Sprint 0: sin él no hay a qué sumarle nada.
        ("tenancy", "0003_seed_catalog"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
