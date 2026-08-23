"""Catálogo del sistema: planes, permisos y plantillas de rol.

No son datos de prueba: son parte del sistema. Sin las plantillas de rol,
US-43 no tiene qué clonar al dar de alta una organización.

Los precios son marcadores de posición hasta que el Product Owner los defina.
"""

from django.db import migrations

PLANS = [
    {
        "code": "basic", "name": "Básico",
        "description": "Una sucursal, agenda y fichas. Sin inteligencia artificial.",
        "monthly_price": "350.00",
        "max_branches": 1, "max_users": 15, "max_practitioners": 8,
        "max_appointments_month": 800, "max_ai_queries_month": 0,
        "storage_mb": 2048,
        "features": {
            "ai_chatbot": False, "noshow_prediction": False,
            "ai_summaries": False, "report_export": False,
            "online_payment": True,
        },
    },
    {
        "code": "pro", "name": "Pro",
        "description": "Multi-sucursal, reportes exportables y chatbot de orientación.",
        "monthly_price": "890.00",
        "max_branches": 5, "max_users": 60, "max_practitioners": 40,
        "max_appointments_month": 4000, "max_ai_queries_month": 3000,
        "storage_mb": 10240,
        "features": {
            "ai_chatbot": True, "noshow_prediction": False,
            "ai_summaries": False, "report_export": True,
            "online_payment": True,
        },
    },
    {
        "code": "premium", "name": "Premium",
        "description": "Todo lo anterior más predicción de inasistencia y resúmenes por IA.",
        "monthly_price": "1750.00",
        # NULL = ilimitado.
        "max_branches": None, "max_users": None, "max_practitioners": None,
        "max_appointments_month": None, "max_ai_queries_month": None,
        "storage_mb": 51200,
        "features": {
            "ai_chatbot": True, "noshow_prediction": True,
            "ai_summaries": True, "report_export": True,
            "online_payment": True,
        },
    },
]

# Código: <modulo>.<recurso>.<accion>
PERMISSIONS = [
    # Plataforma — sólo el Superadministrador.
    ("platform.organization.create", "platform", "Registrar una nueva organización"),
    ("platform.organization.read", "platform", "Consultar organizaciones"),
    ("platform.organization.update", "platform", "Editar datos de una organización"),
    ("platform.organization.suspend", "platform", "Suspender o reactivar una organización"),
    ("platform.plan.create", "platform", "Crear un plan de suscripción"),
    ("platform.plan.update", "platform", "Editar un plan de suscripción"),
    ("platform.plan.assign", "platform", "Asignar un plan a una organización"),
    ("platform.metric.read", "platform", "Ver el panel de métricas globales"),
    ("platform.alert.read", "platform", "Ver alertas de aislamiento"),
    ("platform.alert.resolve", "platform", "Marcar una alerta como resuelta"),
    # Usuarios y seguridad — organización.
    ("users.user.create", "users", "Crear usuarios en la organización"),
    ("users.user.read", "users", "Consultar usuarios de la organización"),
    ("users.user.update", "users", "Editar usuarios de la organización"),
    ("users.user.deactivate", "users", "Dar de baja un usuario"),
    ("users.role.create", "users", "Crear roles"),
    ("users.role.read", "users", "Consultar roles"),
    ("users.role.update", "users", "Editar roles y sus permisos"),
    ("users.role.assign", "users", "Asignar roles a usuarios"),
    ("users.audit.read", "users", "Consultar la bitácora de auditoría"),
    # Catálogo — Sprint 1, declarados ahora para no migrar dos veces.
    ("catalog.branch.create", "catalog", "Registrar sucursales"),
    ("catalog.branch.read", "catalog", "Consultar sucursales"),
    ("catalog.branch.update", "catalog", "Editar sucursales"),
    # Pacientes.
    ("patients.patient.create", "patients", "Registrar pacientes"),
    ("patients.patient.read", "patients", "Consultar pacientes"),
    ("patients.patient.update", "patients", "Editar pacientes"),
]

ROLES = [
    ("platform_admin", "Superadministrador de Plataforma",
     "Administra organizaciones y planes. Sin acceso a datos clínicos."),
    ("org_admin", "Administrador de Organización",
     "Gestiona usuarios, sucursales, catálogo y reportes de su organización."),
    ("practitioner", "Médico",
     "Atiende pacientes y registra la consulta."),
    ("receptionist", "Recepcionista",
     "Agenda, cobra fichas y registra el check-in."),
    ("patient", "Paciente",
     "Reserva fichas y consulta su propio historial."),
]

# Qué permisos trae cada plantilla. El paciente no lleva ninguno del catálogo
# administrativo: opera sobre sus propios datos, que se resuelve en la vista.
ROLE_PERMISSIONS = {
    "platform_admin": lambda code, module: module == "platform",
    "org_admin": lambda code, module: module in {"users", "catalog", "patients"},
    "receptionist": lambda code, module: code in {
        "patients.patient.create", "patients.patient.read",
        "patients.patient.update", "catalog.branch.read",
    },
    "practitioner": lambda code, module: code in {
        "patients.patient.read", "catalog.branch.read",
    },
    "patient": lambda code, module: False,
}


def seed(apps, schema_editor):
    SubscriptionPlan = apps.get_model("tenancy", "SubscriptionPlan")
    Permission = apps.get_model("accounts", "Permission")
    Role = apps.get_model("accounts", "Role")
    RolePermission = apps.get_model("accounts", "RolePermission")

    # Las plantillas de rol y sus permisos viven a nivel plataforma
    # (organization_id NULL) y su política exige contexto de superadmin. Sin
    # esta línea la migración falla, porque Django la corre como app_user.
    schema_editor.execute("SELECT set_config('app.is_platform_admin', 'on', true)")

    for plan in PLANS:
        SubscriptionPlan.objects.update_or_create(
            code=plan["code"], defaults={k: v for k, v in plan.items() if k != "code"},
        )

    permissions = {}
    for code, module, description in PERMISSIONS:
        permission, _ = Permission.objects.update_or_create(
            code=code, defaults={"module": module, "description": description},
        )
        permissions[code] = permission

    for code, name, description in ROLES:
        role, _ = Role.objects.update_or_create(
            code=code, organization=None,
            defaults={"name": name, "description": description, "is_system": True},
        )
        matches = ROLE_PERMISSIONS[code]
        for permission_code, module, _description in PERMISSIONS:
            if matches(permission_code, module):
                RolePermission.objects.update_or_create(
                    role=role, permission=permissions[permission_code],
                    defaults={"organization": None},
                )


def unseed(apps, schema_editor):
    SubscriptionPlan = apps.get_model("tenancy", "SubscriptionPlan")
    Permission = apps.get_model("accounts", "Permission")
    Role = apps.get_model("accounts", "Role")

    schema_editor.execute("SELECT set_config('app.is_platform_admin', 'on', true)")
    Role.objects.filter(organization__isnull=True, is_system=True).delete()
    Permission.objects.filter(code__in=[c for c, _m, _d in PERMISSIONS]).delete()
    SubscriptionPlan.objects.filter(code__in=[p["code"] for p in PLANS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0002_rls_policies"),
        ("accounts", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
