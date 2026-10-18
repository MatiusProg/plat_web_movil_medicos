# US-29 — Panel de KPIs: definición de cada indicador

> Documento para US-30 (reportes operativos). Los conjuntos de datos de
> `reporting/datasets.py` deben dar **los mismos números** que el panel, así
> que reutilizan los filtros de `appointments/kpis.py` en vez de reescribirlos.

## Alcance de todo indicador

- **Rango:** `from` y `to`, fechas inclusivas, interpretadas en la zona horaria
  de la organización y aplicadas a `Appointment.starts_at`
  (`[from 00:00, to+1 00:00)`).
- **Sucursal:** filtro opcional `branch`.
- **Organización:** la de quien consulta. La aísla RLS y además cada consulta
  filtra por `organization` de forma explícita.
- **Estados que nunca cuentan:** `rescheduled` (la ficha nueva ya cuenta) y
  `expired`.
- **Se calcula en la base:** `Count(filter=...)`, `Sum` y `values().annotate()`.
  Lo único que se recorre en Python son las agendas (`Schedule`), que son pocas.

## Ocupación de agenda

`ocupación = fichas que ocuparon un espacio / espacios ofrecidos`

- **Ocuparon un espacio:** estados `pending_payment`, `confirmed`, `attended`
  y `no_show`. Una ficha cancelada libera el espacio.
- **Espacios ofrecidos:** los que derivan las agendas activas (`Schedule`) en
  el rango, con `scheduling.availability.generate_slots`, menos los que cubre
  un bloqueo activo (`ScheduleBlock`, de la organización, del profesional o de
  la sucursal).
- **Capacidad efectiva de un espacio = 1:** lo fija el índice único
  `uq_appointment_active_slot`. `Schedule.capacity` es informativo.
- Sin espacios ofrecidos la tasa es `null`, no 0.
- La tasa es la razón real: puede pasar de 1 si se reservó sobre una agenda que
  después se desactivó.

## Tasa de inasistencia

`inasistencia = fichas ausentes / fichas que debían atenderse`

- **Debían atenderse:** `attended` + `no_show` + `confirmed` cuya hora de fin ya
  pasó. **No** entran `cancelled`, `pending_payment`, `expired`, `rescheduled`
  ni `confirmed` futuras: una ficha cancelada a tiempo no es una inasistencia.
- **Ausentes:** `no_show` + `confirmed` con `ends_at` pasado y sin
  `checked_in_at`.
- **Por qué se calcula así:** hoy ningún código de producción lleva una ficha a
  `no_show`; una `confirmed` vencida que nunca hizo check-in se queda
  `confirmed`. Contarla como ausente en la consulta evita que la tasa dé 0 % y
  no exige proceso ni migración.
- Sin fichas que debían atenderse la tasa es `null`, no 0.
- Es el mismo número que el modelo de predicción del Sprint 4 intenta anticipar.

## Demanda por sucursal y por especialidad

`demanda = fichas que ocuparon un espacio`, agrupadas.

- Mismo conjunto de estados que la ocupación.
- **Por sucursal:** `Appointment.branch`.
- **Por especialidad:** `Appointment` no tiene especialidad; se llega por
  `practitioner -> PractitionerSpecialty -> Specialty`. Un profesional con dos
  especialidades **cuenta en cada una**, por lo que la suma por especialidad
  puede superar el total. El **total** se calcula aparte, sin duplicar.
  Un profesional sin especialidades cae en «Sin especialidad».

## Ingresos por fichas

`ingresos = suma de Payment.amount`

- Solo pagos `succeeded`; `refunded`, `pending`, `failed` y `expired` no suman.
- Se filtran por la **fecha de la ficha** (`appointment.starts_at`), no por
  `paid_at`, para que cuadren con el resto de los indicadores del rango.
- **Agrupados por moneda** (`Payment.currency`), nunca sumados entre monedas.
  También se desglosan por sucursal.
- Un pago transferido al reprogramar (`transfer_payment`) pertenece a la ficha
  nueva, así que no se cuenta dos veces.

## Contrato

`GET /api/reporting/kpis/?from=YYYY-MM-DD&to=YYYY-MM-DD&branch=<uuid>`

Permiso `reporting.kpi.read` (administración de la organización).

```json
{
  "range": {"from": "2026-10-01", "to": "2026-10-31", "timezone": "America/La_Paz"},
  "branch": null,
  "occupancy": {"offered": 120, "booked": 84, "rate": 0.7},
  "no_show": {"expected": 70, "missed": 9, "rate": 0.1286},
  "demand": {
    "total": 84,
    "by_branch": [{"id": "…", "name": "Centro", "total": 50}],
    "by_specialty": [{"id": "…", "name": "Pediatría", "total": 30}]
  },
  "revenue": {
    "by_currency": [{"currency": "BOB", "total": "4200.00", "payments": 42}],
    "by_branch": [{"id": "…", "name": "Centro", "currency": "BOB", "total": "2500.00"}]
  }
}
```

Las tasas son fracciones entre 0 y 1 (o `null`); la pantalla las muestra en %.
