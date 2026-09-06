/**
 * Catálogo del centro médico: sucursales, especialidades y profesionales.
 *
 * Sólo lectura: el ABM de sucursales (US-11) y de especialidades y
 * profesionales (US-12) es de otra pantalla. Acá vive lo que consumen los
 * selectores de la agenda (US-13), la disponibilidad (US-15) y la búsqueda
 * (US-16).
 */

import { pedir, type Contexto } from './cliente'

export interface Sucursal {
  id: string
  name: string
  address: string
  phone: string
  timezone: string
  is_active: boolean
}

export interface Especialidad {
  id: string
  name: string
  description: string
  is_active: boolean
}

export interface Referencia {
  id: string
  name: string
}

export interface ProfesionalTarjeta {
  id: string
  full_name: string
  specialties: Referencia[]
  branches: Referencia[]
  /** ISO 8601, del endpoint de US-15. `null` si no hay nada en el horizonte. */
  next_available_slot: string | null
}

interface Pagina<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export function listarSucursales(
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Sucursal[]> {
  return pedir<Sucursal[]>('/catalog/branches/', { ...contexto, senal })
}

export function listarEspecialidades(
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Especialidad[]> {
  return pedir<Especialidad[]>('/catalog/specialties/', { ...contexto, senal })
}

export interface FiltrosBusqueda {
  q?: string
  specialty?: string
  branch?: string
  page?: number
}

export function buscarProfesionales(
  filtros: FiltrosBusqueda,
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Pagina<ProfesionalTarjeta>> {
  const parametros = new URLSearchParams()
  if (filtros.q) parametros.set('q', filtros.q)
  if (filtros.specialty) parametros.set('specialty', filtros.specialty)
  if (filtros.branch) parametros.set('branch', filtros.branch)
  if (filtros.page) parametros.set('page', String(filtros.page))
  const sufijo = parametros.toString() ? `?${parametros.toString()}` : ''
  return pedir<Pagina<ProfesionalTarjeta>>(
    `/catalog/professionals/${sufijo}`,
    { ...contexto, senal },
  )
}
