# Modelo de dominio: qué agregar en el Sprint 3

El modelo de dominio del Sprint 2 (`Sprint 2 - 2.1.2 Modelo de dominio` en `PlataformaMedica.eapx`) ya está ordenado. El Sprint 3 cambia poco, así que se carga **a mano** sobre una copia de ese diagrama, en vez de regenerarlo.

Los datos salen de los modelos de Django de `main` al 26/10/26 (migraciones posteriores al 06/10, cuando se armó el del Sprint 2), no de memoria.

## Resumen

| Cambio | Dónde | Historia |
|---|---|---|
| Tabla nueva **ENCOUNTER_PRESCRIPTION_ITEMS** | `encounters/models.py` → `PrescriptionItem` | US-26 |
| Tabla nueva **ENCOUNTER_ORDERS** | `encounters/models.py` → `MedicalOrder` | US-26 |
| Tabla nueva **DEVICE_TOKENS** | `notifications/models.py` → `DeviceToken` (app nueva) | US-28 |
| Columna nueva `reminder_sent_at` en **APPOINTMENTS** | `appointments/models.py` | US-28 |
| Valor nuevo `cash` en `provider` de **PAYMENTS** (no cambia la columna) | `payments/models.py` | US-23 |

Ninguna otra tabla cambió: US-27, US-29 y US-33 leen tablas que ya estaban.

## Antes de empezar

1. Respalda el `.eapx` (cierra EA y copia el archivo).
2. En el Project Browser, abre `CAP. 4 - Proceso de desarrollo`, crea el paquete **`Sprint 3 - 2.1.2 Modelo de dominio`** y copia adentro el diagrama del Sprint 2 (clic derecho → *Copy/Paste* → *Paste Diagram* → **Deep copy** si quieres que las clases sean del Sprint 3, o **Shallow copy** si quieres que las compartan). Renómbralo a **`2.1.2 Modelo de dominio - Sprint 3`**.
3. Cambia la nota del diagrama: «al cierre del Sprint 2» → «al cierre del Sprint 3».

## Las mismas reglas del Sprint 2

Así es como está hecho el diagrama del Sprint 2 (`scripts/ea-dominio-sprint2.ps1`), y las tablas nuevas tienen que verse igual:

- Una clase por **tabla**, con el nombre en **MAYÚSCULAS**.
- **Sin operaciones.** El modelo de dominio es de datos: los modelos de Django de estas tres tablas no tienen métodos propios (sólo `__str__`), y en el Sprint 2 ninguna clase del dominio lleva operaciones. Los métodos están en los diagramas de **diseño de clase**.
- Columnas **privadas** (`-`), la clave primaria primero, el tipo de PostgreSQL en **mayúsculas**, con el estereotipo **`PK`** o **`FK`** en la columna que lo es.
- Asociaciones **sin dirección**, del padre al hijo, con un **verbo en MAYÚSCULAS** que se lee `PADRE VERBO HIJO`. Multiplicidad: el padre `1` (o `0..1` si la FK admite NULL) y el hijo `0..*`.
- `organization_id` va **como columna FK**, pero **no se dibuja la línea** hacia ORGANIZATIONS (sólo se dibuja para suscripciones, métricas y alertas, como explica la nota del diagrama).

## 1. ENCOUNTER_PRESCRIPTION_ITEMS (receta: un renglón por medicamento)

**Dónde ponerla:** en la última columna, debajo de ENCOUNTER_AMENDMENTS (la columna de la atención).

**Nota de la clase:** *Un medicamento de la receta de una atención. Sólo se agrega o se quita mientras la atención está en borrador: un trigger de la base lo impide en una atención firmada (`trg_prescription_items_solo_en_borrador`).*

| Columna | Tipo | Estereotipo | Nulo |
|---|---|---|---|
| id | UUID | PK | no |
| organization_id | UUID | FK | no |
| encounter_id | UUID | FK | no |
| medication | VARCHAR(200) | | no |
| dose | VARCHAR(80) | | no |
| frequency | VARCHAR(80) | | no |
| duration | VARCHAR(80) | | no |
| instructions | VARCHAR(300) | | no (puede ir vacía) |
| created_at | TIMESTAMPTZ | | no |

**Relación:**

| Padre | Verbo | Hijo | Multiplicidad (padre – hijo) | FK |
|---|---|---|---|---|
| ENCOUNTERS | **PRESCRIBE** | ENCOUNTER_PRESCRIPTION_ITEMS | `1` – `0..*` | `encounter_id` (ON DELETE PROTECT) |

## 2. ENCOUNTER_ORDERS (órdenes de laboratorio e imagen)

**Dónde ponerla:** debajo de ENCOUNTER_PRESCRIPTION_ITEMS.

**Nota de la clase:** *Un estudio pedido en la atención. `kind`: laboratory, imaging u other (`ck_order_kind`). Igual que la receta, sólo se edita en borrador (`trg_orders_solo_en_borrador`).*

| Columna | Tipo | Estereotipo | Nulo |
|---|---|---|---|
| id | UUID | PK | no |
| organization_id | UUID | FK | no |
| encounter_id | UUID | FK | no |
| kind | VARCHAR(12) | | no |
| description | VARCHAR(300) | | no |
| notes | VARCHAR(300) | | no (puede ir vacía) |
| created_at | TIMESTAMPTZ | | no |

**Relación:**

| Padre | Verbo | Hijo | Multiplicidad (padre – hijo) | FK |
|---|---|---|---|---|
| ENCOUNTERS | **SOLICITA** | ENCOUNTER_ORDERS | `1` – `0..*` | `encounter_id` (ON DELETE PROTECT) |

## 3. DEVICE_TOKENS (teléfonos que reciben avisos push)

**Dónde ponerla:** en la tercera columna, la de lo que cuelga del usuario (AUDIT_LOG, LOGIN_ATTEMPTS, PASSWORD_RESET_TOKENS…), al final.

**Nota de la clase:** *El token de Firebase Cloud Messaging de un dispositivo del usuario. Se registra al iniciar sesión en el móvil y se borra al cerrarla, o cuando FCM avisa que ya no existe. `platform`: android, ios o web. UNIQUE(organization_id, token).*

| Columna | Tipo | Estereotipo | Nulo |
|---|---|---|---|
| id | UUID | PK | no |
| organization_id | UUID | FK | no |
| user_id | UUID | FK | no |
| token | TEXT | | no |
| platform | VARCHAR(10) | | no |
| created_at | TIMESTAMPTZ | | no |
| last_seen_at | TIMESTAMPTZ | | no |

**Relación:**

| Padre | Verbo | Hijo | Multiplicidad (padre – hijo) | FK |
|---|---|---|---|---|
| USERS | **REGISTRA_DISPOSITIVO** | DEVICE_TOKENS | `1` – `0..*` | `user_id` (ON DELETE CASCADE) |

## 4. Cambios en tablas que ya están

**APPOINTMENTS:** agrega la columna, después de `attendance_confirmed_at`:

| Columna | Tipo | Estereotipo | Nulo |
|---|---|---|---|
| reminder_sent_at | TIMESTAMPTZ | | **sí** |

Si la clase tiene nota, súmale: *`reminder_sent_at`: cuándo se mandó el recordatorio; mientras sea NULL, el proceso de recordatorios la puede avisar (US-28).*

**PAYMENTS:** no cambia ninguna columna. Si la nota de la clase menciona los proveedores, agrega `cash`: *`provider`: stripe, simulated o **cash** (cobro en ventanilla, US-23).*

## Cómo cargar una tabla en EA

1. Desde la Toolbox, **Class** sobre el diagrama; nombre en mayúsculas.
2. **Attributes** (F9): por cada columna, *Name* = la columna, *Type* = el tipo, *Scope* = **Private**, *Stereotype* = `PK` o `FK` donde corresponda.
3. Para igualar el aspecto de las del Sprint 2, copia el formato de una clase vecina: clic derecho en ella → *Appearance* → *Copy Style*, y en la nueva *Paste Style*.
4. **Association** del padre al hijo. En sus propiedades: *Name* = el verbo; *Direction* = **Unspecified**; en *Role(s)*, multiplicidad `1` en el extremo del padre y `0..*` en el del hijo.
5. *Layout* → acomoda a mano para que las líneas no crucen las cajas.

Al terminar quedan **3 tablas nuevas, 3 asociaciones nuevas y 1 columna nueva**.
