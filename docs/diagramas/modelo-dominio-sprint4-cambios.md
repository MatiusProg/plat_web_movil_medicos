# Modelo de dominio: qué agregar en el Sprint 4

El modelo de dominio del Sprint 3 (`2.1.2 Modelo de Dominio - Sprint 3` en `PlataformaMedica.eapx`) ya está ordenado. Igual que en el Sprint 3, los cambios del Sprint 4 se cargan **a mano** sobre una copia de ese diagrama, sin regenerarlo.

Los datos salen de las migraciones agregadas a `main` desde el cierre del Sprint 3 (commit `555a64d`) y de los `models.py` correspondientes, no de memoria:

```
git diff --name-status 555a64d..main -- 'backend/*/migrations/*.py'
```

ai/0001–0003, appointments/0007–0010, catalog/0008, encounters/0007–0013, messaging/0001–0003, noshow/0001–0003, reporting/0004, tenancy/0007–0008.

## Resumen

| Cambio | Clase en el diagrama | Tabla física | Dónde está | Historia |
|---|---|---|---|---|
| Tabla nueva | **TEXTOS_GENERADOS_IA** | `ai_generated_texts` | `ai/models.py` → `AiGeneratedText` (app nueva) | US-42 (la escriben US-39 y US-40) |
| Tabla nueva | **CONVERSACIONES_ATENCION** | `encounter_threads` | `messaging/models.py` → `EncounterThread` (app nueva) | US-47 |
| Tabla nueva | **MENSAJES_CONVERSACION** | `encounter_messages` | `messaging/models.py` → `EncounterMessage` | US-47 |
| Tabla nueva | **VERSIONES_MODELO** | `model_versions` | `noshow/models.py` → `ModelVersion` (app nueva) | US-35 (US-38 reentrena) |
| Tabla nueva | **PREDICCIONES_INASISTENCIA** | `noshow_predictions` | `noshow/models.py` → `NoShowPrediction` | US-35 (US-36 la lee) |
| Tabla nueva | **LISTA_ESPERA** | `waitlist_entries` | `appointments/models.py` → `WaitlistEntry` | US-52 |
| Tabla nueva | **PRECONSULTAS_FICHA** | `appointment_preconsultations` | `appointments/models.py` → `AppointmentPreconsultation` | US-51 |
| Tabla nueva | **CALIFICACIONES_ATENCION** | `encounter_ratings` | `encounters/models.py` → `EncounterRating` | US-48 |
| Tabla nueva | **TOMAS_MEDICAMENTO** | `encounter_medication_intakes` | `encounters/models.py` → `MedicationIntake` | US-49 |
| Tabla nueva | **SIGNOS_VITALES** | `encounter_vital_signs` | `encounters/models.py` → `VitalSigns` | US-53 |
| Tabla nueva | **GASTOS** | `expenses` | `reporting/models.py` → `Expense` | US-50 |
| Tabla nueva | **AJUSTES_FINANZAS** | `finance_settings` | `reporting/models.py` → `FinanceSettings` | US-50 |
| Columna nueva `reinforced_reminder_sent_at` | **FICHAS** | `appointments` | `appointments/0007` | US-36 |
| Columna nueva `fee_percent` | **PROFESIONALES** | `practitioners` | `catalog/0008` | US-50 |
| Valor nuevo `vital_signs` en `section` (no cambia la columna) | **ENMIENDAS_ATENCION** | `encounter_amendments` | `encounters/0013` | US-53 |
| Claves nuevas `waitlist` y `accounting` en `features` (no cambia la columna) | **PLANES_SUSCRIPCION** | `subscription_plans` | `tenancy/0007`, `tenancy/0008` | US-52, US-50 |

Al terminar quedan **12 clases nuevas, 32 asociaciones nuevas (más 2 opcionales) y 2 columnas nuevas** en clases existentes.

## Antes de empezar

1. Respalda el `.eapx` (cierra EA y copia el archivo).
2. En el Project Browser, crea el paquete **`Sprint 4 - 2.1.2 Modelo de dominio`** y copia adentro el diagrama del Sprint 3 (*Paste Diagram* → **Deep copy** o **Shallow copy**, como en el Sprint 3). Renómbralo a **`2.1.2 Modelo de Dominio - Sprint 4`** (el marco del PNG del Sprint 3 todavía dice «Sprint 2»: conviene corregirlo en la copia).
3. Cambia la nota del diagrama: «al cierre del Sprint 3» → «al cierre del Sprint 4».

## Las mismas reglas del Sprint 3

Así está hecho el diagrama del Sprint 3 (ver el PNG `docs/diagramas/png/Sprint3/2.1.2 Modelo de Dominio - Sprint 3.png`), y las clases nuevas tienen que verse igual:

- Una clase por **tabla**, con el nombre **en castellano, en MAYÚSCULAS y en plural, con guiones bajos** (en el Sprint 3 se renombraron: `appointments` → FICHAS, `encounters` → ATENCIONES, `encounter_orders` → ORDENES_MEDICAS, `encounter_prescription_items` → MEDICAMENTOS_RECETA, `encounter_amendments` → ENMIENDAS_ATENCION, `device_tokens` → TOKENS_DISPOSITIVO…). Los nombres de este documento siguen ese criterio; la tabla física va en la nota de la clase.
- Las **columnas** se dejan con su nombre físico en inglés (`starts_at`, `patient_id`…), igual que en el Sprint 3.
- **Sin operaciones.**
- Columnas **privadas** (`-`), tipo de PostgreSQL en **MAYÚSCULAS** (`UUID`, `VARCHAR(n)`, `TEXT`, `TIMESTAMPTZ`, `SMALLINT`, `INTEGER`, `NUMERIC(p,s)`, `JSONB`, `BOOLEAN`, `DATE`, `DOUBLE PRECISION`, `BIGSERIAL`). En EA las columnas comunes quedan arriba y las de estereotipo **`PK`** y **`FK`** se agrupan abajo, como en el diagrama.
- Se incluyen `created_at` / `updated_at` (el Sprint 3 las incluye).
- Asociaciones **sin dirección**, del padre al hijo, con un **verbo en MAYÚSCULAS** que se lee `PADRE VERBO HIJO`. Multiplicidad: el padre `1` (o `0..1` si la FK admite NULL) y el hijo `0..*` (o `0..1` si la FK es única, un OneToOne).
- `organization_id` va **como columna FK**, pero **no se dibuja la línea** hacia ORGANIZACIONES, salvo para lo propio del inquilino (en el Sprint 3: suscripción, métricas y alertas). En el Sprint 4 sólo **AJUSTES_FINANZAS** entra en esa excepción; ver la sección 2.
- **Las FK compuestas** `(x_id, organization_id) REFERENCES padre (id, organization_id)` que agregan las migraciones de RLS se dibujan como **una sola asociación** (la de `x_id`): `organization_id` ya está como FK en la clase.
- **Composición o asociación:** el Sprint 3 dibuja todo como asociación simple, porque casi todas las FK son `PROTECT` / `ON DELETE RESTRICT`. Este documento marca las tres que son `CASCADE` por si se quiere usar el rombo negro (composición); si se prefiere mantener el criterio del Sprint 3, se dibujan también como asociación simple.

Los **verbos** no salen del código (Django no los tiene): son una propuesta en la línea de los del Sprint 3 (`SE_ATIENDE_EN`, `PRESCRIBE`, `SOLICITA`…). Cámbialos si alguno no te convence.

---

## 1. Clases nuevas

### Paquete IA

#### TEXTOS_GENERADOS_IA — `ai_generated_texts` (US-42; la llenan US-39 y US-40)

**Nota de la clase:** *Todo texto que escribe la IA para un paciente, en una sola tabla. `kind`: consultation_summary, preparation o history_summary. `status`: draft → approved o discarded, y desde ahí no cambia. `generated_text` (lo que escribió el modelo) no se modifica nunca; `final_text` es lo que aprobó el médico. Nada se borra (triggers de la base). Lo valida el médico de la atención (`practitioner_id`). Un solo resumen vivo por atención y una sola preparación viva por orden.*

| Columna | Tipo | Estereotipo | Nulo |
|---|---|---|---|
| id | UUID | PK | no |
| kind | VARCHAR(24) | | no |
| generated_text | TEXT | | no |
| final_text | TEXT | | no (puede ir vacío) |
| generated_by | VARCHAR(60) | | no (puede ir vacío) |
| status | VARCHAR(10) | | no |
| reviewed_at | TIMESTAMPTZ | | sí |
| created_at | TIMESTAMPTZ | | no |
| updated_at | TIMESTAMPTZ | | no |
| organization_id | UUID | FK | no |
| patient_id | UUID | FK | no |
| practitioner_id | UUID | FK | no |
| encounter_id | UUID | FK | sí |
| medical_order_id | UUID | FK | sí |
| reviewed_by_id | UUID | FK | sí |

### Paquete No-show (inasistencia)

#### VERSIONES_MODELO — `model_versions` (US-35; US-38 reentrena)

**Nota de la clase:** *Cada modelo de inasistencia que se entrenó, por organización. Los coeficientes van en JSON (`params`), nunca un objeto serializado. `kind`: noshow. `status`: active, candidate, rejected o retired; una sola `active` por (organización, tipo). Sólo puede quedar active o candidate si le gana a la línea base (`beats_baseline`). UNIQUE(organization_id, kind, version).*

| Columna | Tipo | Estereotipo | Nulo |
|---|---|---|---|
| id | UUID | PK | no |
| kind | VARCHAR(16) | | no |
| version | INTEGER | | no |
| status | VARCHAR(10) | | no |
| trained_at | TIMESTAMPTZ | | no |
| n_train | INTEGER | | no |
| n_test | INTEGER | | no |
| base_rate | DOUBLE PRECISION | | no |
| params | JSONB | | no |
| metrics | JSONB | | no |
| beats_baseline | BOOLEAN | | no |
| created_at | TIMESTAMPTZ | | no |
| updated_at | TIMESTAMPTZ | | no |
| organization_id | UUID | FK | no |

#### PREDICCIONES_INASISTENCIA — `noshow_predictions` (US-35; US-36 lee `level`)

**Nota de la clase:** *La predicción vigente de cada ficha futura, a lo sumo una por ficha; al recalcular se actualiza. `level`: low, medium o high; `probability` entre 0 y 1. Las de fichas pasadas no se borran: sirven para medir cuánto acertó el modelo.*

| Columna | Tipo | Estereotipo | Nulo |
|---|---|---|---|
| id | UUID | PK | no |
| probability | DOUBLE PRECISION | | no |
| level | VARCHAR(6) | | no |
| factors | JSONB | | no |
| computed_at | TIMESTAMPTZ | | no |
| organization_id | UUID | FK | no |
| appointment_id | UUID | FK (única) | no |
| model_version_id | UUID | FK | no |

### Paquete Mensajería

#### CONVERSACIONES_ATENCION — `encounter_threads` (US-47)

**Nota de la clase:** *El chat paciente–médico de una atención, a lo sumo uno por atención. No se borra, no cambia de atención ni de participantes y, una vez cerrado, no se reabre (trigger). `closed_at` y `closed_by_id` van juntos (`ck_thread_closed`).*

| Columna | Tipo | Estereotipo | Nulo |
|---|---|---|---|
| id | UUID | PK | no |
| patient_read_at | TIMESTAMPTZ | | sí |
| practitioner_read_at | TIMESTAMPTZ | | sí |
| last_message_at | TIMESTAMPTZ | | sí |
| closed_at | TIMESTAMPTZ | | sí |
| created_at | TIMESTAMPTZ | | no |
| organization_id | UUID | FK | no |
| encounter_id | UUID | FK (única) | no |
| patient_id | UUID | FK | no |
| practitioner_id | UUID | FK | no |
| closed_by_id | UUID | FK | sí |

#### MENSAJES_CONVERSACION — `encounter_messages` (US-47)

**Nota de la clase:** *Un mensaje del chat. `side`: patient o practitioner. `flagged_emergency` sólo en mensajes del paciente (`ck_message_flag_patient`). No se modifica ni se borra (trigger).*

| Columna | Tipo | Estereotipo | Nulo |
|---|---|---|---|
| id | UUID | PK | no |
| side | VARCHAR(12) | | no |
| body | TEXT | | no |
| flagged_emergency | BOOLEAN | | no |
| created_at | TIMESTAMPTZ | | no |
| organization_id | UUID | FK | no |
| thread_id | UUID | FK | no |
| author_id | UUID | FK | no |

### Paquete Fichas

#### LISTA_ESPERA — `waitlist_entries` (US-52)

**Nota de la clase:** *Un paciente esperando que se libere un turno, por profesional o por especialidad (al menos uno, `ck_waitlist_target`), en un rango de fechas y, si quiere, en una sucursal. `status`: waiting, offered, booked, expired o cancelled. Al ofrecerle un turno se crea una ficha `pending_payment` real (`offered_appointment_id`). Sólo en los planes Pro y Premium.*

| Columna | Tipo | Estereotipo | Nulo |
|---|---|---|---|
| id | UUID | PK | no |
| date_from | DATE | | no |
| date_to | DATE | | no |
| status | VARCHAR(10) | | no |
| offered_at | TIMESTAMPTZ | | sí |
| created_at | TIMESTAMPTZ | | no |
| updated_at | TIMESTAMPTZ | | no |
| organization_id | UUID | FK | no |
| patient_id | UUID | FK | no |
| requested_by_id | UUID | FK | no |
| practitioner_id | UUID | FK | sí |
| specialty_id | UUID | FK | sí |
| branch_id | UUID | FK | sí |
| offered_appointment_id | UUID | FK | sí |

#### PRECONSULTAS_FICHA — `appointment_preconsultations` (US-51)

**Nota de la clase:** *Notas voluntarias del paciente antes de la atención (motivo y preguntas), a lo sumo una por ficha. Nunca un diagnóstico.*

| Columna | Tipo | Estereotipo | Nulo |
|---|---|---|---|
| id | BIGSERIAL | PK | no |
| reason | TEXT | | no (puede ir vacío) |
| questions | TEXT | | no (puede ir vacío) |
| updated_at | TIMESTAMPTZ | | no |
| organization_id | UUID | FK | no |
| appointment_id | UUID | FK (única) | no |

> Es la única tabla nueva con clave `BIGSERIAL` en vez de `UUID`.

### Paquete Atención

#### CALIFICACIONES_ATENCION — `encounter_ratings` (US-48)

**Nota de la clase:** *La calificación que deja el paciente sobre una atención, a lo sumo una por atención. `stars` de 1 a 5 (`ck_rating_stars`).*

| Columna | Tipo | Estereotipo | Nulo |
|---|---|---|---|
| id | UUID | PK | no |
| stars | SMALLINT | | no |
| comment | VARCHAR(500) | | no (puede ir vacío) |
| created_at | TIMESTAMPTZ | | no |
| updated_at | TIMESTAMPTZ | | no |
| organization_id | UUID | FK | no |
| encounter_id | UUID | FK (única) | no |
| patient_id | UUID | FK | no |
| practitioner_id | UUID | FK | no |
| branch_id | UUID | FK | no |
| rated_by_id | UUID | FK | no |

#### TOMAS_MEDICAMENTO — `encounter_medication_intakes` (US-49)

**Nota de la clase:** *Una toma de un medicamento recetado que marca el paciente. `status`: taken o skipped. Sólo de una receta firmada, y no se cambia ni se borra (trigger). UNIQUE(prescription_item_id, dose_number).*

| Columna | Tipo | Estereotipo | Nulo |
|---|---|---|---|
| id | UUID | PK | no |
| dose_number | SMALLINT | | no |
| status | VARCHAR(8) | | no |
| scheduled_at | TIMESTAMPTZ | | sí |
| recorded_at | TIMESTAMPTZ | | no |
| organization_id | UUID | FK | no |
| prescription_item_id | UUID | FK | no |
| patient_id | UUID | FK | no |
| recorded_by_id | UUID | FK | no |

#### SIGNOS_VITALES — `encounter_vital_signs` (US-53)

**Nota de la clase:** *Los signos vitales de una atención, a lo sumo uno por atención, todos opcionales y con rangos posibles (`ck_vitals_*_posible`; sistólica mayor que diastólica). Sólo se editan en borrador; firmada la atención, se corrigen con una enmienda de sección `vital_signs` (trigger).*

| Columna | Tipo | Estereotipo | Nulo |
|---|---|---|---|
| id | UUID | PK | no |
| systolic | SMALLINT | | sí |
| diastolic | SMALLINT | | sí |
| heart_rate | SMALLINT | | sí |
| temperature | NUMERIC(3,1) | | sí |
| spo2 | SMALLINT | | sí |
| weight_kg | NUMERIC(4,1) | | sí |
| height_cm | NUMERIC(4,1) | | sí |
| glucose | SMALLINT | | sí |
| created_at | TIMESTAMPTZ | | no |
| updated_at | TIMESTAMPTZ | | no |
| organization_id | UUID | FK | no |
| encounter_id | UUID | FK (única) | no |

### Paquete Finanzas

#### GASTOS — `expenses` (US-50)

**Nota de la clase:** *Un gasto del centro, opcionalmente de una sucursal. `category`: insumos, alquiler, sueldos, servicios u otros. `amount` > 0 (`ck_expense_amount`). Sólo en los planes Pro y Premium.*

| Columna | Tipo | Estereotipo | Nulo |
|---|---|---|---|
| id | UUID | PK | no |
| category | VARCHAR(12) | | no |
| amount | NUMERIC(10,2) | | no |
| currency | VARCHAR(3) | | no |
| spent_on | DATE | | no |
| note | VARCHAR(200) | | no (puede ir vacía) |
| created_at | TIMESTAMPTZ | | no |
| updated_at | TIMESTAMPTZ | | no |
| organization_id | UUID | FK | no |
| branch_id | UUID | FK | sí |
| created_by_id | UUID | FK | sí |

#### AJUSTES_FINANZAS — `finance_settings` (US-50)

**Nota de la clase:** *Los ajustes de contabilidad de la organización, a lo sumo uno: el porcentaje que cobra la pasarela (`stripe_percent`, de 0 a 100).*

| Columna | Tipo | Estereotipo | Nulo |
|---|---|---|---|
| id | UUID | PK | no |
| stripe_percent | NUMERIC(5,2) | | no |
| updated_at | TIMESTAMPTZ | | no |
| organization_id | UUID | FK (única) | no |

---

## 2. Relaciones nuevas

«Compuesta» = la FK es `(x_id, organization_id) → padre(id, organization_id)`; se dibuja como una sola línea. `PROTECT` / `RESTRICT` → asociación simple, como en el Sprint 3. `CASCADE` → composición (rombo negro en el padre) si se quiere marcar; si no, asociación simple.

| # | Padre | Verbo (propuesto) | Hijo | Mult. (padre – hijo) | FK | on_delete | Tipo |
|---|---|---|---|---|---|---|---|
| **IA** |
| 1 | PACIENTES | RECIBE_TEXTO | TEXTOS_GENERADOS_IA | `1` – `0..*` | `patient_id` (compuesta) | RESTRICT | asociación |
| 2 | PROFESIONALES | VALIDA | TEXTOS_GENERADOS_IA | `1` – `0..*` | `practitioner_id` (compuesta) | RESTRICT | asociación |
| 3 | ATENCIONES | SE_RESUME_EN | TEXTOS_GENERADOS_IA | `0..1` – `0..*` | `encounter_id` (compuesta) | RESTRICT | asociación |
| 4 | ORDENES_MEDICAS | SE_PREPARA_CON | TEXTOS_GENERADOS_IA | `0..1` – `0..*` | `medical_order_id` (**simple**: `encounter_orders` no tiene UNIQUE(id, organization_id)) | PROTECT | asociación |
| 5 | USUARIOS | REVISA | TEXTOS_GENERADOS_IA | `0..1` – `0..*` | `reviewed_by_id` (compuesta) | RESTRICT | asociación |
| **No-show** |
| 6 | FICHAS | SE_PREDICE_EN | PREDICCIONES_INASISTENCIA | `1` – `0..1` | `appointment_id` (compuesta, única) | **CASCADE** | **composición** |
| 7 | VERSIONES_MODELO | CALCULA | PREDICCIONES_INASISTENCIA | `1` – `0..*` | `model_version_id` (compuesta) | RESTRICT | asociación |
| **Mensajería** |
| 8 | ATENCIONES | SE_CONVERSA_EN | CONVERSACIONES_ATENCION | `1` – `0..1` | `encounter_id` (compuesta, única) | RESTRICT | asociación |
| 9 | PACIENTES | CONVERSA_EN | CONVERSACIONES_ATENCION | `1` – `0..*` | `patient_id` (compuesta) | RESTRICT | asociación |
| 10 | PROFESIONALES | RESPONDE_EN | CONVERSACIONES_ATENCION | `1` – `0..*` | `practitioner_id` (compuesta) | RESTRICT | asociación |
| 11 | USUARIOS | CIERRA | CONVERSACIONES_ATENCION | `0..1` – `0..*` | `closed_by_id` (compuesta) | RESTRICT | asociación |
| 12 | CONVERSACIONES_ATENCION | CONTIENE | MENSAJES_CONVERSACION | `1` – `0..*` | `thread_id` (compuesta) | RESTRICT | asociación |
| 13 | USUARIOS | ESCRIBE_MENSAJE | MENSAJES_CONVERSACION | `1` – `0..*` | `author_id` (compuesta) | RESTRICT | asociación |
| **Fichas** |
| 14 | PACIENTES | ESPERA_EN | LISTA_ESPERA | `1` – `0..*` | `patient_id` (compuesta) | RESTRICT | asociación |
| 15 | USUARIOS | ANOTA | LISTA_ESPERA | `1` – `0..*` | `requested_by_id` (compuesta) | RESTRICT | asociación |
| 16 | PROFESIONALES | SE_ESPERA_CON | LISTA_ESPERA | `0..1` – `0..*` | `practitioner_id` (compuesta) | RESTRICT | asociación |
| 17 | ESPECIALIDADES | SE_ESPERA_EN | LISTA_ESPERA | `0..1` – `0..*` | `specialty_id` (compuesta) | RESTRICT | asociación |
| 18 | SUCURSALES | PREFIERE | LISTA_ESPERA | `0..1` – `0..*` | `branch_id` (compuesta) | RESTRICT | asociación |
| 19 | FICHAS | SE_OFRECE_A | LISTA_ESPERA | `0..1` – `0..*` | `offered_appointment_id` (compuesta) | RESTRICT | asociación |
| 20 | FICHAS | SE_PREPARA_EN | PRECONSULTAS_FICHA | `1` – `0..1` | `appointment_id` (compuesta, única) | RESTRICT | asociación |
| **Atención** |
| 21 | ATENCIONES | SE_CALIFICA_CON | CALIFICACIONES_ATENCION | `1` – `0..1` | `encounter_id` (compuesta, única) | RESTRICT | asociación |
| 22 | PACIENTES | CALIFICA | CALIFICACIONES_ATENCION | `1` – `0..*` | `patient_id` (compuesta) | RESTRICT | asociación |
| 23 | PROFESIONALES | ES_CALIFICADO_EN | CALIFICACIONES_ATENCION | `1` – `0..*` | `practitioner_id` (compuesta) | RESTRICT | asociación |
| 24 | SUCURSALES | RECIBE_CALIFICACION | CALIFICACIONES_ATENCION | `1` – `0..*` | `branch_id` (compuesta) | RESTRICT | asociación |
| 25 | USUARIOS | DEJA | CALIFICACIONES_ATENCION | `1` – `0..*` | `rated_by_id` (compuesta) | RESTRICT | asociación |
| 26 | MEDICAMENTOS_RECETA | SE_TOMA_EN | TOMAS_MEDICAMENTO | `1` – `0..*` | `prescription_item_id` (compuesta; por eso `encounters/0010` agrega UNIQUE(id, organization_id) a `encounter_prescription_items`) | RESTRICT | asociación |
| 27 | PACIENTES | TOMA | TOMAS_MEDICAMENTO | `1` – `0..*` | `patient_id` (compuesta) | RESTRICT | asociación |
| 28 | USUARIOS | MARCA | TOMAS_MEDICAMENTO | `1` – `0..*` | `recorded_by_id` (compuesta) | RESTRICT | asociación |
| 29 | ATENCIONES | MIDE | SIGNOS_VITALES | `1` – `0..1` | `encounter_id` (compuesta, única) | RESTRICT | asociación |
| **Finanzas** |
| 30 | SUCURSALES | GASTA | GASTOS | `0..1` – `0..*` | `branch_id` (compuesta) | RESTRICT | asociación |
| 31 | USUARIOS | CARGA | GASTOS | `0..1` – `0..*` | `created_by_id` (simple) | **SET NULL** | asociación |
| 32 | ORGANIZACIONES | CONFIGURA | AJUSTES_FINANZAS | `1` – `0..1` | `organization_id` (única) | **CASCADE** | **composición** |

**Opcionales** (son FK a ORGANIZACIONES; por la regla del diagrama no se dibujan, pero son propias del inquilino y se podría argumentar lo contrario):

| # | Padre | Verbo | Hijo | Mult. | FK | on_delete | Tipo |
|---|---|---|---|---|---|---|---|
| 33 | ORGANIZACIONES | ENTRENA | VERSIONES_MODELO | `1` – `0..*` | `organization_id` | PROTECT | asociación (un modelo por organización, regla 16) |
| 34 | ORGANIZACIONES | REGISTRA_GASTO | GASTOS | `1` – `0..*` | `organization_id` | **CASCADE** | composición |

Por qué se dibuja la #32 y no las otras: AJUSTES_FINANZAS es configuración de la organización (como SUSCRIPCIONES o METRICAS_USO), y sin esa línea queda sin ninguna conexión.

---

## 3. Cambios en clases que ya están

**FICHAS** (`appointments`, US-36): agrega la columna, después de `reminder_sent_at`:

| Columna | Tipo | Estereotipo | Nulo |
|---|---|---|---|
| reinforced_reminder_sent_at | TIMESTAMPTZ | | **sí** |

Súmale a la nota: *`reinforced_reminder_sent_at`: cuándo se mandó el segundo recordatorio a una ficha con riesgo alto de inasistencia (US-36).*

**PROFESIONALES** (`practitioners`, US-50): agrega la columna, después de `is_active`:

| Columna | Tipo | Estereotipo | Nulo |
|---|---|---|---|
| fee_percent | NUMERIC(5,2) | | no (por defecto 0; de 0 a 100) |

Nota: *`fee_percent`: el porcentaje de honorarios del profesional para la contabilidad (US-50).*

**ENMIENDAS_ATENCION** (`encounter_amendments`, US-53): **no cambia la columna** (`section` sigue `VARCHAR(20)`). Sólo se suma el valor `vital_signs` a los permitidos. Si la nota los enumera: *`section`: reason, evolution, diagnosis, indications, treatment, prescription, orders o **vital_signs**.*

**PLANES_SUSCRIPCION** (`subscription_plans`, US-52 y US-50): **no cambia la columna** `features JSONB`; las migraciones `tenancy/0007` y `0008` le agregan dos claves (datos, no esquema). Si la clase tiene nota: *`features` incluye `waitlist` y `accounting`: basic false, pro y premium true.*

**MEDICAMENTOS_RECETA** (`encounter_prescription_items`): no cambia ninguna columna; sólo gana la clave única `(id, organization_id)` para que TOMAS_MEDICAMENTO cuelgue de ella. No se dibuja.

---

## 4. Dónde ponerlas sin mover lo que está

Referencias tomadas del PNG del Sprint 3. La idea es **agrandar el lienzo hacia la derecha y hacia abajo** (y usar los huecos que hay), sin tocar ninguna caja existente.

| Paquete | Clases | Dónde |
|---|---|---|
| **Atención** | SIGNOS_VITALES, CALIFICACIONES_ATENCION | En una **columna nueva a la derecha de ATENCIONES**, a su misma altura (SIGNOS_VITALES arriba, CALIFICACIONES_ATENCION debajo). Las dos cuelgan sólo de ATENCIONES (y CALIFICACIONES además de PACIENTES/PROFESIONALES/SUCURSALES/USUARIOS). |
| **Atención** | TOMAS_MEDICAMENTO | **Debajo de MEDICAMENTOS_RECETA** (esquina inferior derecha, hay lugar libre). |
| **Mensajería** | CONVERSACIONES_ATENCION, MENSAJES_CONVERSACION | En la misma columna nueva de la derecha, **debajo de CALIFICACIONES_ATENCION**: CONVERSACIONES arriba, MENSAJES abajo (una cuelga de la otra). |
| **IA** | TEXTOS_GENERADOS_IA | **A la derecha de ORDENES_MEDICAS** (arriba a la derecha, en la columna nueva): queda pegada a ORDENES_MEDICAS y por encima de ATENCIONES, sus dos padres clínicos. |
| **No-show** | PREDICCIONES_INASISTENCIA, VERSIONES_MODELO | **Arriba de FICHAS**, en una franja nueva sobre el borde superior (PREDICCIONES justo sobre FICHAS, VERSIONES_MODELO a su izquierda). La línea a FICHAS queda corta. |
| **Fichas** | PRECONSULTAS_FICHA | **Arriba de FICHAS**, a la derecha de PREDICCIONES_INASISTENCIA (sobre PACIENTES), en la misma franja superior. |
| **Fichas** | LISTA_ESPERA | En la franja superior, **entre INTENTOS_INICIO_SESION y SUCURSALES** si cabe, o sobre SUCURSALES. Tiene seis padres (PACIENTES, USUARIOS, PROFESIONALES, ESPECIALIDADES, SUCURSALES, FICHAS): ahí las líneas a SUCURSALES, USUARIOS y FICHAS son cortas. |
| **Finanzas** | AJUSTES_FINANZAS, GASTOS | **Abajo a la izquierda, debajo de PLANES_SUSCRIPCION** (hay hueco entre PLANES_SUSCRIPCION y el borde inferior, a la izquierda de ALERTAS_AISLAMIENTO). AJUSTES_FINANZAS cerca de ORGANIZACIONES (la línea #32); GASTOS al lado. |

Para no ensuciar: las asociaciones a USUARIOS (`REVISA`, `CIERRA`, `ESCRIBE_MENSAJE`, `ANOTA`, `DEJA`, `MARCA`, `CARGA`) son las más largas; trázalas con *Line Style → Orthogonal - Square* como las del Sprint 3.

## Cómo cargar una tabla en EA

Igual que en el Sprint 3 (ver `modelo-de-dominio-sprint-3.md`, «Cómo cargar una tabla en EA»): Class con nombre en mayúsculas → Attributes (F9) con *Scope* Private y estereotipo `PK`/`FK` → *Copy Style* / *Paste Style* desde una clase vecina → Association del padre al hijo, *Direction* Unspecified, multiplicidades en *Role(s)*. Para las dos composiciones (#6 y #32, opcionalmente #34): en vez de Association usa **Composition** desde la Toolbox, con el rombo del lado del padre.

---

## 5. Lo que no es dominio (por si se deja fuera)

Nada de esto agrega columnas ni tablas de dominio; son reglas de la base o filas de catálogo:

- **Políticas RLS** (`ENABLE` / `FORCE ROW LEVEL SECURITY` + `tenant_isolation`) de las 12 tablas nuevas: `ai/0002`, `messaging/0002`, `noshow/0002`, `appointments/0009` y `0010`, `encounters/0008`, `0010`, `0012`, `reporting/0004`.
- **Triggers** de inmutabilidad: textos de IA (no se borran, `generated_text` fijo, decididos no cambian), mensajes y conversaciones del chat, tomas (sólo de receta firmada, no se cambian), signos vitales (sólo en borrador), calificaciones (`encounters/0008`).
- **Claves únicas técnicas** `(id, organization_id)` (`uq_*_id_org`) que existen sólo para las FK compuestas, incluida la que se suma a `encounter_prescription_items`.
- **Permisos nuevos** (filas en PERMISOS / PERMISOS_ROL, no esquema): `ai.text.review` (Médico, `ai/0003`), `encounters.chat` (Médico y Paciente, `messaging/0003`), `appointments.noshow.read` (Administración, `noshow/0003`), `finance.accounting.read` y `finance.expense.manage` (Administración, `reporting/0004`).
- **Claves de plan** `waitlist` y `accounting` en `subscription_plans.features` (`tenancy/0007`, `0008`): datos, no columnas.
- **Índices** (`ix_ai_text_bandeja`, `ix_thread_bandeja`, `ix_noshow_pred_nivel`, `ix_rating_practitioner`, `ix_expense_org_date`…).
