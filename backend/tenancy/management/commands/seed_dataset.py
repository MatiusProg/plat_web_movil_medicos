"""Dataset de demostración: seis organizaciones completas.

    python manage.py seed_dataset --password '<clave común de demostración>'
    python manage.py seed_dataset --dry-run
    python manage.py seed_dataset --enrich morita2 --enrich kolping3k
    python manage.py seed_dataset --history morita2 --history kolping3k

El modo `--enrich` nutre organizaciones que **ya existen** (las de los
primeros sprints, que sólo tenían el catálogo de `seed_catalog`): servicios,
cuentas para sus profesionales, recepción, pacientes y fichas con su
atención. **Sólo agrega**: no modifica ni borra nada de lo que tienen, no
crea especialidades, y las fichas nuevas se reparten sólo entre los
pacientes nuevos —los que ya estaban pueden ser cuentas de prueba de alguien
del equipo—.

**La inasistencia tiene causas (US-35).** El desenlace de cada ficha pasada ya
no se sortea 78/12/10 al azar: una ficha se cancela con ~10 % de probabilidad
y, si no, el paciente se ausenta con la probabilidad que da
`_causas_inasistencia.probabilidad_ausencia` —días de anticipación, pago por
adelantado, faltas previas del paciente, día de la semana y hora—. Los turnos
se deciden en orden cronológico, así que las «faltas previas» son las
anteriores de verdad, y `created_at` de cada ficha queda en la fecha de la
reserva (anticipación real), no en la del alta. Quien pagó por adelantado
tiene un pago simulado hecho al reservar (con 24 h o más de margen); el resto,
un pago en efectivo minutos antes del turno. Un modelo de riesgo entrenado
con esto tiene algo que aprender.

**`--history SLUG`: más historial para una organización que ya tiene datos.**
Agrega fichas pasadas en la ventana de hace 210 a hace 61 días (con las mismas
causas, y las atendidas con su atención firmada), repartidas sólo entre los
pacientes que la organización ya tiene. Usa las agendas activas tal cual
—día, horas y duración del turno— pero ignora su `valid_from` y no las
modifica. Es idempotente: si la organización ya tiene alguna ficha de hace más
de 60 días, no hace nada y lo informa. **Sólo agrega.** No se puede
«repoblar» borrando las fichas viejas para volver a sembrarlas: las atenciones
firmadas tienen triggers (US-24/26) que prohíben el `DELETE`, y con razón.

**Un límite que conviene saber.** Esto agrega historial *por detrás* de lo que
ya hay, y lo ya sembrado no sabe de él: sus «faltas previas» empezaron en cero.
Si lo ya sembrado es del generador viejo (desenlaces al azar) o del nuevo sin
historial, el modelo ve ausencias que el generador no usó como causa y puede
quedar rechazado por descalibrado. Para una organización **nueva** no hace
falta: `fichas()` siembra `DIAS_DE_HISTORIA` días en una sola pasada. `--history`
es para una organización que ya existe y todavía no tiene fichas de hace más de
60 días.

Puebla la plataforma con seis centros médicos ficticios que se pueden
recorrer de punta a punta: sucursales con horario, especialidades,
profesionales con agenda, servicios con precio y preparación, recepción,
pacientes con cuenta y dependientes, antecedentes, fichas pasadas y futuras, y
la atención firmada de las fichas atendidas.

**Por qué existe.** `seed_catalog` siembra el catálogo de una organización;
esto arma organizaciones enteras, con historia. Sin fichas pasadas no hay qué
mostrar en el historial de US-25, ni en los reportes, ni datos de asistencia e
inasistencia para el modelo del Sprint 4 (US-35 a US-38).

**Cuatro reglas:**

1. **Cada organización nace por el mismo camino que desde la pantalla**:
   `tenancy.services.create_organization` (US-43), con sus roles copiados, su
   suscripción y su administrador. Un dataset que se saltea el alta prueba
   otra cosa que la aplicación.
2. **Sólo las especialidades que ya tienen referencia médica** (las 14 de
   `assistant/medical_reference.py`). Con Gemini, el asistente las reconoce
   aunque la descripción del centro sea breve.
3. **Datos ficticios** (regla 7: el repositorio es público). Correos en
   `.test`, documentos y teléfonos inventados.
4. **La clave no se versiona.** Todas las cuentas comparten la clave que se
   pasa por `--password` o por la variable `DATASET_PASSWORD`. El comando no
   tiene ninguna escrita.

**Es repetible:** una organización cuyo slug ya existe se saltea entera, sin
tocarla. Para volver a sembrarla hay que darla de baja primero.

**Después de correrlo hay que reindexar el asistente**, de a una organización
(`embed_catalog --organization <slug>`): el plan gratuito de Gemini permite
100 embeddings por minuto y `--all` se queda sin cuota a mitad de camino.
"""

import datetime as dt
import random
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Role, User, UserRole
from appointments.models import Appointment
from catalog.models import (
    Branch, BranchHours, Practitioner, PractitionerBranch,
    PractitionerSpecialty, Service, Specialty,
)
from encounters.models import Encounter
from patients.models import Patient, PatientHistoryEntry
from payments.models import Payment
from scheduling.models import Schedule
from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization, SubscriptionPlan
from tenancy.services import create_organization

from ._causas_inasistencia import (
    HISTORIAL_DESDE_DIAS, HISTORIAL_HASTA_DIAS, probabilidad_ausencia,
)

LA_PAZ = "America/La_Paz"

# --------------------------------------------------------------------------
#  Las seis organizaciones
# --------------------------------------------------------------------------

ORGANIZATIONS = [
    {
        "slug": "sangabriel", "name": "Clínica San Gabriel",
        "legal_name": "Clínica San Gabriel S.R.L.", "tax_id": "900100101",
        "city": "La Paz", "address": "Av. 6 de Agosto 2450", "plan": "premium",
        "branches": [("Sede Sopocachi", "Av. 6 de Agosto 2450", "2-2410100", True),
                     ("Sede Miraflores", "Av. Busch 1180", "2-2220200", False),
                     ("Sede Calacoto", "Calle 21 de Calacoto 8100", "2-2790300", True)],
        "specialties": ["Medicina general", "Cardiología", "Pediatría", "Ginecología",
                        "Dermatología", "Neurología", "Traumatología", "Oftalmología"],
    },
    {
        "slug": "losandes", "name": "Centro Médico Los Andes",
        "legal_name": "Centro Médico Los Andes S.A.", "tax_id": "900100202",
        "city": "El Alto", "address": "Av. Juan Pablo II 3300", "plan": "pro",
        "branches": [("Sede Ceja", "Av. Juan Pablo II 3300", "2-2820100", True),
                     ("Sede Villa Adela", "Av. Bolivia 1500", "2-2850200", False)],
        "specialties": ["Medicina general", "Pediatría", "Ginecología",
                        "Neumología", "Gastroenterología", "Traumatología"],
    },
    {
        "slug": "scsalud", "name": "Policlínico Santa Cruz Salud",
        "legal_name": "Santa Cruz Salud S.R.L.", "tax_id": "900100303",
        "city": "Santa Cruz", "address": "Av. Monseñor Rivero 410", "plan": "premium",
        "branches": [("Sede Centro", "Av. Monseñor Rivero 410", "3-3330100", True),
                     ("Sede Equipetrol", "Av. San Martín 2200", "3-3410200", True),
                     ("Sede Plan Tres Mil", "Av. Paurito 900", "3-3620300", False)],
        "specialties": ["Medicina general", "Cardiología", "Endocrinología",
                        "Pediatría", "Ginecología", "Urología",
                        "Otorrinolaringología", "Dermatología", "Psicología"],
    },
    {
        "slug": "delvalle", "name": "Clínica del Valle",
        "legal_name": "Clínica del Valle Ltda.", "tax_id": "900100404",
        "city": "Cochabamba", "address": "Av. Heroínas 650", "plan": "pro",
        "branches": [("Sede Centro", "Av. Heroínas 650", "4-4250100", True),
                     ("Sede Quillacollo", "Av. Blanco Galindo km 13", "4-4260200", False)],
        "specialties": ["Medicina general", "Pediatría", "Gastroenterología",
                        "Neurología", "Psicología", "Oftalmología", "Urología"],
    },
    {
        "slug": "chuquisaca", "name": "Centro de Salud Chuquisaca",
        "legal_name": "Centro de Salud Chuquisaca S.R.L.", "tax_id": "900100505",
        "city": "Sucre", "address": "Calle Bolívar 320", "plan": "basic",
        "branches": [("Sede Central", "Calle Bolívar 320", "4-6450100", True),
                     ("Sede Mercado Campesino", "Av. Jaime Mendoza 1100", "4-6460200", False)],
        "specialties": ["Medicina general", "Pediatría", "Ginecología",
                        "Endocrinología", "Otorrinolaringología", "Traumatología"],
    },
    # US-35: la organización para mostrar el riesgo de inasistencia. Premium
    # (el único plan que incluye `noshow_prediction`) y sembrada con las causas
    # de ausencia en una sola pasada, así que su modelo aprende. Las que se
    # sembraron antes de US-35 tienen los desenlaces al azar.
    {
        "slug": "urbari", "name": "Clínica Urbari",
        "legal_name": "Clínica Urbari S.R.L.", "tax_id": "900100606",
        "city": "Santa Cruz", "address": "Av. Banzer, 4.º Anillo 1850", "plan": "premium",
        "branches": [("Sede Central", "Av. Banzer, 4.º Anillo 1850", "3-3440100", True),
                     ("Sede Norte", "Av. Virgen de Cotoca 2210", "3-3440200", True),
                     ("Sede Sur", "Av. Santos Dumont 3900", "3-3440300", False)],
        "specialties": ["Medicina general", "Pediatría", "Cardiología", "Ginecología",
                        "Endocrinología", "Traumatología", "Dermatología", "Neumología"],
    },
]

# Descripción breve de cada especialidad, con palabras de paciente. La
# referencia médica de Karen completa el resto cuando el proveedor es Gemini.
SPECIALTY_TEXT = {
    "Medicina general": "Consulta de primer contacto para adultos. Fiebre, gripe, dolor de cabeza, dolor de estómago, cansancio, chequeos y certificados.",
    "Cardiología": "Corazón y presión arterial. Palpitaciones, presión alta, falta de aire al caminar, hinchazón de pies y control de colesterol.",
    "Pediatría": "Salud de bebés, niñas y niños. Fiebre, tos, diarrea, vacunas y control de crecimiento.",
    "Ginecología": "Salud de la mujer. Control anual, Papanicolaou, menstruación irregular, anticonceptivos y control del embarazo.",
    "Dermatología": "Piel, cabello y uñas. Manchas, acné, picazón, caída del cabello, hongos y lunares que cambian.",
    "Neurología": "Cerebro y nervios. Dolores de cabeza fuertes o frecuentes, mareos, hormigueos, temblores y pérdida de memoria.",
    "Traumatología": "Huesos, músculos y articulaciones. Golpes, torceduras, dolor de rodilla, espalda u hombro, y fracturas.",
    "Oftalmología": "Ojos y visión. Ver borroso, ojos rojos o irritados, control de la vista y lentes.",
    "Neumología": "Pulmones y respiración. Tos que no se va, silbido en el pecho, asma y falta de aire.",
    "Gastroenterología": "Estómago e intestinos. Acidez, gastritis, dolor abdominal, estreñimiento, diarrea frecuente e hinchazón.",
    "Endocrinología": "Hormonas y metabolismo. Diabetes, tiroides, sobrepeso y control del azúcar en la sangre.",
    "Urología": "Riñones, vejiga y próstata. Ardor al orinar, orinar muy seguido, cálculos y control de próstata.",
    "Otorrinolaringología": "Oído, nariz y garganta. Dolor de oído, sinusitis, ronquera, amígdalas y pérdida de audición.",
    "Psicología": "Salud emocional. Ansiedad, tristeza que no pasa, estrés, problemas para dormir y acompañamiento en momentos difíciles.",
}

# Servicios por especialidad: (nombre, tipo, precio en Bs o None, preparación).
SERVICES = {
    None: [
        ("Consulta de Medicina general", "consultation", 100, ""),
        ("Consulta de especialidad", "consultation", 150, "Traé tus estudios anteriores si los tenés."),
        ("Análisis de sangre (hemograma y glucosa)", "study", 80,
         "Ayuno de 8 horas: no comer nada desde la noche anterior, sólo agua."),
        ("Examen general de orina", "study", 40,
         "Primera orina de la mañana, en un frasco estéril que se entrega en la sucursal."),
    ],
    "Cardiología": [("Electrocardiograma", "study", 90, "No requiere ayuno. Venir con ropa cómoda."),
                    ("Perfil lipídico", "study", 120, "Ayuno de 12 horas. Sin alcohol el día anterior.")],
    "Ginecología": [("Papanicolaou", "study", 70, "No estar menstruando. Sin relaciones sexuales las 48 horas anteriores."),
                    ("Ecografía obstétrica", "study", 200, "Vejiga llena: tomar cuatro vasos de agua una hora antes.")],
    "Dermatología": [("Crioterapia de verrugas", "procedure", None, "")],
    "Traumatología": [("Radiografía simple", "study", 120, "Sacarse collares, aros y objetos metálicos.")],
    "Oftalmología": [("Medición de la vista", "study", 60, "Si usás lentes, traelos.")],
    "Gastroenterología": [("Ecografía abdominal", "study", 180, "Ayuno de 6 horas y la vejiga llena.")],
    "Endocrinología": [("Hemoglobina glicosilada", "study", 110, "No requiere ayuno.")],
    "Urología": [("Ecografía renal y vesical", "study", 170, "Vejiga llena: tomar un litro de agua una hora antes.")],
    "Neumología": [("Espirometría", "study", 150, "No fumar 4 horas antes. Sin comidas pesadas.")],
    "Otorrinolaringología": [("Audiometría", "study", 130, "Evitar ruidos fuertes el día anterior.")],
    "Psicología": [("Sesión de psicología", "consultation", 130, "")],
}

FIRST_NAMES_F = ["María", "Ana", "Lucía", "Carla", "Daniela", "Gabriela", "Paola", "Fernanda",
                 "Valeria", "Rocío", "Silvia", "Patricia", "Andrea", "Mónica", "Claudia", "Jimena"]
FIRST_NAMES_M = ["Juan", "Carlos", "Luis", "Jorge", "Diego", "Marco", "Andrés", "Javier",
                 "Fernando", "Sergio", "Ricardo", "Álvaro", "Gonzalo", "Mauricio", "Rodrigo", "Pablo"]
LAST_NAMES = ["Mamani", "Quispe", "Condori", "Flores", "Vargas", "Rojas", "Gutiérrez", "Choque",
              "Fernández", "Mendoza", "Torrez", "Apaza", "Salazar", "Rivera", "Aguilar", "Villca",
              "Copa", "Huanca", "Pérez", "Ortiz", "Castro", "Limachi", "Méndez", "Zeballos"]

ALLERGIES = [("Penicilina", "severe"), ("Ibuprofeno", "moderate"), ("Mariscos", "anaphylactic"),
             ("Polen", "mild"), ("Sulfas", "moderate")]
CONDITIONS = ["Hipertensión arterial", "Diabetes tipo 2", "Asma", "Hipotiroidismo", "Gastritis crónica"]
MEDICATIONS = ["Enalapril 10 mg", "Metformina 850 mg", "Salbutamol inhalador", "Levotiroxina 50 mcg"]

# Lo que se escribe en la atención firmada, por especialidad.
CLINICAL = {
    "Medicina general": ("Fiebre y dolor de garganta desde hace dos días.", "Faringitis aguda.", "Paracetamol 500 mg cada 8 horas por 3 días."),
    "Cardiología": ("Control de presión arterial.", "Hipertensión arterial controlada.", "Continuar con su medicación habitual."),
    "Pediatría": ("Tos y mocos hace una semana.", "Resfrío común.", "Lavados nasales y abundante líquido."),
    "Ginecología": ("Control ginecológico anual.", "Control normal.", "Papanicolaou anual."),
    "Dermatología": ("Granos en la cara que no mejoran.", "Acné moderado.", "Limpieza facial dos veces al día."),
    "Neurología": ("Dolor de cabeza frecuente.", "Cefalea tensional.", "Higiene del sueño y control en un mes."),
    "Traumatología": ("Dolor de rodilla al subir escaleras.", "Esguince leve de rodilla.", "Reposo relativo y hielo local."),
    "Oftalmología": ("Ve borroso de lejos.", "Miopía leve.", "Uso de lentes recetados."),
    "Neumología": ("Silbido en el pecho por las noches.", "Asma leve.", "Inhalador de rescate según necesidad."),
    "Gastroenterología": ("Acidez después de comer.", "Gastritis.", "Evitar comidas irritantes."),
    "Endocrinología": ("Control de azúcar.", "Diabetes tipo 2 compensada.", "Continuar dieta y control en tres meses."),
    "Urología": ("Ardor al orinar.", "Infección urinaria baja.", "Abundante líquido y control con examen de orina."),
    "Otorrinolaringología": ("Dolor de oído derecho.", "Otitis externa.", "Mantener el oído seco."),
    "Psicología": ("Ansiedad por el trabajo.", "Trastorno de ansiedad leve.", "Sesiones semanales y técnicas de respiración."),
}

OPENING_HOURS = [("08:00", "12:00"), ("14:00", "19:00")]
SATURDAY_HOURS = [("08:00", "12:00")]
SLOT_MINUTES = 30

# Doscientos cincuenta pacientes por centro, sesenta con cuenta en la
# aplicación. Con la ocupación de abajo quedan unas siete u ocho fichas por
# paciente en seis meses: lo bastante para que el historial de US-25 tenga
# varias atenciones, sin que cada paciente viva en el consultorio.
#
# El número importa para US-35. Con cien pacientes y seis meses de fichas
# (unas 21 por paciente) todos acumulaban faltas hasta saturar el riesgo: el
# 55 % de las fichas futuras salía en nivel «alto» y la tasa de ausencia subía
# al 23 % en lo más reciente. Un nivel que marca a más de la mitad no sirve para
# priorizar. Con 250 la tasa base es ~12 % y los niveles se reparten ~22 % alto,
# ~17 % medio y ~61 % bajo (medido sobre `urbari`).
PATIENTS = 250
PATIENTS_WITH_ACCOUNT = 60
OCCUPANCY_PAST = 0.25
OCCUPANCY_FUTURE = 0.18

# Cuánto pasado siembra una organización nueva, **en una sola pasada** (US-35).
# No son dos ventanas pegadas a propósito: las «faltas previas» de un paciente
# son una causa de su próxima ausencia, y sólo valen si el generador las contó
# desde el principio. Con el pasado reciente por un lado y el historial por el
# otro, el modelo veía faltas que el generador no había usado y se descalibraba
# (predecía 24 % de ausencias donde había 16 %, y quedaba rechazado). Medido
# sobre `losandes`: con una sola pasada, las dos mitades del tiempo se
# explican con el mismo modelo.
DIAS_DE_HISTORIA = 180

# Lo que no depende de causas: una ficha se cancela con ~10 % de probabilidad,
# sin importar nada más (una cancelación no es una ausencia: el turno se libera).
TASA_CANCELACION = 0.10
# Cuánta gente paga al reservar, si la reserva tiene 24 h o más de margen.
PAGO_ADELANTADO = 0.65
# Peso de cada día de anticipación, de 0 a 40: lo normal es reservar de 1 a 14
# días antes; hay menos reservas a último momento y pocas con más de dos semanas.
PESOS_ANTICIPACION = [3] + [6] * 14 + [1.5] * 26
# Un pago por adelantado tiene que quedar al menos 24 h antes del turno. El pago
# llega hasta 30 min después de reservar, así que hacen falta 24 h y 30 min.
MINUTOS_MIN_ADELANTO = 24 * 60 + 30


def _t(texto):
    return dt.time.fromisoformat(texto)


class Sembrador:
    """Todo lo que se siembra dentro de una organización ya existente.

    Lo usan los dos modos del comando: el alta completa de una organización
    nueva y el `--enrich` de una que ya existe. **Nunca modifica ni borra**:
    sólo agrega, y cada paso mira primero qué hay.
    """

    def __init__(self, organizacion, hash_clave, superadmin, admin):
        self.org = organizacion
        self.rnd = random.Random(organizacion.slug)   # determinista por organización
        self.hash = hash_clave
        self.superadmin = superadmin
        self.admin = admin
        self.dominio = f"{organizacion.slug}.test"
        self.roles = {r.code: r for r in Role.objects.filter(organization=organizacion)}
        self.hoy = timezone.now().astimezone(ZoneInfo(LA_PAZ)).date()
        usados = set(User.objects.filter(organization=organizacion)
                     .values_list("document_number", flat=True))
        usados |= set(Patient.objects.filter(organization=organizacion)
                      .exclude(document_number=None).values_list("document_number", flat=True))
        base = int((organizacion.tax_id or "100")[-3:]) * 100000 + 10
        self._docs = (str(n) for n in range(base, 10**9) if str(n) not in usados)
        self.resumen = {}

    def _contar(self, clave, n=1):
        self.resumen[clave] = self.resumen.get(clave, 0) + n

    def persona(self, sexo=None):
        sexo = sexo or self.rnd.choice("FM")
        nombre = self.rnd.choice(FIRST_NAMES_F if sexo == "F" else FIRST_NAMES_M)
        return nombre, f"{self.rnd.choice(LAST_NAMES)} {self.rnd.choice(LAST_NAMES)}", sexo

    def _correo_libre(self, prefijo):
        """`prefijo1@…`, `prefijo2@…`: el primero que no exista."""
        n = 1
        while User.objects.filter(organization=self.org,
                                  email__iexact=f"{prefijo}{n}@{self.dominio}").exists():
            n += 1
        return f"{prefijo}{n}@{self.dominio}"

    def cuenta(self, nombre, apellido, rol, prefijo):
        usuario = User.objects.create_user(
            email=self._correo_libre(prefijo), organization=self.org,
            first_name=nombre, last_name=apellido, document_number=next(self._docs),
            phone=f"7{self.rnd.randint(1000000, 9999999)}",
        )
        User.objects.filter(pk=usuario.pk).update(password=self.hash)
        UserRole.objects.create(user=usuario, role=self.roles[rol], organization=self.org,
                                assigned_by=self.superadmin)
        return usuario

    # ---- Catálogo -------------------------------------------------------

    def sucursales(self, lista):
        for nombre, direccion, telefono, sabado in lista:
            sede = Branch.objects.create(organization=self.org, name=nombre,
                                         address=direccion, phone=telefono, timezone=LA_PAZ)
            for dia in range(5):
                for abre, cierra in OPENING_HOURS:
                    BranchHours.objects.create(organization=self.org, branch=sede, weekday=dia,
                                               opens_at=_t(abre), closes_at=_t(cierra))
            if sabado:
                for abre, cierra in SATURDAY_HOURS:
                    BranchHours.objects.create(organization=self.org, branch=sede, weekday=5,
                                               opens_at=_t(abre), closes_at=_t(cierra))
            self._contar("sucursales")

    def especialidades(self, nombres):
        for n in nombres:
            Specialty.objects.create(organization=self.org, name=n, description=SPECIALTY_TEXT[n])
            self._contar("especialidades")

    def servicios(self):
        """Sólo si la organización no tiene ninguno: no se pisa lo que cargó."""
        if Service.objects.filter(organization=self.org).exists():
            return
        especialidades = {s.name: s for s in Specialty.objects.filter(organization=self.org)}
        for clave_esp, lista in SERVICES.items():
            if clave_esp is not None and clave_esp not in especialidades:
                continue
            for nombre, tipo, precio, prep in lista:
                # El precio varía un poco entre centros, como en la vida real.
                ajuste = Decimal(self.rnd.choice([0, 0, 10, -10, 20]))
                Service.objects.create(
                    organization=self.org, name=nombre, kind=tipo,
                    specialty=especialidades.get(clave_esp),
                    price=None if precio is None else Decimal(precio) + ajuste,
                    preparation=prep,
                )
                self._contar("servicios")

    # ---- Personal -------------------------------------------------------

    def recepcion(self):
        """Una persona de recepción por sede, si no hay nadie con ese rol."""
        if UserRole.objects.filter(organization=self.org, role__code="receptionist").exists():
            return
        for _sede in Branch.objects.filter(organization=self.org, is_active=True):
            n, a, _s = self.persona()
            self.cuenta(n, a, "receptionist", "recepcion")
            self._contar("recepción")

    def cuentas_de_profesionales(self):
        """Cuenta y rol Médico para los profesionales que no tienen.

        Sin cuenta no pueden entrar a registrar la atención (US-24), y la
        atención firmada necesita quién la firmó.
        """
        for prof in Practitioner.objects.filter(organization=self.org, user__isnull=True):
            usuario = self.cuenta(prof.first_name, prof.last_name, "practitioner", "medico")
            prof.user = usuario
            prof.save()
            self._contar("cuentas de profesionales")

    def profesional(self, nombre_esp, sedes, matricula):
        """Un profesional nuevo con cuenta y agenda en una o dos sedes."""
        n, a, _s = self.persona()
        usuario = self.cuenta(n, a, "practitioner", "medico")
        prof = Practitioner.objects.create(
            organization=self.org, user=usuario, first_name=n, last_name=a,
            license_number=matricula,
        )
        PractitionerSpecialty.objects.create(
            organization=self.org, practitioner=prof,
            specialty=Specialty.objects.get(organization=self.org, name=nombre_esp),
        )
        # Días distintos en cada sede: nunca dos agendas el mismo día (US-13 c).
        sus_sedes = self.rnd.sample(sedes, k=min(len(sedes), self.rnd.choice([1, 2, 2])))
        for j, dia in enumerate(self.rnd.sample(range(5), k=4)):
            sede = sus_sedes[j % len(sus_sedes)]
            PractitionerBranch.objects.get_or_create(organization=self.org,
                                                     practitioner=prof, branch=sede)
            manana = self.rnd.random() < 0.6
            Schedule.objects.create(
                organization=self.org, practitioner=prof, branch=sede, weekday=dia,
                start_time=_t("08:00" if manana else "14:00"),
                end_time=_t("12:00" if manana else "18:00"),
                slot_minutes=SLOT_MINUTES,
                valid_from=self.hoy - dt.timedelta(days=DIAS_DE_HISTORIA),
            )
        self._contar("profesionales")
        return prof

    # ---- Pacientes ------------------------------------------------------

    def pacientes(self, cantidad, con_cuenta):
        """Pacientes nuevos, con antecedentes y algunos hijos a cargo.

        Devuelve sólo los creados acá: las fichas se reparten entre ellos y
        no entre los pacientes que la organización ya tenía, que pueden ser
        cuentas de prueba de alguien del equipo.
        """
        nuevos = []
        for i in range(1, cantidad + 1):
            n, a, s = self.persona()
            usuario = self.cuenta(n, a, "patient", "paciente") if i <= con_cuenta else None
            pac = Patient.objects.create(
                organization=self.org, user=usuario, document_type=Patient.DocumentType.CI,
                document_number=usuario.document_number if usuario else next(self._docs),
                first_name=n, last_name=a, sex=s,
                birth_date=self.hoy - dt.timedelta(days=self.rnd.randint(18 * 365, 80 * 365)),
                phone=f"7{self.rnd.randint(1000000, 9999999)}",
            )
            nuevos.append(pac)
            if usuario and i % 3 == 0:
                hn, _ha, hs = self.persona()
                nuevos.append(Patient.objects.create(
                    organization=self.org, guardian=pac, relationship="child",
                    first_name=hn, last_name=a, sex=hs,
                    birth_date=self.hoy - dt.timedelta(days=self.rnd.randint(365, 12 * 365)),
                ))
            if self.rnd.random() < 0.35:
                alergia, gravedad = self.rnd.choice(ALLERGIES)
                PatientHistoryEntry.objects.create(organization=self.org, patient=pac,
                                                   kind="allergy", description=alergia,
                                                   severity=gravedad)
            if self.rnd.random() < 0.3:
                PatientHistoryEntry.objects.create(organization=self.org, patient=pac,
                                                   kind="condition",
                                                   description=self.rnd.choice(CONDITIONS))
            if self.rnd.random() < 0.2:
                PatientHistoryEntry.objects.create(organization=self.org, patient=pac,
                                                   kind="medication",
                                                   description=self.rnd.choice(MEDICATIONS))
        self._contar("pacientes", len(nuevos))
        return nuevos

    # ---- Fichas y atenciones -------------------------------------------

    def fichas(self, pacientes):
        """Ocupa una parte de los turnos de cada agenda, de 180 días atrás a 14 adelante.

        Sólo si la organización no tiene ninguna ficha todavía: es lo que
        hace repetible al `--enrich`. Respeta la vigencia de cada agenda, así
        que a una organización que ya existía le siembra lo que sus agendas
        cubren. Todo el pasado sale **en una sola pasada cronológica**
        (`DIAS_DE_HISTORIA`): las faltas previas de cada paciente son una
        causa, y sólo valen si se contaron desde el principio.
        Lo pasado queda con desenlace —atendida (con su atención firmada),
        ausente o cancelada—, que es justo el dato que el modelo de
        inasistencia del Sprint 4 necesita; cómo se decide, en `_crear_fichas`.
        Lo futuro queda confirmado o pendiente de pago.
        """
        if Appointment.objects.filter(organization=self.org).exists() or not pacientes:
            return
        ahora = timezone.now()
        turnos = self._turnos(self.hoy - dt.timedelta(days=DIAS_DE_HISTORIA),
                              self.hoy + dt.timedelta(days=14), ahora,
                              respetar_vigencia=True)
        self._crear_fichas(turnos, pacientes, ahora)

    def historial(self):
        """Agrega fichas pasadas (US-35) a una organización que ya tiene datos.

        Usa la ventana `[hoy - 210 d, hoy - 61 d]`, las mismas causas de
        ausencia y **sólo los pacientes que la organización ya tiene**. Las
        agendas se usan tal cual (día de la semana, horas, duración del
        turno), pero se ignora su `valid_from`: la ficha de hace seis meses
        nunca existió en la agenda de hoy y no hay por qué tocar la agenda
        para sembrarla.

        Es idempotente: si la organización ya tiene alguna ficha de hace más
        de 60 días, no hace nada. Eso cubre tanto la segunda corrida como una
        organización cuyo historial real ya empezó antes.
        """
        tz = ZoneInfo(LA_PAZ)
        corte = dt.datetime.combine(self.hoy - dt.timedelta(days=60), dt.time.min, tzinfo=tz)
        if Appointment.objects.filter(organization=self.org, starts_at__lt=corte).exists():
            self.resumen["historial"] = "ya hay fichas de hace más de 60 días: no se agrega nada"
            return
        pacientes = list(Patient.objects.filter(organization=self.org, is_active=True)
                         .select_related("user"))
        if not pacientes:
            self.resumen["historial"] = "la organización no tiene pacientes: no se agrega nada"
            return
        ahora = timezone.now()
        turnos = self._turnos(self.hoy - dt.timedelta(days=HISTORIAL_DESDE_DIAS),
                              self.hoy - dt.timedelta(days=HISTORIAL_HASTA_DIAS),
                              ahora, respetar_vigencia=False)
        self._crear_fichas(turnos, pacientes, ahora)

    def _turnos(self, desde, hasta, ahora, respetar_vigencia):
        """Los turnos ocupados `(inicio, agenda)` de todas las agendas activas.

        Sólo decide *cuáles* se ocupan (la ocupación pasada es mayor que la
        futura). El desenlace y el paciente se deciden después, con los turnos
        ya ordenados en el tiempo.
        """
        tz = ZoneInfo(LA_PAZ)
        turnos = []
        agendas = (Schedule.objects.filter(organization=self.org, is_active=True)
                   .select_related("practitioner"))
        for agenda in agendas:
            if agenda.practitioner.user_id is None:
                continue
            dia = desde
            while dia <= hasta:
                vigente = not respetar_vigencia or (
                    agenda.valid_from <= dia and (
                        agenda.valid_until is None or dia <= agenda.valid_until))
                if dia.weekday() == agenda.weekday and vigente:
                    inicio = dt.datetime.combine(dia, agenda.start_time, tzinfo=tz)
                    fin = dt.datetime.combine(dia, agenda.end_time, tzinfo=tz)
                    while inicio < fin:
                        ocupacion = OCCUPANCY_PAST if inicio < ahora else OCCUPANCY_FUTURE
                        if self.rnd.random() < ocupacion:
                            turnos.append((inicio, agenda))
                        inicio += dt.timedelta(minutes=agenda.slot_minutes)
                dia += dt.timedelta(days=1)
        return turnos

    def _minutos_de_anticipacion(self, inicio, ahora):
        """Cuánto antes del turno se reservó, en minutos.

        Se sortean días enteros (más peso a 1–14) y un resto de media hora a
        diez horas, para que la hora de la reserva no caiga siempre en la hora
        del turno. Una ficha futura no puede haberse reservado más adelante
        que ahora: se acorta a lo ya transcurrido.
        """
        dias = self.rnd.choices(range(len(PESOS_ANTICIPACION)), PESOS_ANTICIPACION)[0]
        minutos = dias * 1440 + self.rnd.randint(30, 600)
        if inicio - dt.timedelta(minutes=minutos) > ahora - dt.timedelta(minutes=5):
            hasta_el_turno = int((inicio - ahora).total_seconds() // 60)
            minutos = hasta_el_turno + self.rnd.randint(5, 4320)
        return minutos

    def _crear_fichas(self, turnos, pacientes, ahora):
        """Decide el desenlace de cada turno ocupado y lo inserta.

        **En orden cronológico**, para que las «faltas previas» de un paciente
        sean de verdad las anteriores en el tiempo. El desenlace pasado no es
        un sorteo parejo: una ficha se cancela con probabilidad fija y, si no,
        el paciente se ausenta con `probabilidad_ausencia` (anticipación,
        pago por adelantado, faltas previas, día y hora). Es lo que le da al
        modelo de US-35 algo que aprender.

        Pagos: quien pagó por adelantado lo hizo al reservar (simulado, con al
        menos 24 h de margen); el resto paga en efectivo en ventanilla minutos
        antes del turno. Una ficha pendiente de pago o cancelada no tiene pago.
        """
        especialidad_de = {
            ps.practitioner_id: ps.specialty.name
            for ps in PractitionerSpecialty.objects.filter(organization=self.org)
            .select_related("specialty")
        }
        usuarios_paciente = {p.id: p.user for p in pacientes if p.user_id}
        # Quien cobra el efectivo es recepción; si no hay, el que reservó.
        cobradores = list(User.objects.filter(organization=self.org,
                                              user_roles__role__code="receptionist")
                          .distinct().order_by("created_at"))
        sin_titular = self.admin or self.superadmin
        faltas = {}                                   # paciente -> ausencias hasta ahora
        ausencia = {True: [0, 0], False: [0, 0]}      # pagó adelantado -> [fichas, ausentes]
        desenlaces = {}
        nuevas_fichas, nuevas_atenciones, nuevos_pagos, creadas = [], [], [], []

        for inicio, agenda in sorted(turnos, key=lambda t: (t[0], str(t[1].pk))):
            pac = self.rnd.choice(pacientes)
            reservo = usuarios_paciente.get(pac.guardian_id or pac.id) or sin_titular
            minutos = self._minutos_de_anticipacion(inicio, ahora)
            creada = inicio - dt.timedelta(minutes=minutos)
            # Un adelanto con menos de un día de margen no es adelanto. Se
            # sortea siempre, para no cambiar el resto de la serie aleatoria.
            adelantado = self.rnd.random() < PAGO_ADELANTADO and minutos >= MINUTOS_MIN_ADELANTO

            if inicio >= ahora:
                estado = self.rnd.choices(["confirmed", "pending_payment"], [3, 1])[0]
            elif self.rnd.random() < TASA_CANCELACION:
                estado = "cancelled"
            else:
                p = probabilidad_ausencia(minutos / 1440, adelantado, faltas.get(pac.id, 0),
                                          inicio.weekday(), inicio.hour)
                ausente = self.rnd.random() < p
                estado = "no_show" if ausente else "attended"
                ausencia[adelantado][0] += 1
                if ausente:
                    ausencia[adelantado][1] += 1
                    faltas[pac.id] = faltas.get(pac.id, 0) + 1

            cancelada = estado == "cancelled"
            ficha = Appointment(
                organization=self.org, patient=pac, booked_by=reservo,
                practitioner=agenda.practitioner, branch_id=agenda.branch_id,
                schedule=agenda, starts_at=inicio,
                ends_at=inicio + dt.timedelta(minutes=agenda.slot_minutes),
                status=estado,
                # Cancela el día anterior, pero nunca antes de haber reservado.
                cancelled_at=(max(creada + dt.timedelta(minutes=10),
                                  inicio - dt.timedelta(days=1)) if cancelada else None),
                cancellation_reason="patient" if cancelada else "",
                refund_eligible=True if cancelada else None,
            )
            nuevas_fichas.append(ficha)
            creadas.append(creada)
            desenlaces[estado] = desenlaces.get(estado, 0) + 1

            # US-29: una ficha confirmada, atendida o ausente está pagada; el
            # panel de ingresos lo necesita.
            if estado in ("confirmed", "attended", "no_show"):
                if adelantado:
                    proveedor, cobra = "simulated", reservo
                    pagado = creada + dt.timedelta(minutes=self.rnd.randint(2, 30))
                else:
                    proveedor = "cash"
                    cobra = self.rnd.choice(cobradores) if cobradores else reservo
                    # Minutos antes del turno, y nunca antes de haber reservado.
                    pagado = max(inicio - dt.timedelta(minutes=self.rnd.randint(10, 20)),
                                 creada + dt.timedelta(minutes=1))
                nuevos_pagos.append(Payment(
                    organization=self.org, appointment=ficha, created_by=cobra,
                    amount=Decimal(self.rnd.choice([80, 100, 120, 150])),
                    currency="BOB", provider=proveedor, status="succeeded",
                    paid_at=min(ahora, pagado),
                ))
            if estado == "attended":
                nuevas_atenciones.append(self._atencion(
                    ficha, agenda.practitioner,
                    especialidad_de.get(agenda.practitioner_id, "Medicina general"),
                ))

        # En bloque: contra una base remota, miles de INSERT de a uno son
        # minutos de pura latencia.
        Appointment.objects.bulk_create(nuevas_fichas, batch_size=500)
        Encounter.objects.bulk_create(nuevas_atenciones, batch_size=500)
        Payment.objects.bulk_create(nuevos_pagos, batch_size=500)

        # `created_at` es `auto_now_add`: el INSERT lo pisa con «ahora» y toda
        # la ficha parecería reservada hoy. La anticipación es justo la causa
        # que el modelo tiene que leer, así que se corrige después del alta.
        # `bulk_update` no pasa por `pre_save`, o sea que no dispara el
        # `auto_now` de `updated_at`: sólo se escribe la columna pedida.
        for ficha, creada in zip(nuevas_fichas, creadas):
            ficha.created_at = creada
        Appointment.objects.bulk_update(nuevas_fichas, ["created_at"], batch_size=500)
        for pago in nuevos_pagos:
            pago.created_at = pago.paid_at          # el cobro nace cuando se paga
        Payment.objects.bulk_update(nuevos_pagos, ["created_at"], batch_size=500)

        self._contar("pagos", len(nuevos_pagos))
        self._contar("fichas", len(nuevas_fichas))
        self._contar("atenciones firmadas", len(nuevas_atenciones))
        self.resumen["desenlaces"] = ", ".join(f"{k} {v}" for k, v in sorted(desenlaces.items()))
        for adelanto, etiqueta in ((True, "ausencia con pago adelantado"),
                                   (False, "ausencia sin pago adelantado")):
            total, ausentes = ausencia[adelanto]
            if total:
                self.resumen[etiqueta] = f"{ausentes} de {total} ({ausentes / total:.1%})"

    def _atencion(self, ficha, profesional, especialidad):
        """La atención firmada de una ficha atendida, lista para insertar.

        Se inserta ya firmada: el trigger de US-24 vigila ``UPDATE`` y
        ``DELETE``, no el alta, y un encuentro que nace firmado no pasó nunca
        por un estado editable.
        """
        motivo, diagnostico, tratamiento = CLINICAL.get(especialidad, CLINICAL["Medicina general"])
        return Encounter(
            organization=self.org, appointment=ficha, patient_id=ficha.patient_id,
            practitioner_id=ficha.practitioner_id, branch_id=ficha.branch_id,
            reason=motivo, diagnosis=diagnostico, treatment=tratamiento,
            status=Encounter.Status.SIGNED, signed_at=ficha.ends_at,
            signed_by_id=profesional.user_id,
        )


class Command(BaseCommand):
    help = "Siembra seis organizaciones de demostración, o nutre una existente."

    def add_arguments(self, parser):
        parser.add_argument("--password", help="Clave común de todas las cuentas "
                            "(si no, la variable DATASET_PASSWORD).")
        parser.add_argument("--dry-run", action="store_true",
                            help="Muestra qué se crearía, sin escribir nada.")
        parser.add_argument("--only", help="Sembrar sólo este slug de las seis.")
        parser.add_argument("--enrich", metavar="SLUG", action="append",
                            help="Nutrir una organización que ya existe (repetible). "
                                 "Sólo agrega: no modifica ni borra nada.")
        parser.add_argument("--history", metavar="SLUG", action="append",
                            help="Agregar fichas pasadas (de hace 210 a 61 días) a una "
                                 "organización que ya existe (repetible). Sólo agrega, "
                                 "y no hace nada si ya tiene fichas de hace más de 60 días.")

    def handle(self, *args, **opciones):
        import os

        if sum(bool(opciones[k]) for k in ("only", "enrich", "history")) > 1:
            raise CommandError("Usá --only, --enrich o --history: uno solo.")

        orgs = [o for o in ORGANIZATIONS if not opciones["only"] or o["slug"] == opciones["only"]]
        if opciones["only"] and not orgs:
            raise CommandError(f"No hay ninguna organización con slug «{opciones['only']}».")

        if opciones["dry_run"]:
            if opciones["history"]:
                self.stdout.write("Se agregaría historial a: " + ", ".join(opciones["history"]))
            elif opciones["enrich"]:
                self.stdout.write("Se nutrirían: " + ", ".join(opciones["enrich"]))
            else:
                for o in orgs:
                    self.stdout.write(f"{o['name']} ({o['slug']}) · {o['city']} · plan {o['plan']} · "
                                      f"{len(o['branches'])} sedes · {len(o['specialties'])} especialidades")
            return

        # `--history` no crea cuentas: no necesita la clave.
        hash_clave = None
        if not opciones["history"]:
            clave = opciones["password"] or os.environ.get("DATASET_PASSWORD")
            if not clave or len(clave) < 10:
                raise CommandError("Falta la clave común (--password o DATASET_PASSWORD), "
                                   "de 10 caracteres o más. No se versiona.")
            # Un solo hash para todas las cuentas: Argon2 es lento a propósito, y
            # calcularlo cientos de veces convierte un comando de segundos en uno
            # de minutos sin ganar nada.
            hash_clave = make_password(clave)

        with platform_admin_context():
            superadmin = User.objects.filter(is_platform_admin=True).order_by("created_at").first()
            existentes = {o.slug: o for o in Organization.objects.all()}
            planes = {p.code: p for p in SubscriptionPlan.objects.all()}
        if superadmin is None:
            raise CommandError("No hay superadministrador: crealo con createsuperuser.")

        if opciones["history"]:
            for slug in opciones["history"]:
                if slug not in existentes:
                    raise CommandError(f"No existe la organización «{slug}».")
            for slug in opciones["history"]:
                self._informar(existentes[slug].name, slug,
                               self._agregar_historial(existentes[slug], superadmin))
            return
        if opciones["enrich"]:
            for slug in opciones["enrich"]:
                if slug not in existentes:
                    raise CommandError(f"No existe la organización «{slug}».")
                self._informar(existentes[slug].name, slug,
                               self._nutrir(existentes[slug], superadmin, hash_clave))
        else:
            for datos in orgs:
                if datos["slug"] in existentes:
                    self.stdout.write(self.style.WARNING(f"{datos['slug']}: ya existe, se saltea."))
                    continue
                self._informar(datos["name"], datos["slug"],
                               self._sembrar(datos, planes[datos["plan"]], superadmin, hash_clave))

        self.stdout.write("")
        self.stdout.write("Siguiente paso: reindexar el asistente de a una organización,")
        self.stdout.write("  python manage.py embed_catalog --organization <slug>")

    def _informar(self, nombre, slug, resumen):
        self.stdout.write(self.style.SUCCESS(f"{nombre} ({slug})"))
        for clave_r, valor in resumen.items():
            self.stdout.write(f"  {clave_r:<26} {valor}")

    # ----------------------------------------------------------------------

    @transaction.atomic
    def _sembrar(self, datos, plan, superadmin, hash_clave):
        """Una organización nueva completa, dada de alta como desde la pantalla."""
        dominio = f"{datos['slug']}.test"
        organizacion, admin, _ = create_organization(
            organization_data={
                "slug": datos["slug"], "name": datos["name"], "legal_name": datos["legal_name"],
                "tax_id": datos["tax_id"], "contact_email": f"contacto@{dominio}",
                "contact_phone": datos["branches"][0][2], "address": datos["address"],
                "city": datos["city"], "timezone": LA_PAZ,
            },
            admin_data={"email": f"admin@{dominio}", "first_name": "Administración",
                        "last_name": datos["name"], "document_number": f"{datos['tax_id'][-4:]}01"},
            plan=plan, created_by=superadmin,
        )
        with tenant_context(organizacion.id):
            User.objects.filter(pk=admin.pk).update(password=hash_clave)
            s = Sembrador(organizacion, hash_clave, superadmin, admin)
            s.resumen["administrador"] = admin.email
            s.sucursales(datos["branches"])
            s.especialidades(datos["specialties"])
            s.servicios()
            s.recepcion()
            sedes = list(Branch.objects.filter(organization=organizacion))
            matricula = 1
            for nombre_esp in datos["specialties"]:
                # Medicina general y Pediatría tienen dos profesionales: son las
                # de más demanda, y así hay más de un médico por especialidad.
                for _ in range(2 if nombre_esp in ("Medicina general", "Pediatría") else 1):
                    s.profesional(nombre_esp, sedes, f"MP-{datos['tax_id'][-3:]}{matricula:03d}")
                    matricula += 1
            s.fichas(s.pacientes(PATIENTS, PATIENTS_WITH_ACCOUNT))
        return s.resumen

    @transaction.atomic
    def _agregar_historial(self, organizacion, superadmin):
        """Fichas pasadas para una organización que ya existe, sin tocar lo que tiene."""
        with tenant_context(organizacion.id):
            admin = (User.objects.filter(organization=organizacion,
                                         user_roles__role__code="org_admin")
                     .order_by("created_at").first())
            s = Sembrador(organizacion, None, superadmin, admin)
            s.historial()
        return s.resumen

    @transaction.atomic
    def _nutrir(self, organizacion, superadmin, hash_clave):
        """Agrega datos a una organización existente, sin tocar lo que tiene."""
        with tenant_context(organizacion.id):
            admin = (User.objects.filter(organization=organizacion,
                                         user_roles__role__code="org_admin")
                     .order_by("created_at").first())
            s = Sembrador(organizacion, hash_clave, superadmin, admin)
            s.servicios()
            s.recepcion()
            s.cuentas_de_profesionales()
            sedes = list(Branch.objects.filter(organization=organizacion, is_active=True))
            nombres = set(Specialty.objects.filter(organization=organizacion)
                          .values_list("name", flat=True))
            # Un segundo profesional en las especialidades de más demanda, si
            # la organización las tiene. No se crea ninguna especialidad.
            for i, nombre_esp in enumerate(["Medicina general", "Pediatría"], start=1):
                if nombre_esp in nombres and Practitioner.objects.filter(
                    organization=organizacion, specialties__name=nombre_esp,
                ).count() < 2:
                    s.profesional(nombre_esp, sedes,
                                  f"MP-{organizacion.slug[:4].upper()}-{900 + i}")
            ya_hay = Patient.objects.filter(organization=organizacion).count()
            faltan = max(0, PATIENTS - ya_hay)
            s.fichas(s.pacientes(faltan, min(faltan, PATIENTS_WITH_ACCOUNT)))
            if admin is None:
                s.resumen["aviso"] = "la organización no tiene administrador"
        return s.resumen
