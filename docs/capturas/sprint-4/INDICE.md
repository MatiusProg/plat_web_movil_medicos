# Capturas del Sprint 4: índice

Tomadas el 13/11/2026 **contra producción**, como pide la regla 17 del reparto:
- web: `platwebmovilmedicos-production-ae19.up.railway.app`
- API: `web-production-872fa.up.railway.app`
- organización **sangabriel**, con las cuentas demo; ventana de 1536 × 639.

Cuentas:
- médico: `medico1@sangabriel.test` (Mauricio Copa Choque)
- paciente: `paciente1@sangabriel.test` (Jimena Flores Fernández)

## Cómo se armó el caso

El chat necesita una atención firmada hace menos de 15 días. Mauricio atiende de lunes a jueves y el 13/11 era viernes, así que se preparó así, todo desde la web y por los flujos normales:
1. **Admin (*Agendas*, US-13):** se le agregó a Mauricio una regla de viernes de 14:00 a 18:00 en Sede Sopocachi, vigente solo el 13/11/2026. La sucursal cierra de 12:00 a 14:00, por eso no se pudo antes.
2. **Admin (*Mostrador*, US-23):** se reservó la ficha de Jimena a las 16:00 y se registró el cobro en efectivo (110 BOB, simulado).
3. **Médico:** se registró la atención: motivo, evolución, diagnóstico «Faringitis viral», indicaciones y tratamiento. Se cargó la receta (paracetamol 500 mg, 1 comprimido cada 8 horas por 5 días, después de las comidas) y se firmó a las 15:50.

## US-47: Chat con el médico tratante (CU48)

| Archivo | Caso que muestra |
|---|---|
| `US-47-00-web-paciente-mi-historia-atencion-de-hoy.png` | *Mi historia clínica* de Jimena, con la atención del 13/11 recién firmada arriba. |
| `US-47-01-web-paciente-escribir-al-medico.png` | Cada atención firmada tiene el enlace «Escribir al médico sobre esta atención →». |
| `US-47-02-web-paciente-chat-vencido.png` | **Borde: ventana vencida.** Chat de la atención del 29/09 con el mismo médico: sin caja para escribir, con «pasaron 15 días desde la atención» y el enlace para reservar una ficha. |
| `US-47-03-web-medico-chat-en-la-atencion-firmada.png` | Médico: al firmar, aparece «Consultas del paciente» debajo de la receta, con el aviso, la receta, «Cerrar conversación» y el plazo («hasta el 28 de noviembre de 2026», 15 días). |
| `US-47-04-web-medico-bandeja-vacia.png` | *Consultas de pacientes* antes de que Jimena escriba: «Ningún paciente te escribió todavía.» |
| `US-47-05-web-paciente-atencion-de-hoy.png` | La atención del 13/11 en la historia del paciente: receta, firma y el enlace al chat. |
| `US-47-06-web-paciente-chat-abierto-con-receta.png` | Chat abierto del paciente: aviso de que no es para urgencias, receta de la atención, caja para escribir y contador (0/2000). |
| `US-47-07-web-paciente-consulta-enviada.png` | Consulta sobre la medicación enviada; aparece como «Tú» y no muestra derivación. |
| `US-47-08-web-paciente-urgencia-derivada.png` | **Borde: urgencia (US-34).** Con «dolor de pecho y me falta el aire» la derivación a emergencias aparece arriba de la conversación, con «Tu mensaje le llegó a tu médico igual, pero no esperes su respuesta para ir.» |
| `US-47-09-web-paciente-chat-ajeno-no-encontrado.png` | **Borde: conversación que no es suya.** Un id de atención que no pertenece al paciente da «No encontrado», sin decir si existe. Se probó con un id inexistente. El caso de la atención real de otro paciente está cubierto por `tests/test_us47.py`. |
| `US-47-10-web-medico-bandeja-posible-urgencia.png` | Bandeja del médico: Jimena arriba, con «Posible urgencia» y «2 sin leer». |
| `US-47-11-web-medico-mensajes-con-marca-de-urgencia.png` | El médico ve el mensaje marcado «Posible urgencia: se le indicó ir a emergencias». |
| `US-47-12-web-medico-respuesta.png` | Respuesta del médico en la conversación. |
| `US-47-13-web-medico-confirmar-cierre.png` | Confirmación antes de cerrar: «¿Cerrar? El paciente ya no podrá escribir.» |
| `US-47-14-web-medico-conversacion-cerrada.png` | Conversación cerrada: sin caja para responder y con «El médico cerró esta conversación.» |
| `US-47-15-web-paciente-respuesta-y-chat-cerrado.png` | El paciente ve la respuesta del médico y el chat cerrado, con «reserva una ficha». |

## US-42: Textos de IA validados por el médico

| Archivo | Caso que muestra |
|---|---|
| `US-42-01-web-resumen-aprobado.png` | *Textos por validar* → «Aprobados»: el resumen de la consulta de Jimena (US-39) generado con `gemini-3.5-flash-lite` al firmar, marcado «Aprobado sin cambios». |

## Lo que falta

- **US-42, texto pendiente:** la captura del resumen en «Pendientes», con *Aprobar*, *Guardar sin aprobar* y *Descartar*, se guardó en baja resolución y no sirve. Se repite con la próxima atención firmada.
- **Móvil (US-47):** la pantalla del chat y el aviso push que la abre. Se toman con la APK contra producción.
