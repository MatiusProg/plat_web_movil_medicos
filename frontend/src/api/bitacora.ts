/**
 * US-06 — Bitácora de auditoría.
 *
 * Sólo lectura, y no por comodidad: el backend no expone verbos de escritura
 * sobre `/api/audit/logs/` ni siquiera para el administrador. Si algún día
 * aparece acá una función que hace POST, es que alguien abrió algo que tenía
 * que estar cerrado.
 *
 * Los nombres de los campos van en inglés porque son los que devuelve el
 * backend.
 */

import { pedir, type Contexto } from './cliente'

export interface ActorBitacora {
  id: string
  email: string
  full_name: string
}

export interface AsientoBitacora {
  id: number
  /** `null` cuando la acción no la hizo una persona identificada. */
  actor: ActorBitacora | null
  action: string
  /** Texto legible del `action`, resuelto por el backend. */
  action_label: string
  entity: string
  entity_id: string
  detail: Record<string, unknown>
  ip_address: string | null
  user_agent: string
  occurred_at: string
}

export interface AccionBitacora {
  code: string
  label: string
}

export interface FiltrosBitacora {
  actor?: string
  action?: string
  date_from?: string
  date_to?: string
  page?: number
}

interface Pagina<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

function consulta(filtros: FiltrosBitacora): string {
  const partes = new URLSearchParams()
  if (filtros.actor) partes.set('actor', filtros.actor)
  if (filtros.action) partes.set('action', filtros.action)
  if (filtros.date_from) partes.set('date_from', filtros.date_from)
  if (filtros.date_to) partes.set('date_to', filtros.date_to)
  if (filtros.page && filtros.page > 1) partes.set('page', String(filtros.page))
  const cadena = partes.toString()
  return cadena ? `?${cadena}` : ''
}

export function listarBitacora(
  filtros: FiltrosBitacora,
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Pagina<AsientoBitacora>> {
  return pedir<Pagina<AsientoBitacora>>(`/audit/logs/${consulta(filtros)}`, {
    ...contexto,
    senal,
  })
}

/**
 * Las acciones que esta organización tiene registradas.
 *
 * Devuelve las que existen y no el catálogo completo: un desplegable con
 * quince opciones que no traen ninguna fila no ayuda a auditar.
 */
export function listarAccionesBitacora(
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<AccionBitacora[]> {
  return pedir<AccionBitacora[]>('/audit/logs/actions/', { ...contexto, senal })
}
