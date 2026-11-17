# Sprint 4: ampliación del 17/11 (seis historias nuevas)

**Fecha:** 17/11/26. **Se suma a:** `reparto.md`, que sigue siendo el contrato del sprint. Este documento agrega **US-48 a US-53** y corre la ruta crítica.

## Por qué hay ampliación

En la revisión del 17/11 la ingeniera dejó una lista de pendientes. Para el sistema pidió:
- *«Buscar un plus a la hora de comprar, no se conformen con el comprobante.»*
- *«Revisar que los comandos de voz hagan todo de la manera más simplificada posible, por ejemplo ganancias, utilidad, un área de contabilidad.»*
- *«Calificación por estrella, cosas así, para tener datos estadísticos.»*
- *«Si terminaron su US, hagan más.»*

Un CRM también lo mencionó como opcional. **No entra:** un centro médico no vende productos como una farmacia, y no hay a quién hacerle seguimiento comercial que no cubran ya las fichas, los recordatorios y el chat.

Con las tres de la ingeniera, el grupo decidió sumar **tres propuestas propias**, elegidas con un criterio:
- que usen piezas que ya existen;
- que den datos que se puedan medir;
- que se noten en la demo.

Las tres se buscaron en lo que ofrecen hoy los sistemas de clínicas de la región (Medilink, AgendaPro, Medesk, Clinic Cloud), y ninguna existe todavía en nuestro código.

Daniel confirmó el 17/11 que terminó US-37 y US-38 y que las sube después. Por eso él toma una de las nuevas.

---

## 1. Reparto

| US | Historia | Origen | Dueño | Capas | Horas | Prioridad |
|---|---|---|---|---|---|---|
| **US-48** | Calificación de la atención con estrellas | Ingeniera | Karen | Backend + Web + Móvil | 6 | Must have |
| **US-49** | Recordatorio para tomar los medicamentos | Propuesta | Karen | Backend + Móvil | 8 | Should have |
| **US-50** | Finanzas por voz y área de contabilidad | Ingeniera | Alexander | Backend + Web | 10 | Must have |
| **US-51** | Plus en la compra de la ficha | Ingeniera | Daniel | Backend + Web + Móvil | 6 | Must have |
| **US-52** | Lista de espera con aviso de cupo liberado | Propuesta | Luis Miguel | Backend + Web + Móvil | 10 | Should have |
| **US-53** | Signos vitales con gráficas de evolución | Propuesta | Luis Mateo (SM) | Backend + Web + Móvil | 8 | Should have |

**Total de la ampliación: 48 horas.** El sprint pasa de 106 a **154 horas**.

| Integrante | Antes | Ampliación | Total |
|---|---|---|---|
| Karen | 16 | US-48 + US-49 = 14 | 30 |
| Luis Mateo (SM) | 30 | US-53 = 8 | 38 + documentación |
| Luis Miguel | 20 | US-52 = 10 | 30 |
| Alexander | 20 | US-50 = 10 | 30 |
| Daniel | 20 | US-51 = 6 | 26 |

**Criterio**, el mismo de siempre: cada historia va a quien ya es dueño del módulo.
- **Karen:** lo que habla con el paciente, es decir la calificación y los recordatorios de la receta.
- **Alexander:** pagos y voz.
- **Daniel:** la compra. Es la más chica y terminó lo suyo.
- **Luis Miguel:** la inasistencia, de la que la lista de espera es la otra cara.
- **SM:** la atención, donde se registran los signos vitales.

---

## 2. Las historias

### US-48: Calificación de la atención con estrellas (Karen, 6 h)

> **Como** paciente atendido, **quiero** calificar mi atención con estrellas **para** que la clínica sepa cómo la atendieron.
> **Como** administrador, **quiero** ver el promedio por médico, especialidad y sede **para** tener datos con los que decidir.

**Por qué esta historia.** La pidió la ingeniera *«para tener datos estadísticos»*. Hoy el sistema mide cuánto se atiende (US-29), pero no **cómo**: no hay una sola señal de la experiencia del paciente.

**Qué hace:**
- Al firmarse la atención, el paciente puede calificarla de **1 a 5 estrellas**, con un comentario opcional de hasta 500 caracteres.
- **Una sola calificación por atención.** Se puede corregir durante 7 días y después queda fija.
- Solo califica quien fue atendido: el paciente o el titular de su dependiente, con el mismo alcance que la historia clínica (`history_scope`).
- El admin ve los promedios por médico, especialidad y sede, cuántas calificaciones hay y la distribución de 1 a 5. Los comentarios se ven sin el nombre del paciente.
- **El médico ve su promedio, pero no quién lo calificó.**

**Cómo se tiene que ver:**
- **Móvil:** debajo de cada atención firmada en *Mi historia clínica*, una tarjeta «¿Cómo te atendieron?» con cinco estrellas grandes que se tocan y un campo de comentario. Ya calificada, muestra «Calificaste con ★★★★☆» y «Cambiar» mientras queden días.
- **Web, paciente:** lo mismo en *Mi historia clínica*.
- **Web, admin:** una tarjeta nueva «Satisfacción» en `Kpis.tsx`:
  - el promedio grande (★ 4,3 de 120 calificaciones);
  - las barras de distribución de 1 a 5;
  - una tabla por médico y especialidad que se ordena;
  - los últimos comentarios.

**Dónde:** un modelo `EncounterRating` en `encounters/`, la pantalla `MiHistoria.tsx`, la tarjeta en `Kpis.tsx` y `mobile/lib/features/clinical_record/`.

**Bordes que se prueban (regla 17):**
- Calificar una atención que no es tuya o que no está firmada.
- Calificar dos veces.
- Corregir pasados los 7 días.
- Estrellas en 0, 6 o no numéricas.
- Un comentario de 501 caracteres.
- Otra organización.
- Que el médico no vea el nombre del paciente en ningún endpoint.

---

### US-49: Recordatorio para tomar los medicamentos (Karen, 8 h)

> **Como** paciente, **quiero** que la app me avise cuándo tomar cada medicamento de mi receta **para** no olvidarme ni dejar el tratamiento a medias.

**Por qué esta historia.** Dejar el tratamiento a medias es una de las razones más comunes por las que un paciente no mejora y vuelve a consulta. El sistema ya tiene todo para atacarlo:
- la receta estructurada, con dosis, frecuencia y duración (`PrescriptionItem`);
- la app en el teléfono del paciente;
- el chat con el médico si tiene dudas (US-47).

Además da un dato que hoy no existe: el **cumplimiento del tratamiento**.

**Qué hace:**
- En la receta de una atención firmada, el paciente toca **«Activar recordatorios»** en cada medicamento.
- La app programa **notificaciones locales** según la frecuencia y la duración: «cada 8 horas por 5 días» son 15 avisos.
  - El paciente elige la hora de la primera toma.
  - No depende del servidor ni de la conexión.
- **Si la frecuencia no se entiende** («según dolor»), no se inventa un horario. Se dice «Esta indicación no tiene horario fijo» y no se ofrece el recordatorio.
- El aviso trae **«Tomada»** y **«Posponer 15 min»**.
- Las tomas marcadas se mandan al servidor. El médico ve en la historia «Cumplimiento: 12 de 15 tomas (80 %)».

**Cómo se tiene que ver (móvil):**
- En la receta, cada medicamento tiene un interruptor «Recordarme» y, al activarlo, el selector de la hora de la primera toma.
- Una pantalla nueva, **«Mis medicamentos»**, desde el inicio:
  - los tratamientos en curso con una barra de progreso (día 3 de 10);
  - la próxima toma;
  - el historial de tomadas y salteadas.
- La notificación dice «Hora de tu Loratadina 10 mg: 1 comprimido».
- **Web del médico:** en la atención y en el historial, una línea «Cumplimiento del tratamiento» con el porcentaje por medicamento.

**Dónde:**
- `mobile/lib/features/medications/` (nuevo), con `flutter_local_notifications`.
- Un modelo `MedicationIntake` en `encounters/`.
- Un intérprete de frecuencia en `encounters/frequency.py`: «cada N horas», «N veces al día», «cada 24 horas», «una vez al día».

**Bordes que se prueban:**
- Frecuencias que no se entienden.
- Duración vacía.
- Marcar una toma de una receta ajena.
- Marcar dos veces la misma toma.
- Que al desinstalar o cerrar sesión se cancelen los avisos.
- Un medicamento de un dependiente, que lo maneja el titular.

---

### US-50: Finanzas por voz y área de contabilidad (Alexander, 10 h)

> **Como** administrador, **quiero** preguntar en voz alta *«¿cuánto ganamos este mes?»* y ver la respuesta, **para** conocer la situación de la clínica sin armar un reporte.

**Por qué esta historia.** La ingeniera pidió que los comandos de voz sean *«lo más simplificado posible»*, con ganancias, utilidad y un área de contabilidad.
- Hoy los reportes por voz (característica 5) arman una **tabla**: sirven, pero para una pregunta de plata hay que leer filas y sumar.
- Lo que falta es una **respuesta directa** y una pantalla que muestre las cuentas de la clínica.

**Qué hace:**
- **Área de contabilidad** (pantalla nueva, solo administración), por período, sede y médico:
  - **Ingresos:** pagos con estado pagado.
  - **Devoluciones:** pagos devueltos.
  - **Comisión de la pasarela:** porcentaje configurable por proveedor (Stripe; en efectivo es 0).
  - **Honorarios médicos:** porcentaje configurable **por profesional**, sobre lo cobrado de sus fichas.
  - **Utilidad** = ingresos − devoluciones − comisión − honorarios.
- **Preguntas por voz o escritas**, con respuesta en una frase y su número:
  - «¿Cuánto ganamos este mes?» → «Este mes ingresaron Bs 12.450 y la utilidad fue de Bs 5.180.»
  - «Utilidad por sede del mes pasado» → la frase y la tabla.
  - «¿Cuánto facturó la doctora Castro en octubre?»
  - «Compará este mes con el anterior» → la variación en %.
- **Las cifras las calcula el backend, no el modelo.** Gemini solo traduce la frase a una consulta (período, agrupación, filtro), igual que en `reporting/voice.py`. Sin proveedor, cae a las reglas de `_guess` y lo dice.

**Cómo se tiene que ver (web):**
- *Contabilidad* en el menú de administración.
- Arriba, cuatro tarjetas: Ingresos, Devoluciones, Honorarios y Utilidad, con la variación contra el período anterior.
- En el medio, un gráfico de barras de ingresos contra utilidad por mes, de los últimos 6 meses.
- Abajo, la tabla por sede o por médico, que se exporta con los exportadores que ya existen.
- Un **micrófono** arriba a la derecha («Preguntale a tus números»). La respuesta sale en un globo arriba de las tarjetas y las tarjetas se filtran a lo que se preguntó.
- En *Profesionales*, un campo nuevo «Honorario (%)».

**Dónde:** `reporting/finance.py` (nuevo), `reporting/voice.py` (un tipo de pregunta más), `frontend/src/paginas/Contabilidad.tsx` y el campo de honorario en `catalog/`.

**IA:** entra al inventario de la regla 15 con su conjunto de 10 frases de prueba.

**Bordes que se prueban:**
- Una recepcionista o un médico piden contabilidad.
- Otra organización.
- Un período sin pagos (da 0, no un error).
- Honorario mayor que 100 % o negativo.
- Una frase ambigua.
- Sin proveedor.
- Un pago devuelto que no se cuenta dos veces.

---

### US-51: Plus en la compra de la ficha (Daniel, 6 h)

> **Como** paciente que acaba de pagar su ficha, **quiero** tener a mano todo lo que necesito para ir **para** no olvidarme y llegar preparado.

**Por qué esta historia.** La ingeniera pidió *«no conformarse con el comprobante»*. Hoy, al pagar, el paciente recibe el comprobante con QR y nada más. Pero lo que necesita es:
- acordarse del día;
- saber cómo llegar;
- saber si tiene que ir en ayunas.

Las tres cosas el sistema ya las sabe y no se las da.

**Qué hace.** Al confirmar el pago, en la pantalla de éxito, en *Mis fichas* y en el correo de confirmación:
- **«Agregar a mi calendario»:** un archivo `.ics` con la fecha, la hora, la sede, la dirección y un aviso 24 h antes. Funciona con Google Calendar, Outlook y el calendario del teléfono.
- **«Cómo llegar»:** abre el mapa con la ubicación de la sede. Ya están `latitude` y `longitude` en la sucursal.
- **«Cómo prepararte»:** si el servicio es un estudio con indicaciones (`Service.preparation`, por ejemplo «Ayuno de 6 horas y la vejiga llena»), salen destacadas. Si no tiene, la tarjeta no aparece.
- **Cuenta regresiva:** «Faltan 2 días para tu ficha con Mauricio Copa Choque».

**Cómo se tiene que ver:**
- **Web:** la pantalla de pago exitoso deja de ser solo el comprobante. Arriba va el comprobante con su QR, como hoy; debajo, tres tarjetas en fila (**Calendario**, **Cómo llegar**, **Cómo prepararte**) con su ícono y su botón; y la cuenta regresiva.
- **Móvil:** las mismas tres tarjetas en columna. «Cómo llegar» abre Google Maps.
- **Correo:** los mismos tres enlaces y el `.ics` adjunto.

**Dónde:** `appointments/calendar.py` (nuevo, genera el `.ics`), un endpoint `GET /appointments/<id>/calendar.ics`, `MisFichas.tsx`, la pantalla de pago, `mobile/lib/features/appointments/` y la plantilla del correo de `notifications/services.py`.

**Bordes que se prueban:**
- Bajar el `.ics` de una ficha ajena.
- Una ficha cancelada (no da `.ics`).
- Una sede sin coordenadas (no aparece «Cómo llegar»).
- Un servicio sin preparación.
- Un `.ics` válido: se parsea en la prueba y tiene la zona horaria `America/La_Paz`.
- Una ficha de un dependiente.

---

### US-52: Lista de espera con aviso de cupo liberado (Luis Miguel, 10 h)

> **Como** paciente que no encontró turno, **quiero** anotarme en lista de espera **para** que me avisen si alguien libera uno.
> **Como** clínica, **quiero** que un turno cancelado se vuelva a ocupar **para** no perder la consulta.

**Por qué esta historia.**
- US-35 predice quién va a faltar y US-36 lo recuerda dos veces, pero cuando alguien **cancela**, el turno hoy queda vacío.
- La lista de espera es la otra mitad del problema de la inasistencia: **convierte el hueco en una consulta**, y eso es plata para la clínica.
- En los sistemas de la región que revisamos no aparece como función propia.

**Qué hace:**
- Si la búsqueda no encuentra turno con un médico (o en una especialidad) para los días que el paciente quiere, aparece **«Anotarme en lista de espera»**, con el rango de fechas que le sirve.
- Cuando se **cancela** una ficha (`cancel_appointment`), se busca en la lista al **primero que encaje** (mismo médico o especialidad, fecha dentro de su rango) y se le manda un push y un correo: «Se liberó un turno el jueves a las 10:00 con Mauricio Copa Choque».
- **El turno se le guarda 15 minutos.** Si no lo toma, pasa al siguiente.
- Al reservar, la entrada se cierra sola. Las entradas vencen al pasar su rango de fechas.
- El admin ve cuántos se anotaron, cuántos tomaron el turno y la **tasa de recuperación** (turnos cancelados que se volvieron a ocupar).

**Cómo se tiene que ver:**
- **Móvil y web, paciente:**
  - En la búsqueda sin resultados, en vez de «No hay turnos», una tarjeta «¿Querés que te avisemos?» con el rango de fechas y el botón.
  - En *Mis fichas*, una sección «En lista de espera» con su posición («Sos el 2.º») y «Salir de la lista».
- **El aviso:** al tocarlo abre el turno reservado temporalmente, con un contador de 15:00 y el botón «Tomar este turno».
- **Web, admin:** en *Riesgo de inasistencia* (US-35), una tarjeta «Lista de espera» con los anotados por médico y la tasa de recuperación del mes.

**Dónde:** `appointments/waitlist.py` (nuevo), un modelo `WaitlistEntry`, el gancho en `appointments/changes.py::cancel_appointment` (con `on_commit`, como el aviso de cancelación), `BuscarProfesionales.tsx`, `MisFichas.tsx`, `mobile/lib/features/search/` y `.../appointments/`.

**Bordes que se prueban:**
- Dos pacientes compiten por el mismo cupo (solo uno se lo queda).
- El turno guardado vence y pasa al siguiente.
- Anotarse dos veces al mismo médico.
- Anotarse por un dependiente.
- Un rango de fechas en el pasado.
- Otra organización.
- Una cancelación de un turno que ya pasó (no avisa).
- Que el aviso no diga nada de otro paciente.

---

### US-53: Signos vitales con gráficas de evolución (Luis Mateo, 8 h)

> **Como** médico, **quiero** registrar los signos vitales en la atención y ver cómo evolucionan **para** decidir con datos y no de memoria.
> **Como** paciente, **quiero** ver mi presión o mi peso a lo largo del tiempo.

**Por qué esta historia.**
- Nuestra historia clínica registra motivo, evolución, diagnóstico y receta, pero **no tiene un solo número**: los signos vitales, si se anotan, quedan como texto libre en «Evolución».
- Es lo primero que tiene cualquier historia clínica real.
- Habilita lo que el resto del sistema no puede: **ver una tendencia**, como la presión que sube consulta tras consulta.

**Qué hace:**
- En la atención, un bloque «Signos vitales» con presión arterial (sistólica/diastólica), frecuencia cardíaca, temperatura, saturación de oxígeno, peso, talla y glucosa.
- **El IMC se calcula solo.** Todos los campos son opcionales.
- **Rangos de validación** que rechazan lo imposible: una temperatura de 60 °C o una talla de 3 m no se guardan.
- Un **rango de alerta** que marca lo anormal sin bloquearlo: presión ≥ 140/90, saturación < 92 %, temperatura ≥ 38 °C.
- Se firman con la atención y después no se editan, igual que el resto.
- **Gráficas de evolución** por signo vital, con una línea a lo largo de las atenciones firmadas y la franja normal sombreada.

**Cómo se tiene que ver:**
- **Web, médico:**
  - En `Atencion.tsx`, una grilla de campos chicos con su unidad (mmHg, lpm, °C, %, kg, cm, mg/dL). El valor fuera de rango se pinta en ámbar con «Alto».
  - En el historial, una pestaña «Evolución» con un gráfico por signo y un selector.
- **Web y móvil, paciente:** en *Mi historia clínica*, una sección «Mis signos vitales» con la última medición y su gráfico (peso, presión).
- **En la atención firmada:** una fila compacta, «PA 120/80 · FC 72 · T 36,5 °C · SpO₂ 98 % · IMC 24,1».

**Dónde:** un modelo `VitalSigns` (uno a uno con `Encounter`) en `encounters/`, `Atencion.tsx`, `Historial.tsx`, `MiHistoria.tsx` y `mobile/lib/features/clinical_record/`.

**Bordes que se prueban:**
- Valores fuera de lo posible.
- Editar después de firmar.
- Ver los signos de un paciente ajeno.
- IMC sin talla (no se calcula).
- Una atención sin signos (la gráfica no se rompe).
- Otra organización.

Va **verificada por mutación**, porque toca la historia clínica (regla 17).

---

## 3. Lo que vale para las seis

- **Regla 17, sin excepción.** Cada historia entra a `main` con tres cosas:
  - pruebas de bordes;
  - sus casos en el 2.3.1;
  - **capturas contra producción** en `docs/capturas/sprint-4/`, agregadas al `INDICE.md`.
- **Nada nuevo cruza organizaciones:** todo modelo nuevo lleva `organization` y todo se consulta dentro de `tenant_context`.
- **Planes:**
  - La contabilidad (US-50) y la lista de espera (US-52) son de **Pro y Premium**.
  - Las estrellas (US-48), el plus de la compra (US-51), los recordatorios (US-49) y los signos vitales (US-53) van en **todos los planes**, porque son del paciente o de la historia clínica.
- **El móvil sale en una sola APK final** (v1.6.0) con todo lo del sprint. Cada uno avisa al SM cuando lo suyo del móvil está en `main`.

## 4. Ruta crítica, corrida

| Fecha | Qué tiene que estar | Quién |
|---|---|---|
| 17/11 | US-37 y US-38 subidas | Daniel |
| **20/11** | US-48 a US-53 mergeadas (backend, web y móvil) | Cada dueño |
| **21/11** | Backend congelado: solo correcciones, pantallas, documento y pruebas | Todos |
| **22/11** | Verificación de todas las IA en producción (se suma US-50) | Luis Miguel + dueños |
| **22/11** | Release final con la APK v1.6.0 | SM |
| 23/11 | Cierre del sprint y documento preliminar para revisar | SM |
| 24–26/11 | Revisión *(a confirmar)* | Todos |

## 5. Tareas nuevas para el Sprint Backlog del documento

| Id | Tarea | Tipo | Estimación | Responsable | Prioridad |
|---|---|---|---|---|---|
| T-58 | Calificación de la atención con estrellas | Historia | 6 horas | Ortega Mancilla, K.P. | Must have |
| T-59 | Recordatorio para tomar los medicamentos | Historia | 8 horas | Ortega Mancilla, K.P. | Should have |
| T-60 | Finanzas por voz y área de contabilidad | Historia | 10 horas | Osinaga Blanco, A. | Must have |
| T-61 | Plus en la compra de la ficha | Historia | 6 horas | Iporo Chulque, J.D. | Must have |
| T-62 | Lista de espera con aviso de cupo liberado | Historia | 10 horas | Aguayo Quiroz, L.M. | Should have |
| T-63 | Signos vitales con gráficas de evolución | Historia | 8 horas | Hurtado Castro, L.M. | Should have |

Los casos de uso siguen la numeración del documento: **CU49 a CU54**, en el mismo orden que US-48 a US-53.

## 6. El documento (Word)

Lo que la ingeniera pidió del documento final (artefactos finales, calificaciones, conclusiones, bibliografía y anexos) se trabaja aparte. Como siempre, **primero en copias preliminares**, que no se suben a OneDrive hasta que se revisen.
