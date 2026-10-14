# US-33 — Reserva conversacional en el móvil

**Para:** Mateo · **Deja:** Karen · **Fecha:** 14/10/2026

El backend (PR #77) y la web (PR #78) de US-33 están mergeados y desplegados en
Railway. Solo falta el móvil. Esta guía explica qué hay que hacer en
`mobile/lib/features/assistant/` para que la app haga lo mismo que la web.

**Referencia:** la pantalla web `frontend/src/paginas/Asistente.tsx` ya resuelve
todo este flujo. Si tienes una duda de comportamiento, lo que hace la web es lo
correcto.

---

## 1. Reglas que no se rompen

1. **El modelo propone, no reserva.** La única forma de reservar es
   `POST /api/assistant/book/`, que por dentro usa `book_appointment`.
2. **Nada se reserva sin que el paciente toque *Confirmar*.** Elegir un
   horario solo abre la hoja de confirmación.
3. **Los horarios salen del backend** (`/assistant/slots/`), nunca del texto
   de la respuesta. No armes horarios en la app.
4. **Una urgencia corta el camino a la reserva.** Si llega `emergency: true`,
   muestra la alerta roja que ya existe (`_AlertaEmergencia`) y no ofrezcas
   horarios.
5. **La conversación no se guarda en el servidor.** Vive solo en la pantalla.
   No agregues tablas ni almacenamiento local del texto del paciente.
6. **Reserva por `/assistant/book/`, no por `/appointments/appointments/`.**
   El endpoint del asistente revisa que la ficha sea del titular o de uno de
   sus dependientes y deja registro en la bitácora. El otro no hace esa
   revisión.

---

## 2. Contratos del backend (ya desplegados)

### 2.1 `POST /api/assistant/suggest/`: llega un campo nuevo

La respuesta de siempre ahora trae `booking`:

```json
"booking": {
  "available": true,
  "booking_intent": true,
  "specialty": {"id": "uuid", "name": "Cardiología"}
}
```

- `available`: el usuario puede reservar desde el asistente (tiene ficha de
  paciente y permisos, y hay especialidad). Si es `false`, no muestres nada
  de reserva.
- `booking_intent`: el mensaje pide un turno ("quiero un turno de
  cardiología el jueves"). Si es `true`, **busca los horarios sola**, sin
  esperar a que toque un botón.
- `specialty`: la especialidad para la que se buscan horarios. Puede ser
  `null`.

El campo `kind` ahora puede valer `"reserva"`.

### 2.2 `POST /api/assistant/slots/`: horarios para ofrecer

```json
// pedido
{"specialty": "uuid", "preference": "el jueves por la tarde", "branch": "uuid opcional"}
```

`preference` es texto libre de hasta 200 caracteres y puede ir vacío. Entiende
hoy, mañana, pasado mañana, los nombres de los días, "esta semana", "la
semana que viene", "fin de semana" y "por la mañana", "por la tarde", "por la
noche".

```json
// respuesta normal
{
  "emergency": false,
  "kind": "reserva",
  "answer": "No hay horarios de Cardiología a esa hora. Estos son del mismo día. Elige uno y confirma para reservar.",
  "generated_by": "regla",
  "specialty": {"id": "uuid", "name": "Cardiología"},
  "preference": {"date_from": "2026-10-15", "date_to": "2026-10-15", "days": ["2026-10-15"], "part_of_day": "tarde"},
  "matched_preference": false,
  "relaxed": "mismo_dia",
  "offers": [
    {
      "practitioner": {"id": "uuid", "full_name": "Laura Gómez"},
      "branch": {"id": "uuid", "name": "Sede Norte"},
      "schedule": {"id": "uuid"},
      "start": "2026-10-15T08:00:00-04:00",
      "end": "2026-10-15T08:30:00-04:00"
    }
  ]
}
```

- `offers` trae como máximo 6 horarios, ordenados del más cercano al más
  lejano. Si está vacío, no hay horarios: muestra `answer` y el campo para
  pedir otro día.
- `relaxed` dice qué se aflojó cuando no había nada exacto: `mismo_dia`,
  `misma_franja`, `proximos` o `null`. El texto de `answer` ya lo explica, así
  que basta con mostrar `answer`.
- **Si la preferencia describe una urgencia**, la respuesta viene con
  `emergency: true`, igual que en suggest. Trátala igual: alerta roja y sin
  horarios.
- Errores: `404 especialidad_invalida`, y `403` si el plan no tiene el
  asistente.

### 2.3 `POST /api/assistant/book/`: reservar el horario elegido

```json
{
  "patient": "uuid del titular o de un dependiente, o null para el titular",
  "practitioner": "offers[i].practitioner.id",
  "branch": "offers[i].branch.id",
  "schedule": "offers[i].schedule.id",
  "starts_at": "offers[i].start"
}
```

| Respuesta | Qué significa | Qué hace la app |
|---|---|---|
| `201` | Devuelve la ficha (mismo formato que `Appointment`), en estado `pending_payment` | Burbuja "Ficha reservada" con botón a `/appointments/{id}` |
| `409 turno_ocupado` | Otro la tomó entre que se mostró y se confirmó | Aviso "Ese horario se acaba de ocupar. Estos son los que quedan." y **volver a buscar con el mismo pedido** |
| `400` (`turno_invalido`, etc.) | El horario ya no es válido | Mostrar `detail` |
| `403 sin_ficha_de_paciente` | El usuario no es paciente | Mostrar `detail` |
| `404 paciente_invalido` | El paciente no es suyo | Mostrar `detail` |
| `403` límite del plan | Se acabaron las fichas del mes | Mostrar `detail` |

---

## 3. Qué cambiar

### 3.1 `assistant_api.dart`

1. En `AssistantReply`, agrega la pista de reserva, por ejemplo
   `final BookingHint? booking;` con `available`, `bookingIntent`,
   `specialtyId` y `specialtyName`. Léela en `fromJson` de forma tolerante,
   como el resto del archivo: si no viene, queda `null`.
2. Agrega los modelos `OfferedSlot` (practitionerId, practitionerName,
   branchId, branchName, scheduleId, start, end) y `SlotsReply` (emergency,
   answer, specialtyId, specialtyName, relaxed, offers).
3. Agrega dos funciones:
   - `Future<SlotsReply> pedirTurnos(ApiClient client, String specialtyId, String preferencia)`,
     que llama a `/assistant/slots/`.
   - `Future<Appointment> reservarDesdeAsistente(ApiClient client, {String? patientId, required OfferedSlot turno})`,
     que llama a `/assistant/book/` y reutiliza `Appointment.fromJson` de
     `features/appointments/appointments_api.dart`.
4. En modo demo (`ASSISTANT_DEMO`), haz que `pedirTurnos` devuelva un par de
   horarios de ejemplo y que `reservarDesdeAsistente` lance un `ApiError`
   diciendo que en modo ejemplo no se reserva. **En demo nunca se reserva de
   verdad.**

### 3.2 `assistant_screen.dart`

1. **Nuevos tipos de turno** en `_Turno`, como en la web: `turnos` (una
   `SlotsReply` + el pedido que la generó), `reservada` (la `Appointment`),
   `aviso` (texto corto) y el `error` de siempre, que reintenta el pedido
   correcto.
2. **Después de suggest:**
   - Si `booking.available && booking.bookingIntent`, llama sola a
     `pedirTurnos(specialtyId, mensajeOriginal)`. El mensaje del paciente
     sirve como preferencia, así se entiende "el jueves por la tarde".
   - Si `booking.available` pero no hay intención, muestra en la burbuja un
     botón **Ver horarios** junto a *Ver profesionales*. Ese botón llama a
     `pedirTurnos` con la preferencia vacía.
3. **Burbuja de horarios** (`_BurbujaTurnos`):
   - El texto `answer`.
   - Una tarjeta por oferta con fecha y hora, profesional y sede. Usa
     `formato.dart` de appointments para las fechas.
   - Chips rápidos: *Mañana*, *Por la mañana*, *Por la tarde*, *La semana que
     viene*. Cada chip agrega un turno del paciente con ese texto y vuelve a
     llamar a `pedirTurnos`.
   - Un campo "¿Otro día u horario?" con botón *Buscar*, que hace lo mismo
     con el texto escrito.
4. **Al tocar una tarjeta**, abre la hoja de confirmación con selector de
   paciente:
   - **Reutiliza `_ConfirmarReserva`** de
     `features/availability/availability_screen.dart`. Hoy es privada:
     muévela a un archivo propio (por ejemplo
     `features/appointments/confirmar_reserva_sheet.dart`) y hazla pública.
   - Hoy recibe un `SlotDisponible`. Cámbiala para que reciba solo lo que
     muestra (inicio, sede, profesional) y devuelva el `PatientOption`
     elegido. Ajusta `availability_screen.dart` para usar la versión nueva
     **sin cambiar su comportamiento**; sus pruebas
     (`test/availability_test.dart`, `test/appointments_booking_test.dart`)
     deben seguir pasando.
   - Si el paciente cierra la hoja sin confirmar, no pasa nada.
5. **Al confirmar**, llama a `reservarDesdeAsistente` con un indicador de
   carga, y luego:
   - `201`: turno `reservada` con "Queda pendiente de pago. Págala desde tus
     fichas para confirmarla." y botón **Ir a la ficha**
     (`context.push('/appointments/${ficha.id}')`).
   - `409 turno_ocupado`: turno `aviso` con el mensaje y otra llamada a
     `pedirTurnos` con el **mismo** pedido. El horario ocupado ya no
     aparece.
   - Otro `ApiError`: `SnackBar` con `error.message`.
6. **Urgencias:** si `pedirTurnos` devuelve `emergency: true`, agrega una
   burbuja con `_AlertaEmergencia` y el `answer`, sin horarios ni chips.
7. Cambia el comentario de cabecera de los dos archivos para mencionar US-33.
   Ojo: el de `assistant_api.dart` todavía dice que es un "armazón para el
   corte del 16/09".

### 3.3 Textos

Todos los textos nuevos van **en tuteo, nunca en voseo**: "Elige", "Confirma",
"Págala", nunca "Elegí", "Confirmá", "Pagala". Ojo: el `SnackBar` actual de
`availability_screen.dart` dice "Pagala" (voseo); si tocas ese archivo,
corrígelo a "Págala".

---

## 4. Pruebas (`test/assistant_test.dart`)

Usa el mismo cliente falso que ya usa el archivo. Como mínimo:

- `AssistantReply.fromJson` lee `booking` y tolera que no venga.
- `SlotsReply.fromJson` lee `offers`, `relaxed` y la urgencia.
- `pedirTurnos` manda `{specialty, preference}` a `/assistant/slots/`.
- `reservarDesdeAsistente` manda `patient`, `practitioner`, `branch`,
  `schedule` y `starts_at` a `/assistant/book/`, **nunca** a
  `/appointments/appointments/`.
- Pantalla: con `booking_intent` se muestran los horarios sin tocar nada.
- Pantalla: tocar una tarjeta **no** llama a `/assistant/book/` hasta
  confirmar en la hoja.
- Pantalla: un `409` muestra el aviso y vuelve a pedir horarios.
- Pantalla: una urgencia en slots no muestra tarjetas.

Antes de subir: `flutter analyze` y `flutter test`, todo en verde.

---

## 5. Probar en el celular contra el despliegue

```
flutter run --dart-define=API_BASE_URL=https://web-production-872fa.up.railway.app/api
```

Hay que usar una cuenta de **paciente** de una organización con agendas, por
ejemplo una de `morita2`. Cardiología (Laura Gómez) solo atiende en las
mañanas, así que "el jueves por la tarde" debería ofrecer el jueves a otra
hora (`relaxed: mismo_dia`).

**Escribe en Supabase.** Cancela cada ficha que reserves en las pruebas, desde
el detalle de la ficha o con
`POST /api/appointments/appointments/{id}/cancel/`.

---

## 6. Lista para cerrar

- [ ] `booking` leído en `AssistantReply`
- [ ] `pedirTurnos` y `reservarDesdeAsistente`, con modo demo que no reserva
- [ ] Búsqueda automática con intención y botón *Ver horarios* sin ella
- [ ] Tarjetas, chips y campo de otro día u horario
- [ ] Hoja de confirmación compartida con `availability_screen.dart`, sin
      romper sus pruebas
- [ ] `201` con botón a la ficha · `409` con aviso y nueva búsqueda · urgencia
      sin horarios
- [ ] Textos en tuteo
- [ ] Pruebas nuevas, más `flutter analyze` y `flutter test` en verde
- [ ] Probado en el celular contra Railway, con las fichas de prueba
      canceladas
