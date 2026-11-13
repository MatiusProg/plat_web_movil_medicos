# US-39 — Casos del resumen de la consulta

Corrida del 12/11/2026 20:49 con `gemini-3.5-flash-lite`: **10 de 10 casos cumplen.**

Generado por `python manage.py evaluate_consultation_summary`. Las atenciones son inventadas (ningún paciente real). Qué se comprueba: los tres apartados, que nombre cada medicamento recetado, que no nombre medicamentos que no están, que no invente cuándo volver, tuteo y largo. Ver el docstring del comando.

| # | Caso | Resultado |
|---|---|---|
| 1 | Cefalea tensional con control al mes | Cumple |
| 2 | Faringitis bacteriana sin fecha de control | Cumple |
| 3 | Hipertensión con laboratorio y control a los tres meses | Cumple |
| 4 | Diabetes tipo 2 recién diagnosticada | Cumple |
| 5 | Gastritis sin antibióticos | Cumple |
| 6 | Lumbalgia con radiografía | Cumple |
| 7 | Control de niño sano sin receta | Cumple |
| 8 | Infección urinaria con urocultivo | Cumple |
| 9 | Rinitis alérgica | Cumple |
| 10 | Dermatitis con volver si empeora | Cumple |

## 1. Cefalea tensional con control al mes

**Datos de la atención:**

```
Motivo de consulta: Dolor de cabeza de tres días.
Diagnóstico: Cefalea tensional.
Indicaciones: Pausas activas en el trabajo. Control en un mes.
Tratamiento: Analgésico por cinco días.
Receta:
- Paracetamol 500 mg, 1 comprimido, cada 8 horas, durante 5 días
```

**Resumen generado:**

```
Qué encontramos
Tienes dolor de cabeza de tres días.
El diagnóstico es cefalea tensional, que significa dolor de cabeza por tensión.

Qué tienes que hacer
Haz pausas activas en el trabajo.
Toma Paracetamol de 500 mg, un comprimido, cada 8 horas, durante 5 días.

Cuándo volver
Tu control es en un mes.
```

## 2. Faringitis bacteriana sin fecha de control

**Datos de la atención:**

```
Motivo de consulta: Dolor de garganta y fiebre de dos días.
Diagnóstico: Faringoamigdalitis bacteriana.
Indicaciones: Abundantes líquidos. Completar el tratamiento.
Tratamiento: Antibiótico por siete días.
Receta:
- Amoxicilina 500 mg, 1 cápsula, cada 8 horas, durante 7 días. Completar aunque se sienta mejor
```

**Resumen generado:**

```
Qué encontramos
Tienes dolor de garganta y fiebre de dos días, lo que es una infección en la garganta y las amígdalas causada por bacterias.

Qué tienes que hacer
Toma Amoxicilina 500 mg, una cápsula cada 8 horas, durante 7 días, y completa el tratamiento aunque te sientas mejor.
Toma abundantes líquidos.

Cuándo volver
Consulta con tu médico cuándo debes volver.
```

## 3. Hipertensión con laboratorio y control a los tres meses

**Datos de la atención:**

```
Motivo de consulta: Control de presión arterial.
Diagnóstico: Hipertensión arterial esencial, en tratamiento.
Indicaciones: Dieta baja en sal, caminar 30 minutos al día. Control en tres meses con resultados.
Tratamiento: Continuar antihipertensivo.
Receta:
- Losartán 50 mg, 1 comprimido, cada 24 horas, durante 3 meses
Estudios pedidos:
- Laboratorio: Creatinina y potasio
```

**Resumen generado:**

```
Qué encontramos
Revisamos cómo está tu presión arterial.
Tienes la presión arterial alta pero estás con tratamiento.

Qué tienes que hacer
Toma Losartán 50 mg, un comprimido, cada 24 horas, durante 3 meses.
Come con poca sal.
Camina 30 minutos al día.
Hazte los estudios de laboratorio de creatinina y potasio.

Cuándo volver
Vuelve al control en tres meses con los resultados.
```

## 4. Diabetes tipo 2 recién diagnosticada

**Datos de la atención:**

```
Motivo de consulta: Sed y cansancio de un mes.
Diagnóstico: Diabetes mellitus tipo 2.
Indicaciones: Plan de alimentación sin azúcares simples. Control en dos semanas.
Tratamiento: Hipoglucemiante oral.
Receta:
- Metformina 850 mg, 1 comprimido, cada 12 horas, durante hasta el control. Con las comidas
Estudios pedidos:
- Laboratorio: Hemoglobina glicosilada (En ayunas)
```

**Resumen generado:**

```
Qué encontramos
Tuviste sed y cansancio de un mes.
El diagnóstico es diabetes mellitus tipo 2, que significa que tu cuerpo tiene problemas para manejar el azúcar en la sangre.
Te pidieron un estudio de laboratorio que es hemoglobina glicosilada, el cual debes hacerte en ayunas.

Qué tienes que hacer
Sigues un plan de alimentación sin azúcares simples.
Tomas Metformina 850 mg, 1 comprimido, cada 12 horas, durante hasta el control. Con las comidas.

Cuándo volver
Tu control es en dos semanas.
```

## 5. Gastritis sin antibióticos

**Datos de la atención:**

```
Motivo de consulta: Ardor en el estómago después de comer.
Diagnóstico: Gastritis aguda.
Indicaciones: Evitar picantes, café y alcohol. Comer en horarios fijos.
Tratamiento: Protector gástrico por cuatro semanas.
Receta:
- Omeprazol 20 mg, 1 cápsula, en ayunas cada mañana, durante 4 semanas
```

**Resumen generado:**

```
Qué encontramos
Sentiste ardor en el estómago después de comer.
Tienes gastritis aguda, que es la inflamación de la pared del estómago.

Qué tienes que hacer
Toma Omeprazol 20 mg, 1 cápsula, en ayunas cada mañana, durante 4 semanas.
Evita los picantes, el café y el alcohol.
Come en horarios fijos.

Cuándo volver
Consulta con tu médico cuándo debes volver a control.
```

## 6. Lumbalgia con radiografía

**Datos de la atención:**

```
Motivo de consulta: Dolor de espalda baja después de levantar peso.
Diagnóstico: Lumbalgia mecánica aguda.
Indicaciones: Reposo relativo, calor local. Volver con la radiografía en una semana.
Tratamiento: Antiinflamatorio por cinco días.
Receta:
- Ibuprofeno 400 mg, 1 comprimido, cada 8 horas, durante 5 días. Después de las comidas
Estudios pedidos:
- Imagenología: Radiografía de columna lumbar
```

**Resumen generado:**

```
Qué encontramos
Tienes dolor de espalda baja después de levantar peso, lo que se conoce como lumbalgia mecánica aguda, que es un dolor muscular y de las articulaciones de la espalda baja causado por un esfuerzo.

Qué tienes que hacer
Debes hacer reposo relativo y aplicar calor local.
Toma Ibuprofeno 400 mg, 1 comprimido, cada 8 horas, durante 5 días, después de las comidas.
Debes hacerte el siguiente estudio: Radiografía de columna lumbar.

Cuándo volver
Debes volver con la radiografía en una semana.
```

## 7. Control de niño sano sin receta

**Datos de la atención:**

```
Motivo de consulta: Control de rutina.
Diagnóstico: Niño sano. Crecimiento y desarrollo adecuados.
Indicaciones: Continuar alimentación variada. Vacunas al día.
```

**Resumen generado:**

```
Qué encontramos
Control de rutina.
Niño sano.
Crecimiento y desarrollo adecuados.

Qué tienes que hacer
Continuar alimentación variada.
Vacunas al día.

Cuándo volver
Consúltalo con tu médico.
```

## 8. Infección urinaria con urocultivo

**Datos de la atención:**

```
Motivo de consulta: Ardor al orinar de dos días.
Diagnóstico: Infección urinaria baja no complicada.
Indicaciones: Tomar dos litros de agua al día. Control en diez días con el urocultivo.
Tratamiento: Antibiótico por cinco días.
Receta:
- Nitrofurantoína 100 mg, 1 cápsula, cada 12 horas, durante 5 días
Estudios pedidos:
- Laboratorio: Urocultivo (Primera orina de la mañana)
```

**Resumen generado:**

```
Qué encontramos
Infección urinaria baja no complicada, que es una infección en la parte baja de las vías urinarias.

Qué tienes que hacer
Tomar dos litros de agua al día.
Nitrofurantoína 100 mg, 1 cápsula, cada 12 horas, durante 5 días.
Hacerte el siguiente estudio de laboratorio: Urocultivo (Primera orina de la mañana).

Cuándo volver
Control en diez días con el urocultivo.
```

## 9. Rinitis alérgica

**Datos de la atención:**

```
Motivo de consulta: Estornudos y congestión nasal cada mañana.
Diagnóstico: Rinitis alérgica.
Indicaciones: Evitar el polvo y ventilar la habitación.
Tratamiento: Antihistamínico por diez días.
Receta:
- Loratadina 10 mg, 1 comprimido, cada 24 horas, durante 10 días
```

**Resumen generado:**

```
Qué encontramos
Vemos estornudos y congestión nasal cada mañana.
El diagnóstico es rinitis alérgica, que es una inflamación dentro de la nariz causada por alergia al polvo u otras cosas del ambiente.

Qué tienes que hacer
Debes evitar el polvo y ventilar la habitación.
Toma Loratadina 10 mg, 1 comprimido, cada 24 horas, durante 10 días.

Cuándo volver
Consulta con tu médico cuándo debes volver.
```

## 10. Dermatitis con volver si empeora

**Datos de la atención:**

```
Motivo de consulta: Manchas rojas con picazón en los brazos.
Diagnóstico: Dermatitis de contacto.
Indicaciones: No usar el detergente nuevo. Volver si en una semana no mejora.
Tratamiento: Crema por siete días.
Receta:
- Hidrocortisona crema 1 %, capa fina, cada 12 horas, durante 7 días. Sobre la zona afectada
```

**Resumen generado:**

```
Qué encontramos
Manchas rojas con picazón en los brazos, que es una reacción en la piel por tocar algo que te causó irritación o alergia.

Qué tienes que hacer
No usar el detergente nuevo.
Usar Hidrocortisona crema 1 %, aplicandocapa fina sobre la zona afectada cada 12 horas, durante 7 días.

Cuándo volver
Volver si en una semana no mejora. Si tienes dudas sobre esto, consúltalo con tu médico.
```
