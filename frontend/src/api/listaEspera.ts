/**
 * US-52 — Lista de espera con aviso de cupo liberado.
 *
 *   GET    /api/appointments/waitlist/          las entradas vivas del paciente
 *   POST   /api/appointments/waitlist/          anotarse
 *   DELETE /api/appointments/waitlist/<id>/     salir de la lista
 *   GET    /api/appointments/waitlist/summary/  resumen para administración
 *
 * Cuando alguien cancela, el backend le guarda el turno 15 minutos al primero
 * de la fila: la entrada pasa a `offered` y el turno aparece como una ficha
 * `pending_payment` normal (con `expires_at`) en «Mis fichas». La función es
 * de los planes Pro y Premium: sin ella el listado llega con `enabled: false`
 * y el resumen responde 403 `plan_limit`.
 */

import { pedir, type Contexto } from './cliente'

export type EstadoEntradaEspera = 'waiting' | 'offered' | 'booked' | 'expired' | 'cancelled'

export interface EntradaEspera {
  id: string
  patient: string
  patient_name: string
  practitioner: string | null
  practitioner_name: string | null
  specialty: string | null
  specialty_name: string | null
  branch: string | null
  branch_name: string | null
  /** `YYYY-MM-DD`. */
  date_from: string
  date_to: string
  status: EstadoEntradaEspera
  /** Lugar en la fila (1 = primero). `null` si ya se le ofreció un turno. */
  position: number | null
  /** La ficha `pending_payment` que se le guardó, si ya se le ofreció. */
  offered_appointment: string | null
  offered_expires_at: string | null
  created_at: string
}

export interface ListaDeEspera {
  /** `false` si el plan no incluye la función: no hay que mostrar la sección. */
  enabled: boolean
  results: EntradaEspera[]
}

export interface AnotarseDatos {
  patient: string
  /** Profesional **o** especialidad, no ambos. */
  practitioner?: string
  specialty?: string
  branch?: string
  dateFrom: string
  dateTo: string
}

export interface ResumenListaDeEspera {
  range: { from: string; to: string }
  waitlist: {
    enrolled: number
    booked: number
    waiting: number
    offered: number
    expired: number
    cancelled: number
    by_practitioner: { practitioner: string; name: string; enrolled: number; booked: number }[]
    by_specialty: { specialty: string; name: string; enrolled: number; booked: number }[]
  }
  recovery: {
    cancelled: number
    recovered: number
    /** Fracción entre 0 y 1, o `null` si no hubo cancelaciones. */
    rate: number | null
  }
}

export function miListaDeEspera(
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<ListaDeEspera> {
  return pedir<ListaDeEspera>('/appointments/waitlist/', { ...contexto, senal })
}

export function anotarseEnListaDeEspera(
  datos: AnotarseDatos,
  contexto: Contexto,
): Promise<EntradaEspera> {
  return pedir<EntradaEspera>('/appointments/waitlist/', {
    ...contexto,
    metodo: 'POST',
    cuerpo: {
      patient: datos.patient,
      practitioner: datos.practitioner,
      specialty: datos.specialty,
      branch: datos.branch,
      date_from: datos.dateFrom,
      date_to: datos.dateTo,
    },
  })
}

export function salirDeListaDeEspera(id: string, contexto: Contexto): Promise<void> {
  return pedir<void>(`/appointments/waitlist/${id}/`, { ...contexto, metodo: 'DELETE' })
}

export function resumenListaDeEspera(
  filtros: { from?: string; to?: string },
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<ResumenListaDeEspera> {
  const consulta = new URLSearchParams()
  if (filtros.from) consulta.set('from', filtros.from)
  if (filtros.to) consulta.set('to', filtros.to)
  const sufijo = consulta.toString() ? `?${consulta}` : ''
  return pedir<ResumenListaDeEspera>(`/appointments/waitlist/summary/${sufijo}`, {
    ...contexto,
    senal,
  })
}
