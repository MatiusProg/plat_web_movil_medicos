# US-53 — Signos vitales en la atención

> Como médico, quiero registrar los signos vitales en la atención, para que la
> historia tenga números y no sólo texto.

Antes de US-53, si el médico anotaba la presión, quedaba como texto suelto en
«Evolución».

## Cómo funciona

1. En la atención (web), el médico carga **presión sistólica y diastólica,
   frecuencia cardíaca, temperatura, saturación de O₂, glucosa, peso y talla**.
   - Todos son opcionales.
   - Se guardan con el mismo «Guardar borrador» y se firman con la atención.
2. Mientras escribe ve el **IMC** y lo **anormal** marcado:
   - **Alta:** presión ≥ 140/90 o temperatura ≥ 38 °C;
   - **Baja:** saturación < 92 %.

   Lo anormal **se guarda**: un paciente con 39 °C existe.
3. Lo **imposible no se guarda**: es un error de tipeo, como 60 °C, una talla de
   3 m o una diastólica mayor o igual que la sistólica.
   - La web lo marca en el campo y no deja guardar ni firmar.
   - El backend lo rechaza con un mensaje que dice el límite.
   - La base lo rechaza con `CHECK`, aunque se salte la API.
4. Firmada la atención, **no se tocan**.
   - La API responde 409 y un trigger de la base rechaza `INSERT`, `UPDATE` y
     `DELETE`.
   - Se corrigen con una **enmienda** en la sección «Signos vitales», que queda
     debajo de lo original.
5. Se ven en tres lugares, con las marcas:
   - en la atención firmada y en el historial del médico, en una **fila
     compacta**: «PA 150/95 Alta · FC 88 · T 38,6 °C Alta · IMC 25,2»;
   - en *Mi historia* del paciente, en la web y en el móvil, con su nombre
     completo.
6. **Gráficas de evolución.**
   - **Médico (web):** en el historial, la pestaña «Evolución» tiene un
     selector con los signos que se tomaron alguna vez y la gráfica del
     elegido.
   - **Paciente (web y móvil):** arriba de *Mi historia*, «Mis signos
     vitales» con la última medición y las gráficas de presión y peso.
   - Van de la atención más vieja a la más nueva, con la **franja normal
     sombreada**. El borde de arriba de la presión, la temperatura y la
     saturación es el mismo umbral que marca «Alta» o «Baja».
   - Se grafica **lo que se firmó**. Si la atención tiene una enmienda de
     signos, el punto va **hueco** y la corrección se lee en la atención: la
     gráfica no interpreta el texto de la enmienda.
   - Con una sola medición lo dice («todavía no hay evolución»). Sin signos,
     la sección no aparece.

### Franjas de referencia de las gráficas

| Signo | Franja |
|---|---|
| Presión sistólica / diastólica | 90–140 / 60–90 mmHg |
| Frecuencia cardíaca | 60–100 lpm |
| Temperatura | 36–38 °C |
| Saturación O₂ | 92–100 % |
| IMC | 18,5–25 |
| Glucosa y peso | Sin franja: la glucosa depende de si estaba en ayunas |

### Límites de lo posible (iguales en la base, la API y la web)

| Signo | Mínimo | Máximo |
|---|---|---|
| Presión sistólica (mmHg) | 50 | 300 |
| Presión diastólica (mmHg) | 20 | 200 |
| Frecuencia cardíaca (lpm) | 20 | 250 |
| Temperatura (°C) | 30 | 45 |
| Saturación O₂ (%) | 50 | 100 |
| Peso (kg) | 0,5 | 400 |
| Talla (cm) | 30 | 250 |
| Glucosa (mg/dL) | 10 | 1000 |

## Datos y base

- La tabla `encounter_vital_signs` es uno a uno con la atención. Se crea en la
  migración `encounters/0011`.
- La migración `0012` agrega:
  - RLS con `FORCE`;
  - la FK compuesta `(encounter_id, organization_id)`, para que no se pueda
    colgar de una atención de otra organización;
  - el trigger `vital_signs_solo_en_borrador`.
- La migración `0013` suma «Signos vitales» a las secciones que se pueden
  enmendar.
- **Respaldos:** la tabla viaja en la copia con `APPEND` y `draft_only_parent`,
  igual que la receta.

## Casos probados

**Backend (`backend/tests/test_us53.py`, 60 pruebas).** Están verificadas por
mutación: rompí el código 12 veces, una por cada caso de abajo, y cada vez cae
alguna prueba.

| Mutación | La detecta |
|---|---|
| Alerta de presión `>=` → `>` | `test_el_borde_de_cada_alerta` |
| Alerta de SpO₂ `<` → `<=` | `test_justo_debajo_del_borde_no_hay_alerta` |
| IMC mal calculado | `test_se_guardan_con_el_borrador_y_traen_el_imc` |
| Sistólica = diastólica aceptada | `test_la_diastolica_no_puede_ser_mayor_ni_igual` |
| Una fila vacía se muestra como objeto | `test_una_fila_vacia_se_muestra_como_null` |
| `null` no borra | `test_null_los_borra` |
| Mezclar en vez de reemplazar | `test_se_reemplazan_enteros_y_no_se_mezclan` |
| Trigger de `UPDATE`/`DELETE` desactivado | `test_la_base_no_deja_cambiarlos_firmada` |
| Trigger de `INSERT` desactivado | `test_la_base_no_deja_agregarlos_firmada` |
| Sin `FORCE` RLS | `test_otra_organizacion_no_los_ve` |
| Límite de temperatura 45 → 65 | `test_lo_imposible_se_rechaza` y otras |
| Sin validar en la API | 16 pruebas |

**Defecto que encontraron las pruebas.** Una saturación imposible (por ejemplo
101 %) devolvía un 500 en lugar del mensaje. El «(%)» del nombre del campo
rompía el formateo de DRF. Se corrigió en `_rango` y quedó cubierto por
`test_el_mensaje_de_la_saturacion_no_rompe`.

**Móvil (`test/clinical_record_test.dart`, 3 pruebas nuevas).** Comprueban que
se muestren los signos con las marcas y la enmienda, que no aparezca la sección
sin signos y que se lean bien los decimales. Están verificadas por mutación.

**Suites:**
- backend: 1561 pruebas en verde;
- móvil: 251 pruebas en verde y `flutter analyze` sin problemas;
- web: el build pasa y el lint no da errores.

## Probado en la web (20/11/26, local)

Las capturas `docs/capturas/sprint-4/US-53-01` a `US-53-06` muestran:
- valores normales con el IMC;
- lo anormal marcado;
- lo imposible en el campo y la firma bloqueada;
- la atención firmada con una enmienda de temperatura;
- el historial del médico.

## Probado en el celular contra producción (21/11/26)

Después del deploy del PR #120 (migraciones 0011–0013 aplicadas en Supabase),
con la APK nueva:
- Mauricio (medico1) firmó una atención de Jimena (paciente1) con 150/95,
  38,6 °C, 96 %, 68,5 kg y 165 cm, más una enmienda de la temperatura.
- En el celular, Jimena la ve con las marcas **Alta**, el IMC 25,2 y la
  enmienda debajo (`US-53-07`).

### Gráficas (21/11/26)

- **Web (local):** con 5 atenciones firmadas de Jimena entre julio y
  noviembre. Capturas `US-53-08` a `US-53-11`: la fila compacta, la evolución
  de la presión del médico, y «Mis signos vitales» del paciente.
  Las franjas se revisaron en modo claro y oscuro. La web no tiene pruebas
  unitarias; se probó en Chrome.
- **Móvil:** 4 pruebas nuevas en `test/clinical_record_test.dart`.
  Comprueban el orden de los puntos, la marca de la enmienda, que la última
  medición sea la más nueva con signos, el aviso con una sola medición y que
  no haya sección sin signos. Están verificadas por mutación: rompí el código
  7 veces y las pruebas lo detectaron las 7.
