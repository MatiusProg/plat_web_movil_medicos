# US-30 — Reportes operativos exportables a PDF y Excel

> *Como administrador, quiero exportar reportes operativos a PDF y Excel para
> compartirlos con la dirección del centro médico.*

La exportación ya existía (característica general 5: CSV, Excel, HTML y PDF, en
la web y en el móvil, también por correo y por voz). Esta historia agrega **lo
que se puede reportar**: dos conjuntos de datos en `reporting/datasets.py`. No
se tocó el constructor ni las pantallas: el catálogo se dibuja solo desde
`GET /api/reporting/datasets/`.

## Los conjuntos

| Código | Qué trae | Columnas principales |
|---|---|---|
| `appointments` — **Fichas** | Una fila por ficha | fecha y hora, paciente, profesional, especialidad, sucursal, estado, **asistencia**, check-in, cancelación |
| `payments` — **Pagos** | Una fila por intento de cobro | fecha de la ficha, fecha del pago, paciente, sucursal, importe, moneda, medio de pago, estado, devolución |

Los filtros ofrecidos son los mismos que las columnas útiles: rango de fechas
(por la fecha de la **ficha**, como el panel), estado, asistencia, sucursal,
profesional, especialidad, medio de pago y moneda.

## Permiso

Los dos exigen **`reporting.kpi.read`**, el permiso del panel de US-29 (sólo la
Administración), además de `reporting.report.run` para usar el constructor.

No se usó `appointments.appointment.read`: lo tienen los pacientes para ver *sus*
fichas, y el alcance de un conjunto es toda la organización. Un reporte de pagos,
además, muestra ingresos. Recepción y profesionales no ven estos dos conjuntos
en el catálogo y reciben 403 si los piden.

## Los números coinciden con el panel

| Pregunta | Cómo sale del reporte | Coincide con |
|---|---|---|
| Fichas por estado | Fichas, filtro de fechas, y se cuentan las filas por «Estado» | — |
| Demanda por sucursal | Fichas, fechas, estado en `pending_payment`, `confirmed`, `attended`, `no_show`; contar por «Sucursal» | `demand.by_branch` |
| Inasistencias | Fichas, fechas, «Asistencia» = *Ausente* | `no_show.missed` |
| Debían atenderse | «Asistencia» = *Ausente* o *Asistió* | `no_show.expected` |
| Ingresos por sucursal | Pagos, fecha de la ficha, estado = *Pagado*; sumar «Importe» por «Sucursal» y «Moneda» | `revenue.by_branch` |

- La columna **Asistencia** se calcula con `debian_atenderse_q` e
  `inasistencia_q` de `appointments/kpis.py`, no se reescribe la regla. Una
  ficha `confirmed` que ya pasó y nunca hizo check-in figura como *Ausente*
  aunque su estado siga siendo *Confirmada*, igual que en el panel. Las demás
  (futuras, canceladas, vencidas…) son *No aplica*.
- El reporte entrega **filas, no totales**. Los totales se obtienen con la
  tabla dinámica o el autofiltro de Excel, que el archivo ya trae activado.
- Cada moneda se suma por separado; nunca se mezclan.
- Una ficha de un profesional con dos especialidades sale dos veces **sólo si se
  pide la columna «Especialidad»**, igual que en la demanda por especialidad del
  panel.

## Cambios en el motor

- `reporting/query.py`: la selección incluye la clave primaria para que
  `DISTINCT` quite sólo los duplicados de un join y no filas iguales por
  coincidencia. Antes, un reporte con pocas columnas («Estado», «Sucursal»)
  devolvía una fila por combinación y no una por registro.
- `reporting/exporters.py`: el importe (`Decimal`) llega al Excel como número,
  con formato `#,##0.00`, para poder sumarlo. Como texto no se sumaba.

## Pruebas

`backend/tests/test_us30.py`: permisos (administración sí; recepción y paciente
no), coincidencia con `/api/reporting/kpis/` en ausentes, demanda e ingresos,
una fila por ficha con pocas columnas, exportación a PDF y a Excel de ambos
conjuntos, importe numérico en el Excel y aislamiento entre organizaciones.

## Fuera de alcance

Totales y agrupaciones dentro del motor (`GROUP BY`). Si la dirección los pide
en el archivo, es una historia aparte que toca `query.py` y los exportadores.
