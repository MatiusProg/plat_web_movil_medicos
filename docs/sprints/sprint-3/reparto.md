# Sprint 3 — Reparto de historias y alcance por integrante

**Fechas:** 13/10/26 – 31/10/26 · **Presentación:** domingo **01/11/26**
*(tentativa)*

**Objetivo:** cerrar la Épica 5 —receta, órdenes y el historial completo del
paciente en el móvil—, levantar la Épica 6 de notificaciones y reportes
operativos, y completar el asistente con la **reserva conversacional**, que es
lo único de la Épica 7 que quedaba afuera.

Este documento es el contrato de trabajo del sprint: dice quién hace qué, en
qué archivos, de quién depende y para cuándo. Si vas a escribir código —o si le
vas a pedir a una IA que lo escriba por vos— leé primero la sección de tu
nombre y después la sección 5.

Las convenciones de código están en `../../convenciones-de-codigo.md`. El
reparto del sprint anterior, en `../sprint-2/reparto.md`.

---

## 0. De dónde sale el alcance

Es el alcance que el apartado 3.11 del documento ya tenía para este sprint
después del movimiento del Sprint 2: **US-26 a US-30, más US-23 y US-33**, que
se corrieron desde el Sprint 2 para hacerle sitio a la Épica 7. **74 horas.**

**No hay deuda del Sprint 2.** Las 14 historias se presentaron en la revisión y
están en `main`. Dos cosas que la retroalimentación marcaba como pendientes ya
están resueltas en el código:

- **US-17 y US-20 en el móvil**: reservar (`features/availability/`), cancelar
  y reprogramar (`features/appointments/`) existen desde el PR #66.
- **US-22 con el QR definitivo de US-19**: el check-in ya valida el comprobante
  firmado (`appointments/checkin.py` usa `receipts.read_code`).

**Lo que queda fuera, por decisión del equipo:** las características generales
2 (privilegios por componente de interfaz) y 3 (bitácora cifrada) —consultado
con la docente, no forman parte del proyecto— y la evidencia visual y de
rendimiento pendiente de US-09, US-10 y US-22.

**Dos historias llegan con parte del trabajo hecho**, y el reparto lo tiene en
cuenta para no construirlas dos veces:

| Historia | Qué ya existe | Qué le queda |
|---|---|---|
| **US-27** — historial en el móvil | La línea de tiempo del paciente en el móvil (`features/clinical_record/`, PR #60) y en la web (`/mi-historia`) | Recetas, órdenes e indicaciones, que dependen de US-26 |
| **US-30** — exportar a PDF y Excel | El constructor de reportes (característica 5) ya exporta csv, xlsx, html y pdf, en la web y en el móvil | Los **reportes operativos**: hoy no hay conjunto de datos de fichas ni de pagos, sólo de pacientes, profesionales, especialidades, sucursales, agendas y bitácora |

---

## 1. Reparto

| Integrante | Historias | Backend | Web | Móvil | Horas |
|---|---|---|---|---|---|
| Ortega Mancilla, Karen Paola | **US-33** | US-33 | US-33 | US-33 | **16** |
| Hurtado Castro, Luis Mateo *(SM)* | US-26, US-27 · + documentación | US-26, US-27 | US-26, US-27 | US-27 | **16** |
| Aguayo Quiroz, Luis Miguel | **US-29** | US-29 | US-29 | — | **16** |
| Osinaga Blanco, Alexander *(PO)* | US-28, US-30 | US-28, US-30 | US-30 | US-28 | **16** |
| Iporo Chulque, José Daniel | US-23 | US-23 | US-23 | — | **10** |

**Total comprometido: 74 horas** · 5 integrantes · 14,8 h de promedio.

**Criterio:** cada historia va a quien ya es dueño del módulo sobre el que se
escribe. Nadie abre una app que no conoce.

**Ritmo.** El sprint dura 19 días corridos. 14,8 h de promedio son ~0,8 h por
día y por persona, el ritmo más bajo de los cuatro sprints. El margen es para
el documento y la presentación, que en el Sprint 2 se comieron los últimos días.

### Por capa

| US | h | Backend | Web | Móvil |
|---|---|---|---|---|
| **US-23** Ficha asistida en mostrador | 10 | Reserva hecha por recepción a nombre del paciente; cobro presencial | Pantalla de mostrador | — |
| **US-26** Receta y órdenes | 10 | Recetas y órdenes colgadas de la atención; su PDF | Dentro de la atención (`Atencion.tsx`) | *(se leen en US-27)* |
| **US-27** Historial, recetas e indicaciones | 6 | Lectura de las recetas y órdenes propias | `/mi-historia` las muestra | `features/clinical_record/` las muestra |
| **US-28** Notificaciones push y correo | 10 | Tokens de dispositivo, envío por FCM y recordatorios programados | — | `firebase_messaging`, permiso de notificaciones y apertura de la ficha al tocar |
| **US-29** Panel de KPIs | 16 | Indicadores agregados por organización | Panel con gráficos | — *(el administrador trabaja en la web)* |
| **US-30** Reportes operativos | 6 | Conjuntos de datos de fichas y de pagos en `reporting/datasets.py` | Ya exporta | Ya descarga |
| **US-33** Reserva conversacional | 16 | Intención de reservar, propuesta de horarios y reserva con confirmación | `Asistente.tsx` | Pantalla del asistente |

---

## 2. Qué le toca a cada uno

### Karen Ortega — *el asistente* — 16 h

**US-33 — Reserva conversacional · 16 h · MÓVIL + WEB · 🟡**

Cierra el asistente que construyó en el Sprint 2. El paciente describe lo que
le pasa, el asistente sugiere la especialidad (US-31) y, en la misma
conversación, **ofrece horarios reales y reserva**. Tres decisiones:

- **El modelo no reserva: propone.** La reserva la hace `book_appointment` de
  `appointments/booking.py`, la misma función que usa la pantalla de reserva,
  con su bloqueo sobre el espacio. El asistente no escribe en `appointments`
  por su cuenta: si lo hiciera, habría dos caminos de reserva y sólo uno con la
  regla de concurrencia.
- **Nada se reserva sin confirmación explícita.** El asistente muestra
  sucursal, profesional, fecha y hora, y el paciente toca *Confirmar*. Un
  horario que el modelo entendió mal y se reserva solo es una ficha que nadie
  pidió.
- **Los horarios que se ofrecen salen del endpoint de disponibilidad**, no del
  texto del modelo. El modelo elige entre lo que la API devolvió; no inventa un
  turno.

La barrera de urgencias de US-34 **sigue corriendo primero**: una conversación
que deriva a emergencia no ofrece reservar.

La ficha nace pendiente de pago, igual que por la pantalla, y sigue el mismo
camino de US-18.

**Archivos:** `assistant/`, `mobile/lib/features/assistant/`,
`frontend/src/paginas/Asistente.tsx`.

**Depende de:** nadie. La reserva y la disponibilidad ya están publicadas.

---

### Luis Mateo Hurtado *(Scrum Master)* — *receta e historial del paciente* — 16 h + documentación

Sigue siendo el dueño de `encounters`: las dos historias se escriben encima de
la atención de US-24.

**US-26 — Receta digital y órdenes · 10 h · BACKEND + WEB · 🟡**

El médico emite, desde la atención, la receta (medicamento, dosis,
frecuencia, duración) y las órdenes de laboratorio o estudios.

- **La receta cuelga de la atención y comparte su regla:** mientras la
  atención es borrador se edita; firmada, no. Corregir una receta firmada es
  una enmienda, como en US-24.
- **Los antecedentes de US-08 se muestran al recetar.** Una alergia declarada
  tiene que estar a la vista de quien receta.
- La receta se descarga en PDF, con los datos de la organización y del médico.

**US-27 — Historial, recetas e indicaciones en el móvil · 6 h · MÓVIL + WEB · 🔴**

La línea de tiempo ya está. Le agrega las recetas, órdenes e indicaciones de
cada atención, con el mismo alcance que ya tiene `history_scope`: el propio
paciente y sus dependientes, y nada más. Sin alcance, 404.

**Además, como SM:** el capítulo del Sprint 3 en el documento —el apartado
"1.1 Objetivos" del Sprint 3 todavía tiene el texto copiado del Sprint 0—,
Daily, Revisión y Retrospectiva, y los diagramas que pida la docente.

**Archivos:** `encounters/`, `mobile/lib/features/clinical_record/`,
`frontend/src/paginas/Atencion.tsx` y `MiHistoria.tsx`.

**Depende de:** nadie.

**Dependen de él:** US-27 depende de US-26 —son suyas las dos—, y la Épica 9
del Sprint 4 (los resúmenes leen la atención y la receta).

---

### Luis Miguel Aguayo — *los indicadores* — 16 h

**US-29 — Panel de KPIs · 16 h · BACKEND + WEB · 🔴**

Ocupación de agenda, tasa de inasistencia, demanda por especialidad y sucursal,
e ingresos por fichas. Todo sale de `appointments` y `payments`, que él conoce
desde la reserva.

- **Los indicadores se calculan en la base**, con agregaciones, no trayendo
  las fichas a Python para contarlas. Una organización poblada tiene miles.
- **La inasistencia es `no_show` sobre las fichas que debían atenderse**, no
  sobre todas: una ficha cancelada a tiempo no es una inasistencia. Definirlo
  por escrito en la historia, porque es el mismo número que el modelo del
  Sprint 4 intenta predecir.
- Filtros por rango de fechas y por sucursal. El administrador ve su
  organización y nada más; el aislamiento lo da RLS, y la prueba lo demuestra.

**Archivos:** un módulo de indicadores, a acordar entre `appointments` y
`reporting`, y una página nueva en `frontend/src/paginas/`.

**Depende de:** nadie.

**Dependen de él:** Alexander (US-30). **Publicar la definición de cada
indicador antes del 20/10**: los reportes operativos tienen que dar los mismos
números que el panel.

---

### Alexander Osinaga *(Product Owner)* — *notificaciones y reportes operativos* — 16 h

**US-28 — Notificaciones push y correo · 10 h · BACKEND + MÓVIL · 🟡**

Confirmación, recordatorio y cancelación de la ficha. El correo ya existe:
Brevo por API, que él dejó andando en US-21. Esta historia agrega el push y
los recordatorios.

- **Push con Firebase Cloud Messaging.** El móvil registra su token al iniciar
  sesión y lo borra al cerrarla; un token por dispositivo, no por persona.
- **Los recordatorios no necesitan Celery.** Ya hay un proceso en ciclo que
  arranca con la API: `run_automatic_backups --loop`, desde `scripts/start.sh`.
  El recordatorio usa el mismo patrón, dentro de `tenant_context` para cada
  organización.
- **Un recordatorio no se manda dos veces.** Se marca como enviado en la misma
  transacción, o un reinicio del proceso lo repite.
- La credencial de Firebase va en variable de entorno, nunca en el
  repositorio. Tampoco el `google-services.json`.

**US-30 — Reportes operativos · 6 h · BACKEND · 🟡**

La exportación ya está hecha (característica 5). Esta historia agrega los
**conjuntos de datos de fichas y de pagos** al catálogo de
`reporting/datasets.py`, para que fichas por estado, ingresos por sucursal o
inasistencias por especialidad se puedan pedir, exportar, y pedir por voz, sin
tocar el constructor. Los números tienen que coincidir con el panel de US-29.

**Archivos:** `appointments/` (los recordatorios), `reporting/datasets.py`,
`mobile/lib/core/` (registro del token).

**Depende de:** Luis Aguayo, sólo para US-30 (las definiciones de los
indicadores).

---

### José Daniel Iporo — *mostrador* — 10 h

**US-23 — Ficha asistida en mostrador · 10 h · BACKEND + WEB · 🟡**

Para el paciente que llega sin reserva. Es la continuación de su check-in de
US-22, en el mismo mostrador.

- **La reserva es `book_appointment`**, la misma función de la pantalla del
  paciente, llamada por recepción a nombre del paciente. No se escribe otra.
- **El cobro presencial necesita un medio de pago nuevo.** Hoy `Payment.Provider`
  sólo tiene `stripe` y `simulated`. Agregar el pago en efectivo en
  ventanilla es tocar `payments`, que es de Alexander: **acordarlo con él el
  primer día**.
- Si el paciente no existe, se lo da de alta con el ABM de US-10 —también
  suyo— sin salir de la pantalla.
- Ficha reservada y pagada en el mostrador queda lista para el check-in sin
  pasar por el QR.

**Archivos:** `appointments/` (módulo de mostrador), una página nueva en
`frontend/src/paginas/`.

**Depende de:** Alexander (el medio de pago presencial).

---

## 3. Dependencias

| Quién espera | A quién | Qué | Para cuándo |
|---|---|---|---|
| Daniel (US-23) | Alexander | Medio de pago presencial en `payments` | 17/10 |
| Alexander (US-30) | Luis Aguayo | Definición escrita de cada indicador | 20/10 |
| SM (US-27) | SM (US-26) | Modelo de receta y órdenes migrado | 22/10 |

Fuera de esas tres, cada historia arranca el primer día.

---

## 4. Ruta crítica

| Fecha | Qué tiene que estar | Quién |
|---|---|---|
| **17/10** | Pago presencial acordado y migrado | Alexander + Daniel |
| **20/10** | Definición de los indicadores publicada | Luis Aguayo |
| **22/10** | US-26 mergeada | SM |
| **27/10** | Backend completo y congelado; sólo pantallas, documento y pruebas | Todos |
| **29/10** | Release con la APK nueva publicada | SM |
| **31/10** | Cierre del sprint | — |
| **01/11** | Presentación *(tentativa)* | Todos |

---

## 5. Reglas que no se negocian

Siguen vigentes las del Sprint 1 (`../sprint-1/reparto.md`, sección 5) y las
del Sprint 2 (`../sprint-2/reparto.md`, sección 6). Se agregan dos:

12. **Una sola forma de reservar.** Pantalla del paciente, asistente y
    mostrador terminan en `book_appointment`. Ningún camino nuevo inserta en
    `appointments` por su cuenta.

13. **Todo lo que corre fuera del ciclo HTTP —recordatorios, envío de push—
    corre dentro de `tenant_context(org.id)`**, una organización a la vez. Un
    recordatorio que recorre las fichas sin contexto o las lee todas, o no lee
    ninguna.

---

## 6. Tareas nuevas para el Sprint Backlog del documento

La numeración del Sprint 2 llegó hasta T-36. El Sprint 3 arranca en T-37.

| ID | Tarea | Tipo | Estimación | Responsable | Prioridad |
|---|---|---|---|---|---|
| T-37 | Ficha asistida en mostrador | Historia | 10 horas | Iporo Chulque, J.D. | Should have |
| T-38 | Receta digital y órdenes | Historia | 10 horas | Hurtado Castro, L.M. | Should have |
| T-39 | Historial, recetas e indicaciones en el móvil | Historia | 6 horas | Hurtado Castro, L.M. | Must have |
| T-40 | Notificaciones push y correo | Historia | 10 horas | Osinaga Blanco, A. | Should have |
| T-41 | Panel de KPIs | Historia | 16 horas | Aguayo Quiroz, L.M. | Must have |
| T-42 | Reportes operativos | Historia | 6 horas | Osinaga Blanco, A. | Should have |
| T-43 | Reserva conversacional | Historia | 16 horas | Ortega Mancilla, K.P. | Should have |
