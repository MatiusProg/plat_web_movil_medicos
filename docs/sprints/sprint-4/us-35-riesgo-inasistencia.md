# US-35 — Riesgo de inasistencia: definiciones

> Documento para US-36 (recordatorio reforzado) y US-38 (reentrenamiento), que
> leen lo que esta historia guarda, y para el capítulo del Sprint 4 del
> documento. El código está en `backend/noshow/`.

## Qué hace

Cada ficha futura (`pending_payment` o `confirmed`, dentro de los próximos 60
días) recibe un **riesgo de inasistencia**: *bajo*, *medio* o *alto*, con su
probabilidad y las razones que más pesaron. La Administración lo ve en
`/riesgo-inasistencia` y puede filtrar por fecha, sucursal y nivel.

Es una función del **plan Premium** (`noshow_prediction`). Un modelo por
organización, entrenado y usado dentro de su `tenant_context` (regla 16).

## La etiqueta

La misma inasistencia de US-29 (`us-29-indicadores.md`): se reutilizan
`debian_atenderse_q` e `inasistencia_q` de `appointments/kpis.py`.

- **Ausente:** `no_show`, o `confirmed` cuya hora de fin ya pasó y sin check-in.
- **Entra al entrenamiento:** `attended`, `no_show` y `confirmed` vencida.
- **No entra:** `cancelled`, `pending_payment`, `expired`, `rescheduled` ni
  `confirmed` futuras. Una ficha cancelada a tiempo no es una inasistencia.

## Las variables

| Variable | Qué mide | Por qué |
|---|---|---|
| `lead_days` | Días entre la reserva y el turno (tope 60) | Reservar con mucha anticipación deja tiempo para olvidarse |
| `paid_early` | Pagó al menos 24 h antes del turno | Pagar en ventanilla el mismo día no compromete a nadie de antemano |
| `prior_no_shows` | Faltas del paciente en fichas que terminaron antes de ésta (tope 5) | Quien faltó, vuelve a faltar |
| `prior_visits` | Veces que sí fue, con el mismo criterio (tope 20) | Un paciente con historial se comporta distinto del nuevo |
| `dow_0` … `dow_5` | Día de la semana, lunes a sábado (el domingo es la base) | Lunes y sábado se falta más |
| `afternoon` | El turno es de las 14:00 en adelante | La tarde se pierde más que la mañana |

**Sin fuga de datos.** Las faltas previas cuentan sólo fichas del mismo paciente
que *terminaron* antes de que empezara la ficha; nunca la propia ni las
posteriores. En entrenamiento y al predecir se usa el mismo código
(`noshow/features.py`).

**Lo que no entra, a propósito:** `attendance_confirmed_at`. En una ficha vieja
ya tiene su valor final y en una futura todavía no existe: entrenar con él
enseñaría algo que al predecir no se sabe. Queda para una versión posterior.

## El modelo

Regresión logística (`scikit-learn`) con las variables estandarizadas. Se eligió
porque cada coeficiente se puede decir en una frase y porque con unos cientos de
fichas por centro un modelo más flexible sólo memoriza.

- **Corte temporal:** el 80 % más antiguo entrena; el 20 % más reciente mide.
- **Mínimos:** 200 fichas con desenlace y 20 ausencias. Con menos no se entrena
  ni se crea versión: la pantalla dice «sin datos suficientes».
- **Se guarda como JSON** (`model_versions.params`: variables, coeficientes,
  intercepto, media y escala). Sin pickle: predecir es una suma y una logística
  (`noshow/scoring.py::predict_proba`).

### Contra qué se mide

La línea base del reparto es *«predecir siempre que asiste»*. Con 12 % de
ausencias ya acierta casi el 88 %, así que la exactitud no sirve para juzgar al
modelo. Se reportan:

| Métrica | Qué dice |
|---|---|
| **Brier** del modelo contra el de predecir siempre la tasa base | Error de las probabilidades; más bajo es mejor |
| **AUC** | ¿Pone las ausencias por encima de las asistencias? 0,5 es azar |
| **Recall y precisión del nivel alto** | De las ausencias reales, cuántas marcó; de las que marcó, cuántas lo eran |
| **Exactitud de «siempre asiste»** | Se muestra, pero no decide |

**El modelo es vigente sólo si le gana a la línea base** (Brier menor y AUC
mayor que 0,5). Si no, la versión queda `rejected`, nunca se usa y la pantalla
lo explica. Lo hace cumplir también la base de datos
(`ck_model_version_supera_base`).

### Los niveles

Relativos a la tasa base de cada organización (la del entrenamiento):

- **Alto:** probabilidad ≥ 2 × tasa base.
- **Medio:** probabilidad ≥ 1,2 × tasa base.
- **Bajo:** el resto.

Un corte fijo (0,4, por ejemplo) casi nunca marcaría «alto» en un centro con 10 %
de ausencias.

## Qué se guarda

| Tabla | Qué |
|---|---|
| `model_versions` | Cada modelo entrenado, con su estado (`active`, `candidate`, `rejected`, `retired`), sus parámetros y sus métricas. Una sola `active` por organización |
| `noshow_predictions` | La predicción vigente de cada ficha futura: probabilidad, nivel, razones, versión que la calculó |

Las dos con RLS forzado y claves compuestas `(x_id, organization_id)`: una
predicción no puede colgar de una ficha ni de un modelo de otra organización.
Las predicciones de fichas que ya pasaron **no se borran**: permiten medir
después cuánto acertó el modelo.

## Cómo se usa

```
python manage.py seed_dataset --only <slug> --password ...   # organización nueva, 180 días en una pasada
python manage.py train_noshow --organization <slug>          # entrena (o --all)
python manage.py score_noshow                                # puntúa las fichas futuras
```

`seed_dataset --history <slug>` existe para una organización que **ya existe** y
todavía no tiene fichas de hace más de 60 días; una organización nueva no lo
necesita (ver «Limitaciones conocidas»).

## Qué se midió con datos reales del generador

`seed_dataset --only urbari` (250 pacientes, 180 días de fichas), entrenado con
`train_for`:

| | Modelo | Línea base |
|---|---|---|
| Brier (más bajo es mejor) | **0,120** | 0,139 |
| AUC | **0,77** | 0,5 |
| Nivel alto: cobertura de las ausencias | **56 %** | — |
| Nivel alto: precisión | **42 %** | — |
| Reparto de las fichas futuras | 22 % alto · 17 % medio · 61 % bajo | — |

Los coeficientes salen en el orden que el generador les dio: faltas previas,
pago por adelantado y anticipación son los tres que más pesan. Con datos del
generador, la ausencia es ~13 % si el paciente pagó por adelantado y ~29 % si no.

**El número de pacientes importa.** Con 100 pacientes y 180 días (unas 21 fichas
por paciente) todos acumulaban faltas hasta saturar el riesgo: el 55 % de las
fichas futuras salía «alto» y el nivel dejaba de servir para priorizar. Con 250
(unas 8 fichas por paciente) el reparto es el de arriba. Con 400 la separación
del modelo empeora (AUC 0,74), por eso se fijó en 250.

En producción `score_noshow --loop` corre junto a gunicorn (`scripts/start.sh`),
una vuelta por hora. Se apaga con `NOSHOW_SCORING=off`. El entrenamiento es
explícito.

## Para quien viene después

- **US-36** lee `NoShowPrediction.level` (`"high"`). Si la ficha no tiene
  predicción, no hay refuerzo. Verificar además el estado de la ficha: las filas
  de fichas canceladas o pasadas se conservan.
- **US-38** reutiliza `noshow.training.train_for(organization)`: crea la versión
  y, si ya hay una vigente, la deja `candidate` sin reemplazarla.
  `noshow.training.promote(version)` hace el cambio (retira a la anterior y
  activa la nueva en una transacción) y se niega si la versión no supera la base.
  Comparar versiones con la misma métrica y los mismos datos de prueba, y decidir
  cuándo promover, es de esa historia.

## API

`GET /api/noshow/appointments/?from=&to=&branch=&level=&page=&page_size=`
(sin `from`/`to`: de hoy a 14 días) y `GET /api/noshow/model/`. Permiso
`appointments.noshow.read` (sólo la Administración) y plan con
`noshow_prediction`. **El riesgo no viaja en `AppointmentSerializer`**: lo leen
el paciente, el móvil y el mostrador, y el paciente no ve cómo lo califica el
centro. Una prueba lo comprueba.

## Limitaciones conocidas

- **Pocos datos por organización.** Con unos cientos de fichas el modelo puede
  no superar la línea base; en ese caso el sistema lo dice y no califica.
- **El generador siembra el pasado en una sola pasada.** Una organización nueva
  recibe `DIAS_DE_HISTORIA` (180) días de fichas en orden cronológico. No es un
  detalle: las faltas previas de un paciente son una causa de su próxima
  ausencia y sólo valen si se contaron desde el principio. Medido: con 60 días
  recientes más 150 de historial sembrados *por separado*, el modelo predecía
  24 % de ausencias donde había 16 %, perdía contra la línea base y quedaba
  rechazado, aunque cada ventana por sí sola tenía señal (AUC 0,79 y 0,66). El
  sistema hizo lo correcto —no calificar con un modelo malo— y el defecto estaba
  en los datos.
- **Organizaciones sembradas antes de US-35.** Sus últimos 60 días tienen
  desenlaces al azar y `created_at` igual al día de la siembra. Agregarles
  `--history` produce el mismo descalibrado de arriba, así que con ellas el
  modelo puede quedar rechazado. Para la demostración, sembrar una organización
  nueva; para producción, ver el reparto.
- **La tasa de ausencia depende de cuántas fichas tenga cada paciente.** Una
  falta previa aumenta la probabilidad de la siguiente y el generador lo
  acumula; con pocos pacientes la tasa sube con el tiempo (ver arriba). Con los
  250 de `PATIENTS` la tasa base ronda el 12 %, igual que el generador anterior,
  y el panel de KPIs (US-29) no cambia de orden de magnitud.
- **Las atenciones firmadas no se pueden borrar** (triggers de US-24), por eso
  no se puede «repoblar» una organización: sólo agregarle historial más viejo.

## Casos de prueba

Los casos automatizados están en `backend/tests/test_us35.py` (variables y
etiqueta, entrenamiento, puntuación, API, y las garantías de la base de datos).
Los resultados obtenidos y las capturas contra producción se completan al
cerrar la historia (regla 17).
