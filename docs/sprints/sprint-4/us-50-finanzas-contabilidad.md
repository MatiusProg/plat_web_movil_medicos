# US-50 — Finanzas por voz y área de contabilidad

Ampliación del 17/11. Planes **Pro y Premium** (función `accounting`). La
administración ve cuánto entra, cuánto se devuelve, cuánto se queda la pasarela,
cuánto se paga a los profesionales, cuánto se gasta y qué queda, y puede
preguntarlo hablando o escribiendo.

## Qué cuenta cada cifra

Todo va **por moneda**, nunca mezclada.

| Cifra | Regla |
| --- | --- |
| Ingresos | Pagos cobrados (`succeeded` o luego devueltos) por la fecha de cobro |
| Devoluciones | Pagos devueltos, por la fecha de **devolución** |
| Comisión | % de la pasarela sobre lo cobrado y no devuelto; el efectivo no paga |
| Honorarios | % del profesional (`Practitioner.fee_percent`) sobre lo cobrado y no devuelto |
| Gastos | Lo cargado a mano (`Expense`), por su fecha; sede o «general» |
| Utilidad | ingresos − devoluciones − comisión − honorarios − gastos |
| Ticket promedio | ingresos ÷ pagos cobrados |

Un pago cobrado en octubre y devuelto en noviembre suma en octubre y resta en
noviembre: no se cuenta dos veces. Cada comisión y honorario se redondea al
centavo por pago, así que **la suma de los grupos es siempre el total**.

## Agrupar y comparar

`sede`, `medico`, `especialidad`, `dia`, `semana`, `mes` y `trimestre`. Agrupar
es solo presentación. Un gasto que no se puede atribuir al criterio (un gasto
general ante «por médico») va a un grupo propio, «Gastos generales». Con un filtro
por médico los gastos no entran: un gasto no es de un médico. «Comparar» pone cada
tarjeta contra el período anterior de la misma duración; sin base (anterior en
cero) no da porcentaje.

## Voz

`POST /api/reporting/finance/interpret/` traduce la frase a
`{metrica, desde, hasta, agrupar, sede, profesional, comparar}`.

- **Python decide** la agrupación, la sede y el profesional, antes de llegar al
  proveedor. El modelo recibe la frase sin esas partes y solo puede llenar métrica,
  período y comparar, de una lista cerrada validada.
- **Las cifras y la frase de respuesta son de Python**, con lo que calculó
  `finance.py`. El modelo no ve datos ni los nombres de los profesionales.
- Sin proveedor (o si falla) se usa el analizador local; lo que no entiende se
  dice en `unresolved` y no se ejecuta nada.
- La bitácora asienta métrica, agrupación y si comparó. **Nunca la frase.**

Ejemplos: «cuánto ganamos este mes», «utilidad por sede del mes pasado», «cuánto
facturó la doctora Gómez en octubre», «compará este mes con el anterior», «gastos
de insumos de la sede Norte de los últimos 3 meses por semana».

## API

| Ruta | Para qué |
| --- | --- |
| `GET finance/summary/` | tarjetas, grupos, comparación (`from`, `to`, `branch`, `practitioner`, `group`, `compare`) |
| `GET finance/series/` | últimos 6 meses |
| `GET finance/export/?file=csv\|xlsx\|pdf` | la tabla agrupada |
| `POST finance/interpret/` | de la frase a la cifra |
| `GET/POST finance/expenses/`, `PATCH/DELETE finance/expenses/{id}/` | gastos |
| `GET/PUT finance/settings/` | comisión de la pasarela |

Permisos: `finance.accounting.read` (ver) y `finance.expense.manage` (cargar
gastos, comisión y honorario), solo **Administración**. Sin la función en el plan
responde 403 `plan_limit`. El honorario (%) solo lo ve y cambia quien tiene esos
permisos.

## Archivos

- Backend: `reporting/finance.py`, `finance_voice.py`, `finance_views.py`,
  modelos `Expense` y `FinanceSettings` (RLS + clave compuesta de sucursal),
  `Practitioner.fee_percent`; migraciones `reporting/0004`, `catalog/0008`,
  `tenancy/0008`.
- Web: `paginas/Contabilidad.tsx`, `api/finanzas.ts`, campo «Honorario (%)» en
  `Profesionales.tsx`, entrada «Contabilidad» en el menú.
- Pruebas: `tests/test_us50.py` y dos casos en `tests/test_isolation.py`.

## Fuera de esta entrega

Quedan como trabajo futuro, por el calendario (backend congelado el 21/11):
servicios y médicos top, cierre de caja diario en PDF, proyección del mes y
alertas (sede en pérdida, caída fuerte, gasto atípico). Tampoco hay inventario de
insumos: los insumos se cargan como gasto con categoría.

## Pendiente de verificar a mano

Capturas en 390 y 1280 px (claro y oscuro) y los casos en producción: la
herramienta del navegador no devolvió capturas en esta sesión.
