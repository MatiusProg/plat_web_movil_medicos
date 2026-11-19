/**
 * US-48 — Calificación de la atención con estrellas.
 *
 *   GET   /api/encounters/<id>/rating/      la calificación propia (o null)
 *   POST  /api/encounters/<id>/rating/      calificar por primera vez
 *   PATCH /api/encounters/<id>/rating/      cambiarla, durante 7 días
 *   GET   /api/encounters/ratings/mine/     el médico: su promedio, sin nombres
 *   GET   /api/reporting/satisfaction/      el tablero del administrador
 *
 * El historial propio (`verHistorial`) ya trae `rating` en cada atención.
 */
import { pedir, type Contexto } from './cliente'

export interface Calificacion {
  stars: number
  comment: string
  created_at: string
  updated_at: string
  editable_until: string
  editable: boolean
}

export const MAX_COMENTARIO = 500

export const calificar = (encuentroId: string, primera: boolean,
  datos: { stars: number; comment: string }, contexto: Contexto) =>
  pedir<{ rating: Calificacion }>(`/encounters/${encodeURIComponent(encuentroId)}/rating/`,
    { ...contexto, metodo: primera ? 'POST' : 'PATCH', cuerpo: datos })

export interface Distribucion { stars: number; total: number }

export interface ResumenEstrellas {
  average: number | null
  count: number
  distribution: Distribucion[]
}

export const verMisEstrellas = (contexto: Contexto, senal?: AbortSignal) =>
  pedir<ResumenEstrellas>('/encounters/ratings/mine/', { ...contexto, senal })

export interface PromedioPorNombre {
  id: string | null
  name: string
  average: number
  count: number
}

export interface Comentario {
  stars: number
  comment: string
  practitioner_name: string
  branch_name: string
  created_at: string
}

export interface Satisfaccion extends ResumenEstrellas {
  plataforma?: boolean
  range: { from: string; to: string }
  branch: string | null
  by_practitioner: PromedioPorNombre[]
  by_specialty: PromedioPorNombre[]
  by_branch: PromedioPorNombre[]
  latest_comments: Comentario[]
}

export const verSatisfaccion = (filtros: { from: string; to: string; branch?: string },
  contexto: Contexto, senal?: AbortSignal) => {
  const consulta = new URLSearchParams({ from: filtros.from, to: filtros.to })
  if (filtros.branch) consulta.set('branch', filtros.branch)
  return pedir<Satisfaccion>(`/reporting/satisfaction/?${consulta}`, { ...contexto, senal })
}

/** «4,3» con coma decimal, o «—» sin calificaciones. */
export const promedio = (valor: number | null) =>
  valor === null ? '—' : valor.toLocaleString('es-BO', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
