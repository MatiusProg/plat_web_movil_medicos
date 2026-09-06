/**
 * US-15 — Disponibilidad consolidada de un profesional entre sus sucursales.
 *
 * Mismo endpoint que consume la app móvil. La respuesta viene agrupada por
 * día, que es como la dibuja la interfaz.
 */

import { pedir, type Contexto } from './cliente'

export interface Espacio {
  start: string
  end: string
  branch: { id: string; name: string }
  capacity: number
  reservable: boolean
  /** `profesional_inactivo` | `sucursal_inactiva` | `null`. */
  reason: string | null
}

export interface DiaDisponible {
  date: string
  slots: Espacio[]
}

export interface Disponibilidad {
  practitioner: { id: string; full_name: string; is_active: boolean }
  range: { from: string; to: string }
  days: DiaDisponible[]
}

export function disponibilidadConsolidada(
  parametros: { practitioner: string; from: string; to: string; branch?: string },
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Disponibilidad> {
  const busqueda = new URLSearchParams({
    practitioner: parametros.practitioner,
    from: parametros.from,
    to: parametros.to,
  })
  if (parametros.branch) busqueda.set('branch', parametros.branch)
  return pedir<Disponibilidad>(
    `/scheduling/availability/?${busqueda.toString()}`,
    { ...contexto, senal },
  )
}
