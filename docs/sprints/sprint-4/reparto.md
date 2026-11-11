# Sprint 4 — Reparto de historias y alcance por integrante

**Fechas:** 10/11/26 – 23/11/26 · **Revisión:** 24–26/11/26 *(fecha exacta a
confirmar con la docente)*

**Objetivo:** cerrar las épicas de IA que faltan —predicción de inasistencia y
demanda (Épica 8) y textos clínicos generados con validación del médico
(Épica 9)—, sumar los **reportes transaccionales por voz** para el paciente y
dejar **todas las IA del sistema terminadas y comprobadas en producción**. Es
el último sprint: lo que no esté en `main` el 21/11 no se presenta.

Este documento es el contrato de trabajo del sprint: dice quién hace qué, en
qué archivos, de quién depende y para cuándo. Si vas a escribir código —o si le
vas a pedir a una IA que lo escriba por vos— leé primero la sección de tu
nombre y después la sección 5.

Las convenciones de código están en `../../convenciones-de-codigo.md`. El
reparto del sprint anterior, en `../sprint-3/reparto.md`.

---

## 0. De dónde sale el alcance

Es lo que el apartado 3.11 del documento tenía para este sprint: **US-35 a
US-42, 78 horas.** No hay deuda del Sprint 3: sus siete historias se
presentaron (nota 85) y están en `main`.

A eso se suman **tres pendientes que dejó la revisión del Sprint 3**:

| Pendiente | Cómo entra al sprint | Horas |
|---|---|---|
| **Reportes transaccionales por voz** — el paciente dice *«quiero ver mis últimas 2 facturas»* y el sistema le muestra esos pagos con el QR de cada comprobante | Historia nueva: **US-46** | 10 |
| **Diagrama de redes** — para el parcial y para el documento del Sprint 4 | Tarea de documentación del SM | 4 |
| **Todas las IA terminadas correctamente** | Regla 15 (sección 5) para cada dueño, más una tarea de verificación final en producción | 4 |

**Total comprometido: 96 horas.**

> **Sobre US-46.** Lo que entendimos de la ingeniera: los reportes por voz que
> ya existen (característica 5) son para el personal del centro. Falta el lado
> del **cliente**: que el paciente pida *sus* transacciones —pagos, fichas,
> comprobantes— hablando, y reciba la lista con el QR de cada una. Si en la
> revisión resulta que pedía otra cosa, la historia se ajusta; la base (consulta
> acotada al propio paciente + QR que ya existe) sirve igual.

**Lo que ya existe y no se vuelve a construir:**

| Pieza | Dónde está | La usa |
|---|---|---|
| Voz → definición de reporte, con el catálogo filtrado por permisos | `reporting/voice.py`, `useVoz.ts`, `voice_input.dart` | US-46 |
| Comprobante con QR firmado (`MC1.`) | `appointments/receipts.py`, `mobile/lib/features/receipts/` | US-46 |
| Proceso de fondo que recorre organizaciones en `tenant_context` | `appointments/reminders.py`, lanzado por `scripts/start.sh` | US-36, US-38 |
| Definición escrita de la inasistencia | `../sprint-3/us-29-indicadores.md` | US-35, US-37 |
| Cliente de Gemini con degradación sin clave | `assistant/generation.py` | US-39, US-40, US-41 |
| Atención, receta y órdenes | `encounters/` | US-39, US-40, US-41 |

---

## 1. Reparto

| Integrante | Historias | Backend | Web | Móvil | Horas |
|---|---|---|---|---|---|
| Ortega Mancilla, Karen Paola | **US-39, US-42** | US-39, US-42 | US-42 | US-39 | **16** |
| Hurtado Castro, Luis Mateo *(SM)* | US-40, US-41 · + diagrama de redes + documentación | US-40, US-41 | US-41 | US-40 | **20** |
| Aguayo Quiroz, Luis Miguel | **US-35** · + verificación final de las IA | US-35 | US-35 | — | **20** |
| Osinaga Blanco, Alexander *(PO)* | US-36, **US-46** | US-36, US-46 | US-46 | US-46 | **20** |
| Iporo Chulque, José Daniel | US-37, US-38 | US-37, US-38 | US-37 | — | **20** |

**Total comprometido: 96 horas** · 5 integrantes · 19,2 h de promedio.

**Criterio:** igual que siempre, cada historia va a quien ya es dueño del
módulo. Karen sigue con lo que habla con el paciente; el SM con lo que lee la
atención; Luis Aguayo con la inasistencia, que ya definió en US-29; Alexander
con recordatorios, pagos y comprobantes. Daniel toma las dos piezas del modelo
que **no** son el clasificador —la proyección de demanda y el reentrenamiento—,
así el modelo no queda en una sola cabeza.

**Ritmo.** 14 días corridos y 19,2 h de promedio: ~1,4 h por día y por
persona, más que en el Sprint 3. Es el último sprint y no hay deuda; el margen
del final es para la presentación y el parcial.

### Por capa

| US | h | Backend | Web | Móvil |
|---|---|---|---|---|
| **US-35** Riesgo de inasistencia | 16 | Generador de datos con causas, entrenamiento, predicción por ficha | Columna y filtro de riesgo en la agenda | — |
| **US-36** Recordatorios reforzados | 10 | Segundo recordatorio para riesgo alto, en el mismo proceso de US-28 | — | *(recibe el push que ya existe)* |
| **US-37** Proyección de demanda | 10 | Proyección por especialidad y franja horaria | Gráfico en `Kpis.tsx` | — |
| **US-38** Reentrenamiento | 10 | Reentrenar, versionar, comparar y promover el modelo | Estado del modelo vigente | — |
| **US-39** Resumen claro de la consulta | 10 | Texto generado desde la atención firmada | *(lo valida el médico en US-42)* | `clinical_record/` lo muestra |
| **US-40** Preparación para estudios | 6 | Instrucciones por orden de laboratorio o imagen | *(las valida el médico en US-42)* | `clinical_record/` las muestra |
| **US-41** Resumen del historial para el médico | 10 | Síntesis del historial antes de la consulta | Panel en `Atencion.tsx` | — |
| **US-42** Validar o editar texto de IA | 6 | Estados borrador → aprobado, con quién y cuándo | Bandeja de textos por validar | — |
| **US-46** Reportes transaccionales por voz | 10 | Consulta de *mis* pagos y fichas desde una frase | Pantalla del paciente | Pantalla del paciente con QR |

---

## 2. Qué le toca a cada uno

### Karen Ortega — *los textos para el paciente* — 16 h

**US-42 — Validar o editar texto de IA · 6 h · BACKEND + WEB · 🔴**

Es la historia que sostiene a toda la Épica 9, y por eso va primero. Ningún
texto generado llega al paciente sin que un médico lo apruebe.

- **Una sola tabla para todo texto generado** (`ai_generated_texts`, como dice
  el modelo de datos del Sprint 0): tipo (`consultation_summary`,
  `preparation`, `history_summary`), la atención o la orden de la que sale, el
  texto generado, el texto final, estado (`draft`, `approved`, `discarded`),
  quién aprobó y cuándo. US-39, US-40 y US-41 escriben acá; nadie crea su
  propia tabla.
- **Se guarda el texto original del modelo y el editado**, los dos. Si el
  médico lo corrige, queda la diferencia; eso es lo que se muestra cuando la
  docente pregunte «¿y si la IA se equivoca?».
- El paciente sólo lee textos `approved`. Un `draft` no sale por ningún
  endpoint del paciente, y la prueba lo demuestra.
- Bandeja web del médico: sus textos pendientes, editar, aprobar, descartar.

**US-39 — Resumen claro de la consulta · 10 h · BACKEND + MÓVIL · 🟡**

Al firmar la atención se genera un resumen en lenguaje llano: qué se encontró,
qué hay que hacer, cuándo volver.

- **Se genera desde la atención firmada y su receta, no desde texto libre.** El
  prompt lleva sólo esos campos. Nada de la atención de otro paciente.
- **Sin proveedor, no se genera**, y se dice. No hay plantilla de reemplazo
  para un resumen médico: un resumen armado por reglas se lee como si lo
  hubiera revisado alguien.
- Nace en `draft` y pasa por US-42. El móvil lo muestra en
  `features/clinical_record/` cuando está aprobado.

**Archivos:** un módulo nuevo `ai/` (o `assistant/`, acordarlo con el SM el
primer día), `frontend/src/paginas/` (bandeja), `mobile/lib/features/clinical_record/`.

**Depende de:** nadie. **Dependen de ella:** el SM (US-40, US-41) necesita la
tabla de US-42 migrada para el **14/11**.

---

### Luis Mateo Hurtado *(Scrum Master)* — *lo que se lee de la atención* — 16 h + diagrama de redes + documentación

**US-41 — Resumen del historial para el médico · 10 h · BACKEND + WEB · 🟢**

Antes de abrir una atención, el médico ve una síntesis: antecedentes de US-08
(alergias primero), diagnósticos previos, medicación activa, últimas órdenes.

- **Cada afirmación del resumen cita la atención de la que sale**, igual que
  el asistente cita sus fragmentos. Un resumen sin fuente no se puede
  verificar.
- **Lo que no se puede omitir no se le deja al modelo:** las alergias se
  muestran siempre, sacadas de la base, aunque el modelo no las mencione.
- Respeta el mismo alcance que la historia clínica: sólo el médico tratante de
  esa organización. Se prueba el borde de acceso
  (ver *historia clínica con máximo cuidado*).

**US-40 — Preparación para estudios · 6 h · BACKEND + MÓVIL · 🟢**

Para cada orden de laboratorio o imagen de US-26, instrucciones de preparación
(ayuno, medicación que suspender, qué llevar).

- **Sale primero del corpus administrativo de US-32**, que ya tiene
  preparaciones cargadas por la organización. El modelo sólo redacta sobre lo
  recuperado; si no hay fragmento, no inventa una preparación.
- Pasa por US-42 y el paciente la ve en el móvil junto a la orden.

**Diagrama de redes · 4 h**

Para el parcial y para el documento. La topología real de producción:
navegador y app Android → Internet (HTTPS) → Railway (frontend estático y API
Django con sus procesos de fondo) → Supabase (PostgreSQL con RLS, us-east-1);
y los servicios externos: Gemini, Stripe, Brevo, Firebase Cloud Messaging.
Con puertos, protocolos y qué tramo va cifrado. Exportado en PNG a
`docs/diagramas/png/Sprint4/`.

**Además, como SM:** el capítulo del Sprint 4 en el documento, Daily, Revisión
y Retrospectiva, y la release final con la APK.

**Archivos:** `encounters/`, `assistant/` (corpus de US-32),
`frontend/src/paginas/Atencion.tsx`, `mobile/lib/features/clinical_record/`.

**Depende de:** Karen (tabla de US-42, 14/11).

---

### Luis Miguel Aguayo — *el riesgo de inasistencia* — 16 h + verificación final

**US-35 — Clasificar cada ficha por riesgo de inasistencia · 16 h · BACKEND + WEB · 🔴**

Es la historia más pesada del sprint y de ella dependen Alexander y Daniel.

- **Primero, los datos.** Hoy `seed_dataset` sortea el desenlace de cada ficha
  pasada al azar (78/12/10), sin relación con nada. Un clasificador entrenado
  sobre eso no aprende y cualquier métrica que muestre es ruido. Hay que
  cambiar el generador para que la inasistencia dependa de **la anticipación
  de la reserva, si pagó por adelantado, sus faltas previas, el día y la
  hora**, y volver a poblar la base. Esto va el primer día.
- **La etiqueta es la misma inasistencia de US-29**: `no_show` sobre las fichas
  que debían atenderse. Una cancelada a tiempo no cuenta.
- Modelo simple y explicable —regresión logística o árbol, con
  `scikit-learn`— entrenado **por organización**, dentro de su
  `tenant_context`. Se guarda en `model_versions` con sus métricas.
- **Se reporta contra una línea base**: «predecir siempre que asiste». Si el
  modelo no le gana, se dice.
- Cada ficha futura tiene su predicción en `noshow_predictions` (bajo, medio,
  alto, con la probabilidad). La agenda web la muestra y filtra.

**Verificación final de las IA · 4 h** — la tarea que cierra el pendiente
«todas las IA terminadas correctamente». Ver la sección 5, regla 15: el
**21/11** recorre en producción, con la cuenta demo de cada rol, cada fila del
inventario de IA y deja el resultado en `docs/sprints/sprint-4/ia-verificacion.md`.
Lo que falle vuelve a su dueño ese mismo día.

**Archivos:** `tenancy/management/commands/seed_dataset.py`, un módulo nuevo
para el modelo (acordar con Daniel), `frontend/src/paginas/Agendas.tsx` o la
agenda del día.

**Depende de:** nadie. **Dependen de él:** Alexander (US-36) y Daniel (US-38)
necesitan las predicciones guardadas para el **15/11**.

---

### Alexander Osinaga *(Product Owner)* — *recordatorios y transacciones por voz* — 20 h

**US-36 — Recordatorios reforzados · 10 h · BACKEND · 🟡**

A las fichas con riesgo alto se les manda un segundo recordatorio, más cerca
de la hora.

- **Va en el mismo proceso de US-28**, no en otro: `send_appointment_reminders
  --loop`, una organización a la vez, en `tenant_context`.
- **Nunca dos veces**, con la misma técnica de `reminder_sent_at`: su propia
  marca, puesta en la misma transacción.
- Lee la predicción de US-35; no la calcula. Si no hay predicción para esa
  ficha, no hay refuerzo.

**US-46 — Reportes transaccionales por voz · 10 h · BACKEND + WEB + MÓVIL · 🟡** *(nueva)*

El paciente pide, hablando o escribiendo, *«mis últimas 2 facturas»*, *«los
pagos de octubre»*, *«mis fichas de cardiología»*, y ve la lista con el
**QR del comprobante** de cada una.

- **Se apoya en lo que ya está:** el reconocimiento de voz es el de la
  característica 5 (en el dispositivo), la traducción de frase a consulta sigue
  las tres reglas de `reporting/voice.py` —lista cerrada, validación contra el
  catálogo, degradación sin proveedor— y el QR es el de US-19.
- **Sólo lo propio.** La consulta está atada al paciente que habla y a sus
  dependientes, como `history_scope`. Un paciente nunca puede pedir pagos de
  otro, diga lo que diga la frase; la prueba lo intenta.
- **El modelo traduce, no responde.** Devuelve `{tipo, cantidad, desde, hasta,
  especialidad}`; los datos y los QR salen de la base. Lo que no entendió lo
  dice en `unresolved`, como el reporte del personal.
- Se puede descargar en PDF con los QR, con el exportador que ya existe.

**Archivos:** `appointments/reminders.py`, `payments/`, `appointments/receipts.py`,
`reporting/voice.py` (reutilizar, no copiar), una página nueva en
`frontend/src/paginas/` y una pantalla en `mobile/lib/features/receipts/`.

**Depende de:** Luis Aguayo, sólo para US-36 (predicciones, 15/11).

---

### José Daniel Iporo — *demanda y reentrenamiento* — 20 h

**US-37 — Proyección de demanda · 10 h · BACKEND + WEB · 🟢**

Cuántas fichas se esperan por especialidad y franja horaria en las próximas
semanas.

- **Promedio por día de la semana y franja**, con la tendencia de las últimas
  semanas. No hace falta un modelo complejo; hace falta que se explique en una
  frase y que se pueda comparar con lo que pasó.
- **Se calcula en la base**, como los KPI de US-29.
- Se muestra en el panel de `Kpis.tsx`, junto a la ocupación real, con el
  margen de error medido sobre semanas pasadas.

**US-38 — Reentrenamiento periódico · 10 h · BACKEND + WEB · 🟢**

El modelo de US-35 se vuelve a entrenar solo, con los desenlaces nuevos.

- **Comando `retrain_noshow`**, con el mismo patrón `--loop` de las copias y
  los recordatorios, organización por organización.
- **Un modelo nuevo no reemplaza al vigente si es peor.** Se compara con la
  misma métrica sobre los mismos datos de prueba; sólo se promueve si gana. Las
  dos versiones quedan en `model_versions`.
- El administrador ve qué versión está vigente, cuándo se entrenó y con qué
  resultado.

**Archivos:** `appointments/kpis.py` (o el módulo de indicadores),
`frontend/src/paginas/Kpis.tsx`, el módulo del modelo de US-35.

**Depende de:** Luis Aguayo (US-38 necesita el entrenamiento de US-35, 15/11).
US-37 arranca el primer día.

---

## 3. Dependencias

| Quién espera | A quién | Qué | Para cuándo |
|---|---|---|---|
| SM (US-40, US-41) | Karen (US-42) | Tabla `ai_generated_texts` migrada | 14/11 |
| Alexander (US-36) | Luis Aguayo (US-35) | Predicciones guardadas por ficha | 15/11 |
| Daniel (US-38) | Luis Aguayo (US-35) | Entrenamiento y `model_versions` | 15/11 |
| Todos | Luis Aguayo | `seed_dataset` con causas y base repoblada | 12/11 |

---

## 4. Ruta crítica

| Fecha | Qué tiene que estar | Quién |
|---|---|---|
| **12/11** | Generador de datos con causas; base local y de producción repobladas | Luis Aguayo |
| **14/11** | US-42 mergeada (la tabla de textos generados) | Karen |
| **15/11** | US-35 mergeada | Luis Aguayo |
| **19/11** | Backend completo y congelado; sólo pantallas, documento y pruebas | Todos |
| **20/11** | Diagrama de redes exportado | SM |
| **21/11** | Verificación de todas las IA en producción | Luis Aguayo + dueños |
| **22/11** | Release final con la APK | SM |
| **23/11** | Cierre del sprint | — |
| **24–26/11** | Revisión *(a confirmar)* | Todos |

---

## 5. Reglas que no se negocian

Siguen vigentes las del Sprint 1 (`../sprint-1/reparto.md`, sección 5), las
del Sprint 2 (`../sprint-2/reparto.md`, sección 6) y las del Sprint 3
(`../sprint-3/reparto.md`, sección 5). Se agregan tres:

14. **Ningún texto generado llega al paciente sin aprobación de un médico.**
    Todo pasa por `ai_generated_texts` y US-42. Un endpoint del paciente que
    lea un `draft` es un defecto, no una mejora.

15. **Una IA está terminada cuando cumple las cuatro, en producción:**
    1. **Funciona con Gemini** en Railway, con la cuenta demo del rol que la usa.
    2. **Degrada sin proveedor y lo dice** —sin clave, sin cuota o con un
       503—: o cae a un modo verificable o responde que no está disponible.
       Nunca inventa.
    3. **No cruza organizaciones ni pacientes**, con una prueba que lo intenta.
    4. **Tiene un número**: la métrica contra la línea base para los modelos
       (US-35, US-37, US-38) o un conjunto de 10 frases de prueba con su
       resultado esperado para las de lenguaje (US-31 a US-34, US-39 a US-41,
       US-46, reportes por voz).

16. **Los modelos se entrenan y se usan dentro de `tenant_context`.** Un modelo
    entrenado con las fichas de todas las organizaciones mezcla datos de
    clientes distintos, que es exactamente lo que el sistema promete no hacer.

### Inventario de IA a verificar el 21/11

| IA | Historia | Dueño |
|---|---|---|
| Sugerencia de especialidad | US-31 | Karen |
| Asistente administrativo | US-32 | SM |
| Reserva conversacional | US-33 | Karen |
| Barrera de urgencias | US-34 | Karen |
| Reportes por voz del personal | Característica 5 | SM |
| Riesgo de inasistencia | US-35 | Luis Aguayo |
| Recordatorio reforzado | US-36 | Alexander |
| Proyección de demanda | US-37 | Daniel |
| Reentrenamiento | US-38 | Daniel |
| Resumen de la consulta | US-39 | Karen |
| Preparación para estudios | US-40 | SM |
| Resumen del historial | US-41 | SM |
| Validación del médico | US-42 | Karen |
| Transacciones por voz del paciente | US-46 | Alexander |

---

## 6. Tareas nuevas para el Sprint Backlog del documento

La numeración del Sprint 3 llegó hasta T-43. El Sprint 4 arranca en T-44.

| ID | Tarea | Tipo | Estimación | Responsable | Prioridad |
|---|---|---|---|---|---|
| T-44 | Clasificar cada ficha por riesgo de inasistencia | Historia | 16 horas | Aguayo Quiroz, L.M. | Must have |
| T-45 | Recordatorios reforzados por riesgo alto | Historia | 10 horas | Osinaga Blanco, A. | Should have |
| T-46 | Proyección de demanda por especialidad y franja | Historia | 10 horas | Iporo Chulque, J.D. | Could have |
| T-47 | Reentrenamiento periódico del modelo | Historia | 10 horas | Iporo Chulque, J.D. | Could have |
| T-48 | Resumen claro de la consulta | Historia | 10 horas | Ortega Mancilla, K.P. | Should have |
| T-49 | Instrucciones de preparación para estudios | Historia | 6 horas | Hurtado Castro, L.M. | Could have |
| T-50 | Resumen del historial para el médico | Historia | 10 horas | Hurtado Castro, L.M. | Could have |
| T-51 | Validar o editar texto generado por IA | Historia | 6 horas | Ortega Mancilla, K.P. | Must have |
| T-52 | Reportes transaccionales por voz del paciente | Historia | 10 horas | Osinaga Blanco, A. | Should have |
| T-53 | Diagrama de redes | Documentación | 4 horas | Hurtado Castro, L.M. | Must have |
| T-54 | Verificación final de las IA en producción | Pruebas | 4 horas | Aguayo Quiroz, L.M. | Must have |

**US-46 en el Product Backlog** (para agregar al 3.6 del documento):

| ID | Sprint | Rol | Historia | Prioridad | Horas |
|---|---|---|---|---|---|
| US-46 | Sprint 4 | Paciente | Consultar por voz mis pagos, fichas y comprobantes recientes y ver el QR de cada uno. | 🟡 | **10 h** |
