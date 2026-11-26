# Capturas del Sprint 2 — índice

Tomadas el 04/10/2026 en el **entorno local**: API `localhost:8000`, web `localhost:5173` y la app móvil en su versión web (`localhost:3000`), en un marco de teléfono de 412 px. Todas en la organización **sangabriel**, con datos sintéticos del dataset sembrado.

- Los archivos `0x-movil-…` son de la app móvil (412 × 635) y los `1x-web-…` de la web (1536 × 639).
- El pago usa la **pasarela simulada**: en local no hay claves de Stripe. Confirma la ficha por el mismo camino que el webhook. El pago con Stripe real se verificó aparte, en producción.

## US-05 — Edición de perfil
- `01-movil-mi-perfil.png`: pantalla Mi perfil en el móvil, con los datos de contacto y de la cuenta.
- `02-movil-perfil-guardado.png`: teléfono cambiado y el aviso "Tus datos se guardaron".
- `11-web-mi-perfil.png`: Mi perfil en la web.
- `12-web-perfil-guardado.png`: teléfono editado y el aviso "Tus datos se guardaron".

## US-09 — Búsqueda de pacientes (recepción, web)
- `11-web-busqueda-por-documento.png`: búsqueda exacta por documento (10100023).
- `12-web-busqueda-por-apellido-sin-tilde.png`: búsqueda parcial "fernandez" sin tilde, que encuentra "Fernández" en nombre y apellido.

## US-10 — ABM de pacientes (web)
- `11-web-pantalla-gestion-de-pacientes.png`: la pantalla de gestión, con buscador y formulario de alta.
- `12-web-alta-formulario-completo.png`: alta manual con el formulario completo.
- `13-web-alta-paciente-registrada.png`: la paciente nueva aparece en los resultados.
- `14-web-editar-paciente.png`: formulario de edición.
- `15-web-edicion-guardada.png`: teléfono corregido en la lista.
- `16-web-baja-logica-confirmacion.png`: confirmación de la baja, que aclara que el registro permanece.
- `17-web-paciente-inactivo.png`: la paciente queda "Inactivo" (baja lógica, no física).
- `18-web-fusion-elegir-origen-destino.png`: "Fusionar duplicados", con origen y destino elegidos (como administrador).
- `19-web-fusion-confirmacion.png`: confirmación de la fusión: quién se absorbe y quién se conserva.
- `20-web-fusion-origen-inactivo.png`: después de fusionar, el origen queda inactivo y el destino hereda el teléfono.

## US-17 — Reserva de ficha
- `01-movil-disponibilidad-del-profesional.png`: turnos libres de la profesional, por día y sede.
- `02-movil-para-quien-es-la-ficha.png`: hoja "Reservar ficha" con "¿Para quién es la ficha?".
- `03-movil-ficha-reservada-pendiente.png`: ficha creada "Pendiente de pago", con el importe y el vencimiento.
- `04-movil-mis-fichas.png`: lista Mis fichas con los estados.
- `11-web-disponibilidad-profesional.png`: Disponibilidad consolidada en la web.
- `12-web-modal-reservar.png`: modal de reserva.
- `13-web-ficha-reservada-pendiente.png`: aviso "Ficha reservada. Quedó pendiente de pago".

## US-18 — Pago en línea
- `01-movil-ficha-pendiente-pagar.png`: ficha pendiente con el botón "Pagar Bs 100.00".
- `02-movil-aviso-antes-de-pagar.png`: diálogo previo: importe y aviso de que la confirmación llega sola.
- `03-pasarela-de-pago.png`: pasarela de pago (simulada en local), abierta desde la app.
- `04-pago-recibido-volver-a-la-app.png`: página de regreso, con el botón "Volver a la aplicación".
- `05-movil-ficha-confirmada-tras-pagar.png`: la app vuelve a consultar y la ficha queda "Confirmada" ("¡Pago recibido!").
- `11-web-mis-fichas-pagar.png`: Mis fichas en la web, con "Pagar Bs 100.00".
- `12-web-pasarela-de-pago.png`: pasarela abierta desde la web.
- `13-web-vuelta-pago-confirmado.png`: regreso automático a Mis fichas con "Pago confirmado".

## US-19 — Comprobante digital con QR
- `01-movil-comprobante-qr.png`: comprobante con el QR firmado y los datos de la ficha.
- `02-movil-mis-comprobantes.png`: "Mis comprobantes" guardados en el teléfono.
- `03-movil-comprobante-sin-conexion.png`: el comprobante abierto **sin conexión**, con el aviso "Sin conexión — copia guardada".
- `11-web-comprobante-qr.png`: modal del comprobante con QR en la web.

## US-20 — Cancelación y reprogramación
- `01-movil-cancelar-ficha-sin-pagar.png`: diálogo de cancelar una ficha sin pagar ("no hay nada que devolver").
- `02-movil-cancelar-ficha-pagada-politica.png`: diálogo de cancelar una ficha pagada, con la política de devolución.
- `11-web-reprogramar-elegir-horario.png`: modal Reprogramar con los horarios libres.
- `12-web-reprogramar-horario-elegido.png`: horario nuevo elegido.
- `13-web-ficha-reprogramada.png`: aviso "Ficha reprogramada"; la original queda "Reprogramada".
- `14-web-cancelada-con-devolucion.png`: cancelación a tiempo de una ficha pagada: "Se devolvió el pago".

## US-21 — Confirmación de asistencia
- `01-movil-boton-confirmar-asistencia.png`: ficha confirmada con "Confirmar que voy a asistir".
- `02-movil-asistencia-confirmada.png`: "Asistencia confirmada el …", con la fecha registrada.
- `11-web-boton-confirmar-asistencia.png`: botón "Confirmar asistencia" en la web.
- `12-web-asistencia-confirmada.png`: marca "✓ Confirmaste tu asistencia".
- `13-correo-enlace-confirmar-asistencia.png`: página del enlace del correo, con el botón "Sí, voy a asistir".
- `14-correo-asistencia-confirmada-gracias.png`: "¡Gracias! Confirmaste tu asistencia".

## US-22 — Check-in en recepción (web)
- `11-web-checkin-pegar-codigo-qr.png`: "Por QR", con el código del comprobante pegado.
- `12-web-checkin-realizado.png`: "Check-in realizado": paciente, profesional y estado Atendido.
- `13-web-rechazo-ya-utilizado.png`: el mismo código otra vez: "Esta ficha ya registró su check-in".
- `14-web-rechazo-codigo-alterado.png`: código modificado: "La firma del comprobante no es válida".

## US-24 — Registro de la atención (médico, web)
- `11-web-medico-atencion-del-dia.png`: fichas del día de la médica.
- `12-web-rechazo-ficha-de-otro-dia.png`: intentar atender una ficha de otro día: "se atiende el día del turno".
- `13-web-abrir-atencion-con-antecedentes.png`: atención abierta en borrador, con los antecedentes declarados.
- `14-web-formulario-de-atencion-completo.png`: motivo, evolución, diagnóstico, indicaciones y tratamiento.
- `15-web-confirmar-firma.png`: aviso de que una atención firmada no se edita.
- `16-web-atencion-firmada.png`: "Firmada por Ana Castro Fernández", en solo lectura.

## US-25 — Historia clínica
- `01-movil-paciente-mi-historia-clinica.png`: Mi historia clínica del paciente en el móvil, con filtros por sucursal.
- `11-web-paciente-mi-historia-clinica.png`: la misma vista en la web.
- `12-web-medico-historial-del-paciente.png`: historial del paciente visto por la médica, con la atención recién firmada.

## US-31 — Sugerencia de especialidad por síntomas
- `01-movil-sugerencia-especialidad.png`: rodilla → Traumatología, con "Ver profesionales" y "En qué se basa".
- `11-web-sugerencia-especialidad.png`: manchas en la piel → Dermatología.
- `12-web-fragmentos-en-que-se-basa.png`: el fragmento recuperado y su similitud.

## US-32 — Consultas administrativas
- `01-movil-costo-de-consulta.png`: costo y preparación de la consulta.
- `11-web-horario-de-sucursal.png`: horario, dirección y profesionales de la Sede Calacoto.
- `12-web-preparacion-y-costo.png`: análisis de sangre: precio y ayuno.

## US-34 — Derivación a emergencia
- `01-movil-derivacion-a-emergencia.png`: síntomas graves → aviso rojo de urgencia en el móvil.
- `11-web-derivacion-a-emergencia.png`: la misma derivación en la web.

## No se pudo capturar
- **Checkout real de Stripe:** en local no hay claves; se usa la pasarela simulada. El checkout real (checkout.stripe.com) se probó en producción, pero no se guardó como captura.
- **Correo recibido en el buzón (US-21):** el correo real se envió por Brevo en producción. Se capturaron las páginas del enlace, no la bandeja de entrada.
- **Vuelta automática a la app nativa:** el enlace `centromedico://` sólo abre la app instalada en un teléfono. En el navegador se capturó la página con el botón.
- **Búsqueda de pacientes en el móvil (US-09/US-10):** esas historias sólo existen en la web.
- **Asistencia offline:** el estado sin conexión se simuló cortando las peticiones del marco, no apagando la red.
