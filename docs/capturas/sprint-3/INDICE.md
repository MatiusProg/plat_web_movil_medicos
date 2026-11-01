# Capturas del Sprint 3 — índice

Tomadas el 26/10/2026 en el **entorno local**: API `localhost:8000` y web `localhost:5173`, en la organización **sangabriel**, con datos sintéticos. Ventana de 1536 × 864. Por ahora sólo web; US-28 (sólo móvil) no tiene pantalla web. Las de US-23 y US-30 se tomaron el 01/11/2026, en el mismo entorno.

## US-26 — Receta digital y órdenes (médico)
- `11-web-atencion-con-antecedentes.png`: la atención en borrador, con la alergia declarada (sulfas) a la vista.
- `12-web-receta-y-ordenes-en-borrador.png`: dos medicamentos y dos órdenes de laboratorio, con *Quitar*.
- `13-web-confirmar-firma.png`: confirmación de la firma: firmada ya no se edita.
- `14-web-atencion-firmada.png`: la atención recién firmada (no va en el documento).
- `15-web-receta-firmada.png`: la receta firmada, sin *Quitar*, con *Descargar receta (PDF)*.
- `16-web-enmienda-a-la-receta.png`: enmienda de la sección «Receta» al lado del original.
- `17-web-receta-pdf.png`: el PDF de la receta (`receta-us26.pdf`): organización, NIT, sede, médico con matrícula, sin diagnóstico.

## US-27 — Historial, recetas e indicaciones
- `21-web-mi-historia.png`: Mi historia clínica del paciente, con la atención del día arriba.
- `22-web-mi-historia-receta-y-ordenes.png`: receta, órdenes y enmienda vistas por el paciente, con el PDF.
- `23-web-historial-del-medico.png`: historial del paciente visto por el médico (no va en el documento).
- `24-web-historial-medico-receta.png`: receta y enmienda en el historial del médico.

## US-29 — Panel de KPIs (administrador)
- `31-web-kpis.png`: ocupación, inasistencia e ingresos de los últimos 30 días.
- `32-web-kpis-demanda.png`: demanda por sucursal y por especialidad, e ingresos por sucursal.
- `33-web-kpis-filtro-sucursal.png`: el panel filtrado por Sede Calacoto.

## US-33 — Reserva conversacional (paciente)
- `41-web-asistente-horarios.png`: pedido de turno; el jueves no tiene horarios y ofrece los más próximos, con los atajos.
- `42-web-confirmar-reserva.png`: tocar un horario sólo abre la confirmación.
- `43-web-ficha-reservada.png`: ficha reservada, pendiente de pago, con *Ir a mis fichas*.
- `45-web-urgencia-sin-horarios.png`: con «dolor de pecho» el asistente deriva a emergencias y no ofrece horarios (US-34).

## US-23 — Reserva asistida en mostrador (recepción)
- `51-web-mostrador-vacio.png`: Atención en mostrador recién abierta: paciente, turno disponible y el botón de reservar todavía inactivo.
- `52-web-mostrador-paciente-elegido.png`: búsqueda «Apaza» y paciente elegido (Claudia Apaza Mendoza, CI 10100033).
- `53-web-mostrador-horario-elegido.png`: profesional (Andrea Gutiérrez Mendoza), fecha 03/11/2026 y el horario de las 09:00 en Sede Miraflores marcado.
- `54-web-mostrador-ficha-reservada.png`: aviso «Ficha reservada. Registrá el cobro antes de 15 minutos.».
- `55-web-mostrador-cobro-en-ventanilla.png`: la ficha reservada, pendiente de pago, con el importe que fija el servidor (150.00 BOB) y *Confirmar cobro en efectivo*.

## US-30 — Reportes operativos de fichas y pagos (administrador)
- `61-web-reporte-fichas-constructor.png`: constructor de reportes con el conjunto «Fichas» elegido, sus columnas y los criterios de fecha.
- `62-web-reporte-fichas-resultado.png`: vista previa de las fichas ausentes de octubre (01/10–31/10, Asistencia = Ausente), con la columna «Asistencia».
- `63-web-reporte-fichas-pdf.png`: el PDF exportado (`fichas.pdf`): criterios arriba, 141 filas en 5 páginas, fecha de generación al pie.
- `64-web-reporte-pagos-constructor.png`: conjunto «Pagos» con el criterio Estado = Pagado.
- `65-web-reporte-pagos-resultado.png`: vista previa de los pagos cobrados (2 pagos de 100 BOB).
- `66-web-reporte-pagos-excel.png`: el Excel exportado (`pagos.xlsx`) abierto: autofiltro activo e importe como número (100,00).
