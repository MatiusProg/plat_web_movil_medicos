/**
 * US-17 y US-20 — Reserva, cancelación y reprogramación de fichas.
 *
 * `/appointments/appointments/` sigue el mismo contrato para web y móvil.
 * La ficha nace `pending_payment`: sólo la confirma el pago en línea (US-18,
 * ajeno a este alcance). Cancelar y reprogramar respetan la política de
 * anticipación de la organización, que decide el backend — acá sólo se
 * muestra lo que devuelve.
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
