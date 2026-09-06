/**
 * US-13 (agendas médicas) y US-14 (bloqueos).
 *
 * Los nombres de los campos van en inglés porque son los que devuelve el
 * backend.
 */

import { pedir, type Contexto } from './cliente'

// --------------------------------------------------------------------------
//  US-13 — Agendas
// --------------------------------------------------------------------------

export interface AgendaRegla {
  id: string
  practitioner: string
  practitioner_name: string
  branch: string
  branch_name: string
  /** 0 = lunes … 6 = domingo. */
  weekday: number
  start_time: string
  end_time: string
  slot_minutes: number
  capacity: number
  valid_from: string
  valid_until: string | null
  is_active: boolean
}

export interface AgendaNueva {
  practitioner: string
  branch: string
  weekday: number
  start_time: string
  end_time: string
  slot_minutes: number
  capacity: number
  valid_from: string
  valid_until?: string | null
}

export interface EspacioCalendario {
  start: string
  end: string
  branch: { id: string; name: string }
  capacity: number
}

export interface DiaCalendario {
  date: string
  slots: EspacioCalendario[]
}

interface Pagina<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export function listarAgendas(
  filtros: { practitioner?: string; branch?: string },
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Pagina<AgendaRegla>> {
  const parametros = new URLSearchParams()
  if (filtros.practitioner) parametros.set('practitioner', filtros.practitioner)
  if (filtros.branch) parametros.set('branch', filtros.branch)
  const sufijo = parametros.toString() ? `?${parametros.toString()}` : ''
  return pedir<Pagina<AgendaRegla>>(`/scheduling/schedules/${sufijo}`, {
    ...contexto,
    senal,
  })
}

export function crearAgenda(
  datos: AgendaNueva,
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<AgendaRegla> {
  return pedir<AgendaRegla>('/scheduling/schedules/', {
    ...contexto,
    metodo: 'POST',
    cuerpo: datos,
    senal,
  })
}

export function editarAgenda(
  id: string,
  datos: Partial<AgendaNueva> & { is_active?: boolean },
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<AgendaRegla> {
  return pedir<AgendaRegla>(`/scheduling/schedules/${id}/`, {
    ...contexto,
    metodo: 'PATCH',
    cuerpo: datos,
    senal,
  })
}

export function bajaAgenda(
  id: string,
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<void> {
  return pedir<void>(`/scheduling/schedules/${id}/`, {
    ...contexto,
    metodo: 'DELETE',
    senal,
  })
}

export function calendarioSemanal(
  practitioner: string,
  semana: string,
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<{ week: string; days: DiaCalendario[] }> {
  const parametros = new URLSearchParams({ practitioner, week: semana })
  return pedir(`/scheduling/schedules/calendar/?${parametros.toString()}`, {
    ...contexto,
    senal,
  })
}

// --------------------------------------------------------------------------
//  US-14 — Bloqueos
// --------------------------------------------------------------------------

export type MotivoBloqueo = 'vacation' | 'holiday' | 'leave' | 'absence'

export interface Bloqueo {
  id: string
  practitioner: string | null
  practitioner_name: string | null
  branch: string | null
  branch_name: string | null
  starts_at: string
  ends_at: string
  reason: MotivoBloqueo
  note: string
  is_active: boolean
}

export interface BloqueoNuevo {
  /** Sin `practitioner` es un feriado de toda la organización. */
  practitioner?: string | null
  branch?: string | null
  starts_at: string
  ends_at: string
  reason: MotivoBloqueo
  note?: string
}

export function listarBloqueos(
  filtros: { practitioner?: string; is_active?: boolean },
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Pagina<Bloqueo>> {
  const parametros = new URLSearchParams()
  if (filtros.practitioner) parametros.set('practitioner', filtros.practitioner)
  if (filtros.is_active !== undefined) {
    parametros.set('is_active', filtros.is_active ? 'true' : 'false')
  }
  const sufijo = parametros.toString() ? `?${parametros.toString()}` : ''
  return pedir<Pagina<Bloqueo>>(`/scheduling/blocks/${sufijo}`, {
    ...contexto,
    senal,
  })
}

export function crearBloqueo(
  datos: BloqueoNuevo,
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Bloqueo> {
  return pedir<Bloqueo>('/scheduling/blocks/', {
    ...contexto,
    metodo: 'POST',
    cuerpo: datos,
    senal,
  })
}

export function fichasAfectadas(
  id: string,
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<{ count: number; appointments: unknown[] }> {
  return pedir(`/scheduling/blocks/${id}/affected/`, { ...contexto, senal })
}

export function levantarBloqueo(
  id: string,
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Bloqueo> {
  return pedir<Bloqueo>(`/scheduling/blocks/${id}/lift/`, {
    ...contexto,
    metodo: 'POST',
    senal,
  })
}
