# US-36 — Recordatorio reforzado: definiciones

> Documento para quien revise o continúe US-36 y para el capítulo del Sprint 4
> del documento. Lee lo que guarda US-35 (`us-35-riesgo-inasistencia.md`) y
> se apoya en el proceso de recordatorios de US-28. El código está en
> `backend/appointments/reminders.py`.

## Qué hace

A las fichas que US-35 calificó con riesgo **alto** de inasistencia se les
manda un **segundo recordatorio**, más cerca de la hora. Sale por push y por
correo, igual que el primero.

No es un proceso nuevo: corre en la misma vuelta de
`send_appointment_reminders --loop` (cada 15 minutos), una organización a la
vez y dentro de su `tenant_context`. Se apaga con `APPOINTMENT_REMINDERS=off`,
junto con el primero.

## Cuándo sale

Una ficha recibe el refuerzo cuando se cumplen **todas** estas condiciones:

| Condición | Por qué |
| --- | --- |
| Está `confirmed` | Una ficha sin pagar, cancelada o ya pasada no se refuerza |
| Empieza dentro de las próximas 3 horas | Es el aviso "más cerca de la hora" |
| Se reservó antes de que empezara esa ventana de 3 horas | Lo recién confirmado ya recibió el aviso de confirmación |
| Su predicción de US-35 es de nivel `high` | Es lo que la historia pide |
| Esa predicción es de un modelo que sigue vigente | Sin modelo vigente no hay predicción |
| El plan de la organización incluye `noshow_prediction` | La predicción de un centro que bajó de plan ya no se usa |
| `reinforced_reminder_sent_at` es nulo | Nunca dos veces |

**Se lee la predicción, no se calcula.** Si la ficha no tiene predicción —no hay
modelo, el plan no lo incluye o `score_noshow` todavía no la calificó— no hay
refuerzo. Una ficha sin calificar es mejor que una calificada con nada.

### Relación con el primer recordatorio

Los dos avisos son **independientes**: cada uno tiene su marca y su ventana.

| | Primer recordatorio (US-28) | Reforzado (US-36) |
| --- | --- | --- |
| A quién | Toda ficha confirmada | Sólo las de riesgo alto |
| Cuándo | Dentro de las 24 h previas | Dentro de las 3 h previas |
| Marca | `reminder_sent_at` | `reinforced_reminder_sent_at` |
| Evento de notificación | `recordatorio` | `recordatorio_reforzado` |

Una ficha de riesgo alto reservada con tres días de anticipación recibe los
dos: uno el día anterior y otro unas horas antes. Una reservada con menos de 24
horas y más de 3 recibe el reforzado pero no el primero, porque el aviso de
confirmación acaba de salir.

## Cómo se evita mandarlo dos veces

Es la técnica de US-28, sin cambios:

1. Cada ficha se toma con `select_for_update(skip_locked=True)`.
2. Se manda el aviso y se pone `reinforced_reminder_sent_at` **en la misma
   transacción**.
3. Si el proceso se reinicia, o el contenedor viejo y el nuevo conviven durante
   un despliegue, la segunda vuelta ya no encuentra la ficha.

Dos detalles propios de esta historia:

- El bloqueo es `of=("self",)`: sólo se bloquea la ficha, no la fila de la
  predicción con la que se une la consulta. Así `score_noshow` puede seguir
  actualizando predicciones mientras se envía.
- **Se marca aunque el envío falle.** Un correo que rebota o un paciente sin
  teléfono registrado fallarían en cada vuelta, para siempre.

## Qué se guarda

Una columna nueva, sin tabla nueva:

| Tabla | Columna | Qué |
| --- | --- | --- |
| `appointments` | `reinforced_reminder_sent_at` | Cuándo salió el segundo recordatorio. `NULL` es que todavía no salió |

La migración es `appointments/0007_appointment_reinforced_reminder_sent_at.py`.
Sólo agrega una columna nula: `appointments` ya tiene RLS forzado desde la
migración `0002`, así que no hay políticas nuevas.

## Qué dice el aviso

| Canal | Contenido |
| --- | --- |
| Push | Título "Tu ficha empieza pronto". Cuándo, con quién y dónde. Pide cancelar si no puede ir |
| Correo | Los datos de la ficha, el enlace para confirmar asistencia (sólo si no la confirmó) y la invitación a cancelar para liberar el turno |

**El texto no dice por qué se manda.** US-35 decidió que el paciente no ve
cómo lo califica el centro: el riesgo no viaja en `AppointmentSerializer`. El
refuerzo respeta lo mismo, y una prueba comprueba que ni el push ni el correo
contienen palabras como "riesgo", "inasistencia" o "probabilidad".

## Configuración

| Variable | Por omisión | Qué hace |
| --- | --- | --- |
| `APPOINTMENT_REINFORCED_REMINDER_HOURS` | `3` | Horas antes de la ficha a las que sale el refuerzo |
| `APPOINTMENT_REMINDER_HOURS` | `24` | Horas del primer recordatorio (US-28) |
| `APPOINTMENT_REMINDERS` | `on` | `off` apaga los dos recordatorios |

`APPOINTMENT_REINFORCED_REMINDER_HOURS` tiene que ser **menor** que
`APPOINTMENT_REMINDER_HOURS`; si no, el segundo aviso no llegaría "más cerca
de la hora".

## Cómo se usa

El refuerzo necesita que la organización tenga el plan Premium y un modelo
vigente con predicciones guardadas (ver US-35). Para verlo funcionar en local:

```bash
python manage.py seed_dataset --only <slug> --password <clave>
python manage.py train_noshow --organization <slug>
python manage.py score_noshow
python manage.py send_appointment_reminders
```

La última línea imprime dos contadores:

```text
Recordatorios de fichas: 3 enviado(s).
Recordatorios reforzados: 1 enviado(s).
```

En producción no hay que hacer nada: `scripts/start.sh` ya lanza
`send_appointment_reminders --loop` junto a gunicorn.

## Limitaciones conocidas

- **La predicción puede tener hasta una hora.** `score_noshow --loop` corre
  una vez por hora. Si una ficha cambia de riesgo entre dos vueltas, el
  refuerzo usa el último nivel guardado.
- **El aviso sale entre 3 h y 2 h 45 min antes.** El proceso da una vuelta cada
  15 minutos y manda lo que ya está dentro de la ventana.
- **Una ficha reservada con menos de 3 horas no se refuerza.** Acaba de
  recibir el aviso de confirmación.
- **Sólo push y correo.** No hay SMS ni WhatsApp.
- **No se mide todavía si el refuerzo reduce las ausencias.** Las predicciones
  de fichas pasadas se conservan (US-35), así que es posible comparar después
  la tasa de inasistencia con y sin refuerzo; esa medición no es de esta
  historia.

## Casos de prueba

Los casos automatizados están en `backend/tests/test_us36.py`:

- Quién recibe el refuerzo: riesgo alto sí; medio, bajo y sin predicción no.
- Que sale más cerca de la hora que el primero, y que los dos son
  independientes.
- Que nunca se manda dos veces.
- Las fichas que no corresponden: pendientes, canceladas, pasadas, lejanas y
  recién confirmadas.
- Sin modelo vigente y sin el plan que incluye la predicción.
- Que el texto no revela el riesgo.
- Aislamiento entre organizaciones, y que una que falla no frena a las demás.
- El comando y el apagado con `APPOINTMENT_REMINDERS=off`.

Los resultados obtenidos y las capturas contra producción se completan al
cerrar la historia (regla 17).
