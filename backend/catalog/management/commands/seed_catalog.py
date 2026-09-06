"""Siembra el catálogo de demostración de una organización.

    python manage.py seed_catalog --organization morita2
    python manage.py seed_catalog --organization morita2 --with-schedules

**Por qué existe.** ``catalog/0004_seed_demo`` ya sembraba las tres sucursales
del caso de estudio, sus especialidades y sus profesionales — pero busca la
organización por el slug fijo ``kolping``, y si no la encuentra **retorna en
silencio**. En la base desplegada las organizaciones se llaman ``kolping3k`` y
``morita2``, así que la migración corrió, no sembró nada y nadie se enteró. El
resultado es que el catálogo queda vacío, y sin profesionales no se pueden
cargar agendas (US-13), lo que deja sin nada que mostrar a la disponibilidad
(US-15) y a la búsqueda (US-16).

Como el ABM web de US-11 y US-12 todavía no existe, sin esto no hay ninguna
forma de cargar el catálogo desde la aplicación.

**Tres cosas que hace distinto de aquella migración:**

1. **Recibe el slug por parámetro** en vez de tenerlo fijo.
2. **Falla ruidosamente** si la organización no existe, y muestra las que sí.
   Un sembrador que no siembra y sale con éxito es peor que uno que falla.
3. Es **idempotente y repetible**: se puede correr las veces que haga falta, y
   dice qué creó y qué ya estaba.

Los datos son **ficticios** (regla 7 del reparto: el repositorio es público).
La duplicación de las constantes respecto de la migración es deliberada: una
migración no debe importar código de la aplicación, porque el código cambia y
la migración tiene que seguir describiendo lo que pasó el día que se aplicó.
"""

import datetime as dt

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization

from ...models import (
    Branch,
    BranchHours,
    Practitioner,
    PractitionerBranch,
    PractitionerSpecialty,
    Specialty,
)

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
WEEKDAYS = [0, 1, 2, 3, 4]

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

# Agenda de demostración: media jornada de mañana, consultas de media hora.
# Cae dentro de la franja 08:00–12:00 de `HOURS`, que es lo que US-13 (d)
# exige.
SCHEDULE_START = dt.time(8, 0)
SCHEDULE_END = dt.time(12, 0)
SLOT_MINUTES = 30
CAPACITY = 1


def _hora(texto):
    return dt.time.fromisoformat(texto)


class Command(BaseCommand):
    help = "Siembra sucursales, especialidades y profesionales de demostración."

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization", required=True,
            help="Slug de la organización a sembrar (por ejemplo: morita2).",
        )
        parser.add_argument(
            "--with-schedules", action="store_true",
            help="Además, una agenda por profesional para que la "
                 "disponibilidad y la búsqueda tengan algo que mostrar.",
        )

    def handle(self, *args, **opciones):
        slug = opciones["organization"]

        # La organización se resuelve con contexto de plataforma: `organizations`
        # está bajo RLS y sin contexto la búsqueda devuelve cero filas — que es
        # justamente como la migración se quedó sin sembrar y sin avisar.
        with platform_admin_context():
            organizacion = Organization.objects.filter(slug=slug).first()
            disponibles = list(Organization.objects.values_list("slug", flat=True))

        if organizacion is None:
            raise CommandError(
                f"No existe una organización con slug «{slug}». "
                f"Las que hay son: {', '.join(disponibles) or '(ninguna)'}."
            )

        # Regla 4 del reparto: fuera del ciclo HTTP, todo va envuelto.
        with tenant_context(organizacion.id):
            resumen = self._sembrar(organizacion, opciones["with_schedules"])

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Catálogo de «{organizacion.name}» ({slug}) listo:"
        ))
        for etiqueta, creados, existentes in resumen:
            self.stdout.write(
                f"  {etiqueta:<18} {creados} creados, {existentes} ya estaban"
            )

    def _sembrar(self, organizacion, con_agendas):
        resumen = []

        with transaction.atomic():
            sucursales, r = self._sucursales(organizacion)
            resumen.append(("sucursales", *r))

            especialidades, r = self._especialidades(organizacion)
            resumen.append(("especialidades", *r))

            profesionales, r = self._profesionales(
                organizacion, sucursales, especialidades,
            )
            resumen.append(("profesionales", *r))

            if con_agendas:
                resumen.append(("agendas", *self._agendas(
                    organizacion, profesionales, sucursales,
                )))

        return resumen

    def _sucursales(self, organizacion):
        sucursales, creados, existentes = {}, 0, 0
        for datos in BRANCHES:
            sucursal, creado = Branch.objects.update_or_create(
                organization=organizacion, name=datos["name"],
                defaults={
                    "address": datos["address"],
                    "phone": datos["phone"],
                    "timezone": datos["timezone"],
                },
            )
            sucursales[datos["name"]] = sucursal
            creados, existentes = creados + creado, existentes + (not creado)

            # El horario de atención, con su corte de mediodía. US-11 (a).
            for weekday in WEEKDAYS:
                for abre, cierra in HOURS:
                    BranchHours.objects.get_or_create(
                        organization=organizacion, branch=sucursal,
                        weekday=weekday, opens_at=_hora(abre),
                        defaults={"closes_at": _hora(cierra)},
                    )
        return sucursales, (creados, existentes)

    def _especialidades(self, organizacion):
        especialidades, creados, existentes = {}, 0, 0
        for nombre, descripcion in SPECIALTIES:
            # La descripción no es decorativa: es el texto que el chatbot del
            # Sprint 4 recuperará por RAG para sugerir la especialidad. US-12 (a).
            especialidad, creado = Specialty.objects.update_or_create(
                organization=organizacion, name=nombre,
                defaults={"description": descripcion},
            )
            especialidades[nombre] = especialidad
            creados, existentes = creados + creado, existentes + (not creado)
        return especialidades, (creados, existentes)

    def _profesionales(self, organizacion, sucursales, especialidades):
        profesionales, creados, existentes = [], 0, 0
        for nombre, apellido, matricula, sus_especialidades, sus_sucursales in PRACTITIONERS:
            profesional, creado = Practitioner.objects.update_or_create(
                organization=organizacion, license_number=matricula,
                defaults={"first_name": nombre, "last_name": apellido},
            )
            creados, existentes = creados + creado, existentes + (not creado)

            # Muchos a muchos con especialidades y con sucursales. La segunda es
            # la que hace posible la disponibilidad consolidada de US-15: sin
            # ella, alguien que atiende en tres sedes serían tres registros.
            for nombre_especialidad in sus_especialidades:
                PractitionerSpecialty.objects.get_or_create(
                    organization=organizacion, practitioner=profesional,
                    specialty=especialidades[nombre_especialidad],
                )
            for nombre_sucursal in sus_sucursales:
                PractitionerBranch.objects.get_or_create(
                    organization=organizacion, practitioner=profesional,
                    branch=sucursales[nombre_sucursal],
                )
            profesionales.append((profesional, sus_sucursales))
        return profesionales, (creados, existentes)

    def _agendas(self, organizacion, profesionales, sucursales):
        """Una agenda por profesional, repartida entre sus sucursales.

        **Los días se reparten, no se repiten.** US-13 (c) prohíbe que un
        profesional tenga dos agendas que se pisen *aunque sean en sucursales
        distintas*, porque no puede estar en dos sedes a la vez. Así que quien
        atiende en tres sedes recibe lunes en una, martes en otra y miércoles en
        la tercera — que además es exactamente el caso que US-15 muestra: la
        disponibilidad consolidada de una persona repartida entre sedes.
        """
        from scheduling.models import Schedule
        from scheduling.validators import (
            validate_no_overlap,
            validate_within_branch_hours,
        )

        hoy = dt.date.today()
        creados = existentes = 0

        for profesional, sus_sucursales in profesionales:
            for indice, weekday in enumerate(WEEKDAYS):
                # Reparto redondo: cada día de la semana cae en una sede
                # distinta, rotando.
                nombre_sucursal = sus_sucursales[indice % len(sus_sucursales)]
                sucursal = sucursales[nombre_sucursal]

                # Si ya está sembrada, se salta **antes** de validar. Sin esto
                # el comando no sería repetible: la comprobación de solapamiento
                # encontraría la agenda que él mismo creó la vez anterior y
                # fallaría acusándola de pisarse consigo misma.
                if Schedule.objects.filter(
                    organization=organizacion, practitioner=profesional,
                    branch=sucursal, weekday=weekday,
                    start_time=SCHEDULE_START, end_time=SCHEDULE_END,
                ).exists():
                    existentes += 1
                    continue

                # Se valida con las mismas reglas que la vista de US-13. Si
                # alguien cambia estas constantes por algo que se pisa o que se
                # sale del horario de la sucursal, el comando falla acá y no
                # deja datos inválidos sembrados.
                validate_within_branch_hours(
                    organization=organizacion, branch_id=sucursal.id,
                    weekday=weekday, start_time=SCHEDULE_START,
                    end_time=SCHEDULE_END,
                )
                validate_no_overlap(
                    organization=organizacion, practitioner_id=profesional.id,
                    weekday=weekday, start_time=SCHEDULE_START,
                    end_time=SCHEDULE_END, valid_from=hoy, valid_until=None,
                    exclude_id=None,
                )

                Schedule.objects.create(
                    organization=organizacion, practitioner=profesional,
                    branch=sucursal, weekday=weekday,
                    start_time=SCHEDULE_START, end_time=SCHEDULE_END,
                    slot_minutes=SLOT_MINUTES, capacity=CAPACITY,
                    valid_from=hoy,
                )
                creados += 1

        return creados, existentes
