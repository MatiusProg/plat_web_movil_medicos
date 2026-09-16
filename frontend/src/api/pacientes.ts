/**
 * US-07 (h) — El selector de *"¿para quién es esta ficha?"*.
 *
 * El endpoint ya está publicado y lo consume la app móvil desde US-08; acá
 * sólo se agrega la función mínima para poblar el mismo selector en la
 * reserva web (US-17). El titular viene siempre primero.
 */

import { pedir, type Contexto } from './cliente'

export interface OpcionDePaciente {
  id: string
  full_name: string
  relationship: string
  relationship_label: string
  is_self: boolean
  birth_date: string | null
}

export function listarOpcionesDePaciente(
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<OpcionDePaciente[]> {
  return pedir<OpcionDePaciente[]>(
    '/patients/dependents/patient-options/',
    { ...contexto, senal },
  )
}
