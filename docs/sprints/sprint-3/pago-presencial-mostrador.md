# Pago presencial — lo que necesita el mostrador de US-23

**Para:** Daniel · **Deja:** Alexander · **Fecha:** 15/10/2026

El reparto del Sprint 3 deja el cobro en efectivo en ventanilla a cargo de
`payments` (Alexander) para el **17/10**, y la ficha asistida en mostrador
(US-23) a cargo tuyo. El medio de pago ya está: viene en el mismo pull request
que esta guía. Aquí está su contrato, cómo encaja en tu flujo y qué te queda a
ti.

**Referencia:** `backend/tests/test_pago_presencial.py` usa el endpoint de
punta a punta. Si tienes una duda de comportamiento, lo que hacen esas pruebas
es lo correcto.

---

## 1. Reglas que no se rompen

1. **El importe lo decide el backend.** El endpoint no recibe monto: lo
   calcula `payments.pricing.quote`, igual que el pago en línea. No mandes ni
   muestres un monto escrito a mano.
2. **La ficha se confirma solo por este endpoint.** Por dentro pasa por
   `confirm_payment`, el mismo camino que el webhook de Stripe. No cambies
   `Appointment.status` a `confirmed` en tu módulo.
3. **No depende del pago en línea del plan.** El plan Básico no trae
   `online_payment` y es justamente el que cobra en ventanilla. No agregues
   `require_feature(..., "online_payment", ...)` al mostrador.
4. **Se cobra antes de que venza la reserva.** `book_appointment` deja la
   ficha `pending_payment` con un vencimiento de `APPOINTMENT_HOLD_MINUTES`
   (15 minutos). En el mostrador se reserva y se cobra en el acto, así que
   alcanza; si vence, el cobro responde `400 ficha_vencida`.
5. **Solo cobra quien tiene `payments.payment.register_cash`.** Lo tienen
   Recepción y la Administración del centro. **No se lo des al rol
   Paciente**: el cobro en ventanilla no pasa por la app.

---

## 2. Contrato del backend

### `POST /api/payments/appointments/{id}/cash/`

Recepción registra que cobró la ficha en efectivo. **Sin cuerpo.** La ficha
queda `confirmed` en el acto.

```json
// 201
{
  "payment_id": "uuid",
  "provider": "cash",
  "amount": "150.00",
  "currency": "BOB",
  "status": "succeeded",
  "appointment": { "...": "la ficha, mismo formato que /appointments/appointments/{id}/",
                   "status": "confirmed", "payment_status": "succeeded" }
}
```

| Respuesta | Qué significa | Qué hace la pantalla |
|---|---|---|
| `201` | Cobrado; la ficha quedó confirmada | Mostrar "Cobrado" y ofrecer el check-in |
| `400 ficha_no_pendiente` | La ficha ya está pagada, cancelada o atendida | Mostrar `detail` |
| `400 ficha_vencida` | Pasaron los 15 minutos de la reserva | Mostrar `detail` y volver a reservar |
| `403` | El usuario no tiene `payments.payment.register_cash` | Mostrar `detail` |
| `404` | La ficha no existe en la organización | Mostrar `detail` |
| `409 ficha_ya_pagada` | Otra recepcionista la cobró en el mismo instante; este cobro quedó **devuelto** | Mostrar `detail` ("devuelve el efectivo") |

El medio de pago nuevo es `Payment.Provider.CASH`, con valor `"cash"` y la
etiqueta **"Efectivo en ventanilla"**. Cada cobro deja dos registros en la
bitácora (`payment.movement`, eventos `cobro_en_ventanilla` y `pagado`), a
nombre de quien cobró.

---

## 3. Cómo encaja en tu flujo de mostrador

1. **Buscar o dar de alta al paciente** con el ABM de US-10, sin salir de la
   pantalla.
2. **Reservar a su nombre.** Ojo: **Recepción hoy no tiene
   `appointments.appointment.create`**, que es del rol Paciente. Tu módulo de
   mostrador en `appointments/` necesita su propio permiso (por ejemplo
   `appointments.appointment.book_at_counter`), sembrado para `receptionist` y
   `org_admin` con el mismo mecanismo que
   `backend/payments/migrations/0005_seed_cash_permission.py`. Por dentro
   llama a `book_appointment` y al control del plan, como hace
   `AppointmentViewSet.create` en `appointments/booking.py`:

   ```python
   check_limit(request.user.organization, "max_appointments_month",
               appointments_this_month(request.user.organization),
               "fichas por mes", "ficha por mes")
   ficha = book_appointment(organization=..., patient_id=..., practitioner_id=...,
                            branch_id=..., schedule_id=..., starts_at=...,
                            booked_by=request.user)
   ```

   `booked_by` es la recepcionista: así queda asentado quién reservó.
3. **Mostrar el importe** antes de cobrar, con el campo `fee`
   (`{"amount", "currency"}`) que ya trae la ficha. Es el mismo número que
   va a cobrar el endpoint.
4. **Cobrar** con `POST /api/payments/appointments/{id}/cash/`.
5. **Check-in sin QR.** La ficha ya está `confirmed`, así que tu
   `POST /api/appointments/checkin/` con `{"document_number": "..."}` la pasa
   a `attended` sin pedir el comprobante.

---

## 4. Lo que pasa después del cobro (no tienes que hacer nada)

- **El paciente recibe el correo de confirmación** de siempre, con el
  comprobante y el enlace para confirmar asistencia. Cuando se mergee US-28
  también le llega el push.
- **Si cancela a tiempo**, la política de devolución de US-20 deja el pago
  `refunded` con motivo `cancelacion_a_tiempo`. En efectivo nadie mueve
  dinero solo: recepción tiene que devolverlo en el mostrador. Si quieres,
  tu pantalla puede marcar las fichas con un pago `cash` devuelto para que
  recepción lo vea; no es obligatorio para US-23.
- **En los reportes de US-30** el medio de pago aparece como "Efectivo en
  ventanilla".

---

## 5. Pruebas

Toma como modelo `backend/tests/test_pago_presencial.py`, que arma una
recepcionista con `dar_rol(user, org, "...", "Recepción", [permisos])`. Para tu
mostrador, como mínimo:

- Recepción reserva a nombre de un paciente de su organización, y la ficha
  queda con `booked_by` = la recepcionista.
- Recepción no puede reservar para un paciente de otra organización.
- Un paciente no puede usar el endpoint del mostrador (`403`).
- Reservar, cobrar y hacer check-in por documento deja la ficha `attended`.
- El límite de fichas del plan se respeta también en el mostrador.

Antes de subir: `pytest` entero en verde.

---

## 6. Probar en local

Con la base local al día (`manage.py migrate` aplica `payments.0004` y
`payments.0005`), el dataset de prueba (`manage.py seed_dataset`) ya tiene
recepción con el permiso:

- Recepción: `recepcion1@sangabriel.test`
- Paciente: `paciente1@sangabriel.test`

La contraseña es la que se pasó a `seed_dataset --password`. **Pídesela a
Alexander por privado:** esas cuentas también existen en el despliegue, y el
repositorio es público.

```bash
# 1. Entrar como recepción
curl -X POST http://localhost:8000/api/accounts/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"recepcion1@sangabriel.test","password":"<la del dataset>","organization":"sangabriel"}'

# 2. Cobrar una ficha pending_payment de esa organización
curl -X POST http://localhost:8000/api/payments/appointments/<id>/cash/ \
  -H "Authorization: Bearer <access>"
```

Mientras no exista tu reserva de mostrador, la ficha `pending_payment` la
puedes crear entrando como el paciente y reservando desde la web o la app.

En Railway las migraciones corren solas al desplegar (`scripts/start.sh`).

---

## 7. Lista para cerrar

- [ ] Permiso propio para reservar en mostrador, sembrado para `receptionist`
      y `org_admin`
- [ ] Reserva a nombre del paciente con `book_appointment` y el límite del plan
- [ ] Alta del paciente con el ABM de US-10 sin salir de la pantalla
- [ ] Importe mostrado desde `fee`, nunca escrito a mano
- [ ] Cobro con `POST /payments/appointments/{id}/cash/`, con los `400`, `404`
      y `409` mostrados
- [ ] Check-in por documento, sin QR
- [ ] Textos en tuteo
- [ ] Pruebas nuevas y `pytest` entero en verde
