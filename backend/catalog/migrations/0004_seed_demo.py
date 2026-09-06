"""Datos de demostración del catálogo, cargados por migración y no a mano
(US-11 f). Todos ficticios (regla 7 del reparto).

Sólo toca la organización del caso de estudio (`kolping`) si existe: en una
base sin ella —o en producción— la migración no hace nada. Es idempotente
(`update_or_create`), así que volver a correrla no duplica.
"""

import datetime as dt

from django.db import migrations

SLUG_CASO_DE_ESTUDIO = "kolping"

BRANCHES = [
    {"name": "Sede Centro", "address": "Calle Bolívar 123",
     "phone": "4-6600100", "timezone": "America/La_Paz"},
    {"name": "Sede Norte", "address": "Av. América 4500",
     "phone": "4-6600200", "timezone": "America/La_Paz"},
    {"name": "Sede Sur", "address": "Av. Panamericana Km 4",
     "phone": "4-6600300", "timezone": "America/La_Paz"},
]

# Horario típico con corte de mediodía, de lunes a viernes.
HOURS = [("08:00", "12:00"), ("14:00", "18:00")]

SPECIALTIES = [
    ("Medicina general", "Atención clínica de primer contacto y controles."),
    ("Cardiología", "Corazón y sistema circulatorio."),
    ("Pediatría", "Salud de niñas y niños hasta la adolescencia."),
    ("Dermatología", "Piel, cabello y uñas."),
    ("Ginecología", "Salud reproductiva y control ginecológico."),
]

PRACTITIONERS = [
    ("Laura", "Gómez", "MP-1001", ["Cardiología", "Medicina general"],
     ["Sede Centro", "Sede Norte"]),
    ("Marta", "González", "MP-1002", ["Pediatría"],
     ["Sede Centro", "Sede Sur"]),
    ("Juan", "Pérez", "MP-1003", ["Dermatología"],
     ["Sede Norte"]),
    ("Diego", "Ríos", "MP-1004", ["Medicina general", "Ginecología"],
     ["Sede Centro", "Sede Norte", "Sede Sur"]),
]


def seed(apps, schema_editor):
    Organization = apps.get_model("tenancy", "Organization")
    Branch = apps.get_model("catalog", "Branch")
    BranchHours = apps.get_model("catalog", "BranchHours")
    Specialty = apps.get_model("catalog", "Specialty")
    Practitioner = apps.get_model("catalog", "Practitioner")
    PractitionerSpecialty = apps.get_model("catalog", "PractitionerSpecialty")
    PractitionerBranch = apps.get_model("catalog", "PractitionerBranch")

    schema_editor.execute("SELECT set_config('app.is_platform_admin', 'on', true)")
    organizacion = Organization.objects.filter(slug=SLUG_CASO_DE_ESTUDIO).first()
    schema_editor.execute("SELECT set_config('app.is_platform_admin', '', true)")
    if organizacion is None:
        return

    schema_editor.execute(
        "SELECT set_config('app.tenant_id', %s, true)", [str(organizacion.id)],
    )

    sucursales = {}
    for datos in BRANCHES:
        sucursal, _ = Branch.objects.update_or_create(
            organization=organizacion, name=datos["name"],
            defaults={
                "address": datos["address"], "phone": datos["phone"],
                "timezone": datos["timezone"], "is_active": True,
            },
        )
        sucursales[datos["name"]] = sucursal
        for weekday in range(5):  # lunes a viernes
            for abre, cierra in HOURS:
                BranchHours.objects.get_or_create(
                    organization=organizacion, branch=sucursal,
                    weekday=weekday, opens_at=abre, closes_at=cierra,
                )

    especialidades = {}
    for nombre, descripcion in SPECIALTIES:
        especialidad, _ = Specialty.objects.update_or_create(
            organization=organizacion, name=nombre,
            defaults={"description": descripcion, "is_active": True},
        )
        especialidades[nombre] = especialidad

    for first_name, last_name, matricula, sus_especialidades, sus_sedes in PRACTITIONERS:
        profesional, _ = Practitioner.objects.update_or_create(
            organization=organizacion, license_number=matricula,
            defaults={
                "first_name": first_name, "last_name": last_name,
                "is_active": True,
                "search_name": f"{first_name} {last_name}".lower(),
            },
        )
        for nombre in sus_especialidades:
            PractitionerSpecialty.objects.get_or_create(
                organization=organizacion, practitioner=profesional,
                specialty=especialidades[nombre],
            )
        for nombre in sus_sedes:
            PractitionerBranch.objects.get_or_create(
                organization=organizacion, practitioner=profesional,
                branch=sucursales[nombre],
            )

    schema_editor.execute("SELECT set_config('app.tenant_id', '', true)")


def unseed(apps, schema_editor):
    # La demo no se borra sola: si alguien la quiere fuera, que lo haga a mano.
    # Dejar `noop` evita romper una base donde ya se construyó encima.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_rls_policies"),
        ("tenancy", "0003_seed_catalog"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
