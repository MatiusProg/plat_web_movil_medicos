/**
 * US-17 a US-21 — Reserva, pago, comprobante, confirmación de asistencia,
 * cancelación y reprogramación de fichas.
 *
 * `/appointments/appointments/` sigue el mismo contrato para web y móvil.
 * La ficha nace `pending_payment` y **sólo la confirma el webhook de Stripe**
 * (US-18): la web abre el checkout y después vuelve a pedir la ficha, nunca
 * la da por pagada. Importes, estados y la política de anticipación los
 * decide el backend — acá sólo se muestra lo que devuelve.
 */

import { pedir, type Contexto } from './cliente'

export type EstadoFicha =
  | 'pending_payment'
  | 'confirmed'
  | 'attended'
  | 'cancelled'
  | 'rescheduled'
  | 'expired'
  | 'no_show'

export interface Ficha {
  id: string
  patient: string
  patient_name: string
  practitioner: string
  practitioner_name: string
  branch: string
  branch_name: string
  starts_at: string
  ends_at: string
  status: EstadoFicha
  expires_at: string | null
  cancelled_at: string | null
  cancellation_reason: string
  refund_eligible: boolean | null
  rescheduled_from: string | null
  checked_in_at: string | null
  // US-21: con fecha = el paciente confirmó que va a asistir.
  attendance_confirmed_at: string | null
  // US-18: lo que cuesta y en qué quedó el último intento de pago.
  fee: { amount: string; currency: string }
  payment_status: 'pending' | 'succeeded' | 'failed' | 'expired' | 'refunded' | null
  created_at: string
  updated_at: string
}

export interface ReservarFichaDatos {
  patient: string
  practitioner: string
  branch: string
  schedule: string
  startsAt: string
}

export interface ReprogramarFichaDatos {
  branch: string
  schedule: string
  startsAt: string
}

export function reservarFicha(
  datos: ReservarFichaDatos,
  contexto: Contexto,
): Promise<Ficha> {
  return pedir<Ficha>('/appointments/appointments/', {
    ...contexto,
    metodo: 'POST',
    cuerpo: {
      patient: datos.patient,
      practitioner: datos.practitioner,
      branch: datos.branch,
      schedule: datos.schedule,
      starts_at: datos.startsAt,
    },
  })
}

export function misFichas(
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Ficha[]> {
  return pedir<Ficha[]>('/appointments/appointments/', { ...contexto, senal })
}

export function cancelarFicha(id: string, contexto: Contexto): Promise<Ficha> {
  return pedir<Ficha>(`/appointments/appointments/${id}/cancel/`, {
    ...contexto,
    metodo: 'POST',
  })
}

export function reprogramarFicha(
  id: string,
  datos: ReprogramarFichaDatos,
  contexto: Contexto,
): Promise<Ficha> {
  return pedir<Ficha>(`/appointments/appointments/${id}/reschedule/`, {
    ...contexto,
    metodo: 'POST',
    cuerpo: {
      branch: datos.branch,
      schedule: datos.schedule,
      starts_at: datos.startsAt,
    },
  })
}

// =========================================================
// US-18 — PAGO EN LÍNEA · US-19 — COMPROBANTE · US-21 — ASISTENCIA
// =========================================================

export interface SesionDePago {
  payment_id: string
  provider: 'stripe' | 'simulated'
  checkout_url: string
  amount: string
  currency: string
  status: string
}

/** Abre el cobro. Stripe vuelve después a "Mis fichas" (`return_to: web`). */
export function iniciarPago(id: string, contexto: Contexto): Promise<SesionDePago> {
  return pedir<SesionDePago>(`/payments/appointments/${id}/checkout/`, {
    ...contexto,
    metodo: 'POST',
    cuerpo: { return_to: 'web' },
  })
}

export interface Comprobante {
  appointment_id: string
  // Lo que va dentro del QR: `MC1.<firma>`. Lo verifica el check-in (US-22).
  code: string
  issued_at: string
  organization_name: string
  patient_name: string
  document_number: string
  practitioner_name: string
  branch_name: string
  branch_address: string
  starts_at: string
  ends_at: string
  status: EstadoFicha
}

export function comprobante(id: string, contexto: Contexto): Promise<Comprobante> {
  return pedir<Comprobante>(`/appointments/appointments/${id}/receipt/`, contexto)
}

export function confirmarAsistencia(id: string, contexto: Contexto): Promise<Ficha> {
  return pedir<Ficha>(`/appointments/appointments/${id}/confirm-attendance/`, {
    ...contexto,
    metodo: 'POST',
  })
}

// =========================================================
// US-22 — CHECK-IN EN RECEPCIÓN
// =========================================================

export interface CheckInDatos {
  qr_code?: string
  document_number?: string
}

export interface CheckInResultado {
  id: string
  status: 'attended'
  checked_in_at: string

  patient: {
    id: string
    name: string
    document_number: string
  }

  branch: {
    id: string
    name: string
  }

  practitioner: {
    id: string
    name: string
  }

  starts_at: string
  ends_at: string
}

export function realizarCheckIn(
    datos: CheckInDatos,
    contexto: Contexto,
): Promise<CheckInResultado> {
  return pedir<CheckInResultado>(
      '/appointments/checkin/',
      {
        ...contexto,
        metodo: 'POST',
        cuerpo: datos,
      },
  )
}