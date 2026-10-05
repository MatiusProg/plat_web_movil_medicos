# US-18, US-19 y US-21 — Pago, comprobante y confirmación

Historias de Alexander Osinaga (PO). Lo que pasa **después** de elegir el turno:
el paciente paga, recibe un comprobante con QR y confirma que va a asistir.

## El recorrido

```
móvil: turno → "¿para quién?" → POST /appointments/appointments/   (US-17, nace pending_payment)
móvil: "Pagar Bs X" → POST /payments/appointments/{id}/checkout/   → checkout_url
navegador: paga en Stripe Checkout (o en la página simulada)
Stripe → POST /payments/webhooks/stripe/  (firmado)  → ficha confirmed + correo
móvil: vuelve a pedir la ficha hasta verla confirmed → comprobante QR (guardado para verlo sin red)
paciente: "Confirmar asistencia" en la app o en el enlace del correo
recepción: escanea el QR → POST /appointments/checkin/  (US-22, la ficha pasa a attended)
```

## Lo que no se negocia, y dónde se cumple

| Regla | Dónde |
|---|---|
| La ficha la confirma el **webhook**, no la pantalla | `payments/services.py · confirm_payment`, único lugar que pasa una ficha a `confirmed` por un pago. El móvil sólo vuelve a pedir la ficha |
| El webhook se verifica con la **firma de Stripe** | `payments/providers.py · parse_event`. Sin `STRIPE_WEBHOOK_SECRET` no se acepta ningún evento |
| **Modo prueba**, ninguna clave en el repo | `STRIPE_SECRET_KEY` y `STRIPE_WEBHOOK_SECRET` sólo en `.env` y en Railway |
| El importe lo decide el backend | `payments/pricing.py`: el servicio de tipo *consulta* más barato de las especialidades del profesional; si no hay, `APPOINTMENT_DEFAULT_FEE` (100 BOB) |
| Lo que promete el plan se cumple | `online_payment` pasa a *aplicado* en `PLAN_RULES`: sin él, el checkout responde 403 `plan_limit` |

**Sin claves de Stripe** se usa el proveedor **simulado**: una página de pago
propia que llama a la misma `confirm_payment`. Sirve para las pruebas y la
demostración; deja de cobrar en cuanto se cargan las claves.

**El webhook no tiene usuario.** El contexto de inquilino se fija con la
organización que viaja en la metadata del evento, que es parte de lo firmado.

## La vuelta después de pagar

El pedido de pago dice de dónde viene: `{"return_to": "app"}` (lo manda el
móvil) o `"web"`. Stripe —o la página simulada— vuelve a
`/api/payments/return/?ficha=<id>&origen=<app|web>&resultado=<pagado|cancelado>`:

- **app** → la página abre `centromedico://app/appointments/<id>`
  (`MOBILE_DEEP_LINK_BASE`), que la app registra en `AndroidManifest.xml` y
  go_router resuelve a la ficha. Tiene además un botón "Volver a la
  aplicación", porque varios navegadores sólo dejan pasar a otra app con un
  toque del usuario.
- **web** → redirige a `FRONTEND_BASE_URL/mis-fichas?ficha=<id>&pago=…`.

Los destinos salen de `settings`, nunca de la URL: un `origen` o una `ficha`
que no sean válidos caen en una página genérica sin enlaces. La página de
regreso **no confirma nada**; la ficha la sigue confirmando el webhook.

## Política de devolución (US-18 → US-20)

Definida por el PO:

- Si el paciente cancela con al menos `Organization.cancellation_notice_hours`
  de anticipación (24 h por omisión), se le devuelve el **100 %**.
- Con menos anticipación **no se devuelve nada**.
- Si el pago llega cuando la ficha ya no lo espera (vencida, cancelada o pagada
  dos veces), se devuelve **en el acto**.
- Si Stripe no responde al devolver, la ficha queda cancelada igual y el error
  queda en el log para devolverlo a mano.

## El comprobante (US-19) — formato acordado con US-22

El QR contiene `MC1.<firma>`: `MC1` es la versión del formato, y la firma
(`django.core.signing`, HMAC-SHA256 con la `SECRET_KEY` y sal propia) cubre el
id de la ficha y el de la organización. Es **único por ficha**, **no se puede
fabricar** sin la clave y es **de un solo uso**, porque lo que se consume es la
ficha: el check-in la pasa a `attended` y un segundo escaneo se rechaza. El
check-in rechaza diciendo por qué: `comprobante_invalido`,
`comprobante_adulterado`, `comprobante_de_otra_organizacion`,
`comprobante_ya_utilizado`, `ficha_no_confirmada`.

El móvil guarda el comprobante la primera vez que lo ve y lo muestra **sin
conexión**.

## La confirmación de asistencia (US-21)

En la app y por correo. El correo sale al confirmarse el pago, con el código
del comprobante y un enlace firmado. El enlace **confirma con POST**, no con
GET: los clientes de correo abren los enlaces solos para revisarlos.

El desenlace queda en `Appointment.attendance_confirmed_at`. Con fecha
significa *confirmó*; en NULL, *no confirmó*. Es la etiqueta que necesita el
modelo de inasistencia del Sprint 4.

## Variables de entorno

| Variable | Para qué |
|---|---|
| `STRIPE_SECRET_KEY` | `sk_test_…`. Vacía = proveedor simulado |
| `STRIPE_WEBHOOK_SECRET` | `whsec_…` del endpoint `…/api/payments/webhooks/stripe/` |
| `PAYMENTS_PROVIDER` | `auto` (por omisión), `stripe` o `simulated` |
| `APPOINTMENT_DEFAULT_FEE` | Arancel si el catálogo no tiene precio de consulta |
| `PUBLIC_API_BASE_URL` | Dominio público de la API, para el enlace del correo |
| `FRONTEND_BASE_URL` | Dominio de la web, adonde vuelve un pago pedido desde la web |
| `MOBILE_DEEP_LINK_BASE` | `centromedico://app` por omisión; el esquema que registra la app |

Para probar el webhook real en local:
`stripe listen --forward-to localhost:8000/api/payments/webhooks/stripe/`.

## Pruebas

`tests/test_us18.py` (19), `tests/test_us19.py` (8) y `tests/test_us21.py` (8).
En el móvil, `test/appointments_payments_test.dart`.
