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

### US-47 en el móvil (17/11/2026)

Con la APK compilada desde `main` contra la API de producción, en un Xiaomi 2311DRK48G con Android 16 (1220 × 2712, capturas con `adb screencap`, a escala 1). La paciente es Jimena (`paciente1`) y el médico, Mauricio (`medico1`).

**Cómo se armó el caso.** Mauricio atiende los martes de 08:00 a 12:00 y ya eran las 17:28, así que:
1. **Admin (*Agendas*):** una regla de martes de 17:00 a 18:00 en Sede Sopocachi, vigente solo el 17/11/2026.
2. **Admin (*Mostrador*):** ficha de Jimena a las 17:30, cobro en efectivo de 110 BOB (simulado) y check-in por documento.
3. **Médico:** atención por «Rinitis alérgica» con receta de loratadina 10 mg (1 comprimido cada 24 horas por 10 días, por la noche), firmada a las 17:34.

`adb input` no escribe tildes ni signos de apertura, por eso los mensajes de la paciente van sin ellos.

| Archivo | Caso que muestra |
|---|---|
| `US-47-16-movil-escribir-al-medico.png` | La atención del 17/11 en *Mi historia clínica*, con receta, firma y el botón «Escribir al médico». |
| `US-47-17-movil-chat-abierto-con-receta.png` | Chat abierto: aviso de que no es para urgencias, receta de la atención y «Puedes escribir hasta el 2 de diciembre» (15 días). |
| `US-47-18-movil-mensaje-en-blanco-no-se-envia.png` | **Borde: mensaje vacío o de solo espacios.** Con la caja vacía y después con 5 espacios, «Enviar» no manda nada: no aparece burbuja ni llega un `POST` al servidor. |
| `US-47-19-movil-tope-2000-caracteres.png` | **Borde: tope de 2000 caracteres.** Se pegaron 2500; el campo quedó con **2000 exactos** (medido con `uiautomator`). No se envió, para no dejarle relleno al médico. En el móvil el contador está oculto (`counterText: ''`): el texto se corta sin aviso. |
| `US-47-20-movil-consulta-enviada.png` | Consulta sobre la medicación enviada, como «Tú · 17 de noviembre, 17:38». |
| `US-47-21-movil-urgencia-derivada.png` | **Borde: urgencia (US-34).** Con «Me duele mucho el pecho y me falta el aire» aparece arriba la derivación a emergencias y «Tu mensaje le llegó a tu médico igual, pero no esperes su respuesta para ir.» |
| `US-47-22-movil-push-tu-medico-te-respondio.png` | Push «Tu médico te respondió · Mauricio Copa Choque respondió tu consulta» con la app en segundo plano. Recortada para no mostrar otras notificaciones del teléfono. |
| `US-47-23-movil-push-abre-el-chat.png` | Tocar el push abre el chat de esa atención (`event=chat`) con las dos respuestas del médico. |
| `US-47-24-movil-chat-cerrado-por-el-medico.png` | **Borde: chat cerrado por el médico** desde la web: sin caja para escribir, «El médico cerró esta conversación.» y «Reservar una ficha nueva», que lleva a *Profesionales* (`/search`). |
| `US-47-25-movil-chat-vencido-15-dias.png` | **Borde: ventana vencida.** Chat de la atención del 29/09: «La conversación se cerró: pasaron 15 días desde la atención.» Tomada con el arreglo 2 de abajo. |
| `US-47-26-movil-sin-conexion-chat-abierto.png` | **Borde: sin conexión (modo avión) con el chat abierto.** El refresco de cada 10 s falla en silencio y la conversación sigue a la vista. |
| `US-47-27-movil-sin-conexion-reintentar.png` | **Borde: abrir el chat sin conexión.** «No se pudo conectar con el servidor. Revisá tu conexión.» y «Reintentar». |
| `US-47-28-movil-medico-sin-entrada-al-chat.png` | El médico en el móvil: su inicio no tiene entrada al chat de pacientes. |
| `US-47-29-movil-medico-ruta-chat-bloqueada.png` | **Borde: un médico fuerza la ruta.** Con `centromedico://app/chat/<id>` (el enlace profundo de US-18) solo ve «Esta sección es para pacientes.» (`SoloPacientes`), sin pedir la conversación. |

**Lo que salió al probar y se corrigió en este PR:**
1. **El push dejaba al paciente sin salida.** Abría el chat con `go('/chat/…')`, y como `/chat` es de primer nivel la pantalla quedaba sola en la pila: sin flecha, y «atrás» cerraba la app (`US-47-23` es de antes del arreglo). Ahora va a `/home` y apila el chat encima (`mobile/lib/app.dart`). No se pudo repetir contra producción porque las dos conversaciones de Jimena ya estaban cerradas y el push solo sale cuando el médico escribe. Se verifica con la próxima atención.
2. **El chat vencido invitaba a escribir.** Sin mensajes mostraba «Escribe tu duda sobre la medicación…» encima de «La conversación se cerró». Ahora la invitación sale solo si se puede escribir (`chat_screen.dart`). La prueba nueva de `test/chat_test.dart` falla si se quita el arreglo.

**No se probó en el móvil:** el dependiente (el titular que escribe por él). Jimena no tiene a nadie a cargo y armarlo pedía otra atención firmada hoy. Lo cubren las pruebas del backend (`tests/test_us47.py`).

## US-42: Textos de IA validados por el médico

| Archivo | Caso que muestra |
|---|---|
| `US-42-01-web-resumen-aprobado.png` | *Textos por validar* → «Aprobados»: el resumen de la consulta de Jimena (US-39) generado con `gemini-3.5-flash-lite` al firmar, marcado «Aprobado sin cambios». |
| `US-42-02-web-resumen-pendiente.png` | *Textos por validar* → «Pendientes» (17/11): el resumen de la atención de las 17:30, generado a las 17:34 con `gemini-3.5-flash-lite`, editable y con *Aprobar*, *Guardar sin aprobar* y *Descartar*. Reemplaza la del 13/11, que había quedado en baja resolución. |
| `US-42-03-web-resumen-aprobado-aviso.png` | Al aprobarlo: «Aprobado. Jimena Flores Fernández ya puede leerlo.» y la lista de pendientes vacía. |

## US-39: Resumen claro de la consulta

| Archivo | Caso que muestra |
|---|---|
| `US-39-01-web-resumen-de-la-consulta.png` | *Mi historia clínica* de Jimena en la web (17/11): «Resumen de tu consulta» arriba de la atención, con «Redactado con IA y revisado por Mauricio Copa Choque · 17 nov 2026, 17:34». Ventana de 1536 × 695. |
| `US-39-02-movil-resumen-de-la-consulta.png` | El mismo resumen en el móvil. |

## Pruebas en el celular contra producción (20/11/26)

Con la APK de main apuntando a Railway (con push) y la atención de hoy de
Jimena (`paciente1@sangabriel.test`) con Mauricio (`medico1`): receta de
GRASABYEBYE cada 8 horas por 5 días y orden de «Perfil lipídico».

| Archivo | Caso que muestra |
|---|---|
| `US-40-01-movil-como-prepararte.png` | US-40 contra el backend local (19/11). |
| `US-40-02-produccion-como-prepararte.png` | **US-40 en producción:** la orden de Perfil lipídico con «Cómo prepararte», redactado por Gemini y revisado por Mauricio. |
| `US-40-03-produccion-resumen-con-estudio.png` | El resumen de la consulta (US-39) nombra el estudio pendiente. |
| `US-49-01-movil-mis-medicamentos.png` | *Mis medicamentos*: las tres recetas de Jimena con «Recordarme» apagado. |
| `US-49-02-movil-recordarme-activo-proxima-toma.png` | Con «Recordarme» activo: «En curso», Día 1 de 5, próxima toma hoy 13:00, «Tomada» / «No la tomé». |
| `US-49-03-movil-notificacion-hora-de-tu-toma.png` | La notificación local a la 1:01: «Hora de tu GRASABYEBYE · toma 1 de 15». |
| `US-49-04-movil-notificacion-tomada-posponer.png` | La notificación abierta, con «Tomada» y «Posponer 15 min». |
| `US-49-05-movil-toma-marcada-desde-la-notificacion.png` | Tras «Tomada» desde la notificación: 1 de 15, próxima toma 21:00 e historial «hoy 13:00 · tomada». En la web, el médico ve 1/15 y el porcentaje. |
| `US-48-01-movil-defecto-sin-boton-enviar.png` | **Defecto encontrado:** con estrellas y comentario no hay botón para enviar; queda un hueco. |
| `US-48-02-movil-calificacion-enviada.png` | Con el arreglo: «Calificaste con ★★★★★», el comentario tal cual y «Cambiar (hasta el 27 de noviembre)». |
| `US-47-30-movil-produccion-mensaje-enviado.png` | La consulta de Jimena en el chat, con la receta y la orden de la atención. |
| `US-47-31-movil-produccion-respuesta-del-medico.png` | Las respuestas de Mauricio aparecen en el chat abierto. |
| `US-47-32-movil-produccion-push-tu-medico-te-respondio.png` | El push «Tu médico te respondió». |
| `US-47-33-movil-produccion-push-abre-el-chat.png` | Con el arreglo: tocar el push abre esa conversación. |
| `US-47-34-movil-produccion-atras-vuelve-al-inicio.png` | «Atrás» desde el chat abierto por el push vuelve al inicio, no cierra la app (el pendiente del 13/11). |

**Lo que salió al probar y se corrigió:**
1. **US-48: no había cómo enviar la calificación.** El tema le da al
   `FilledButton` todo el ancho (`Size.fromHeight`) y en un `Row` no se
   dibuja. Las pruebas no lo veían porque no usaban el tema de la app; ahora
   sí, y fallan sin el arreglo (`rating_card.dart`, `test/rating_test.dart`).
2. **US-47 + US-49: tocar el push no abría el chat.** El plugin de avisos
   locales es uno solo y el último `initialize` decide a quién se le avisa:
   los recordatorios se iniciaban después que el push y se tragaban el toque.
   Ahora se lo devuelven (`Recordatorios.alTocarOtroAviso`); la prueba nueva de
   `test/medications_test.dart` falla sin el arreglo.
3. **Detalle sin arreglar:** el ícono chico de las notificaciones es el de
   Flutter, no el de la app.


## US-53: Signos vitales (web local 20/11/26, móvil en producción 21/11/26)

| Archivo | Caso que muestra |
|---|---|
| `US-53-01-web-signos-normales-con-imc.png` | Valores normales: 120/80, 36,6 °C, 62 kg y 160 cm dan un **IMC de 24,2**, sin marcas. |
| `US-53-02-web-anormal-se-marca.png` | 150/95, 39,2 °C y SpO₂ 88 % se guardan y se marcan **Alta** / **Baja**. |
| `US-53-03-web-imposible-no-se-guarda.png` | **Borde:** 60 °C («El máximo posible es 45.») y una diastólica de 160 con sistólica 150 («Tiene que ser menor que la sistólica.»). |
| `US-53-04-web-firmar-bloqueado.png` | Con un signo imposible, la firma queda bloqueada: «Hay un signo vital imposible: corrígelo o bórralo.» |
| `US-53-05-web-firmada-con-enmienda.png` | Atención firmada: los signos en solo lectura, con sus marcas, el IMC y una enmienda que corrige la temperatura. |
| `US-53-06-web-historial-del-medico.png` | El historial del médico muestra los signos en la línea de tiempo. |
| `US-53-07-movil-paciente-produccion.png` | **Producción, celular:** Jimena (paciente1) ve en *Mi historia clínica* los signos que cargó Mauricio: 150/95 y 38,6 °C marcados **Alta**, IMC 25,2 y la enmienda de la temperatura debajo. |
