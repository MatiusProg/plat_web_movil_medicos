/**
 * US-29 — El panel de KPIs.
 *
 *   GET /api/reporting/kpis/?from=&to=&branch=
 *
 * Las definiciones de cada indicador están en
 * `docs/sprints/sprint-3/us-29-indicadores.md`. Las tasas llegan como
 * fracciones entre 0 y 1, o `null` cuando no hay base para calcularlas.
 */
import { pedir, type Contexto } from './cliente'

export interface TotalPorNombre {
  /** `null` para «Sin especialidad». */
  id: string | null
  name: string
  total: number
}

export interface IngresoMoneda {
  currency: string
  /** Decimal como texto, p. ej. `"150.50"`. */
  total: string
  payments: number
}

export interface IngresoSucursal {
  id: string
  name: string
  currency: string
  total: string
}

export interface Kpis {
  plataforma?: boolean
  range: { from: string; to: string; timezone: string }
  branch: string | null
  occupancy: { offered: number; booked: number; rate: number | null }
  no_show: { expected: number; missed: number; rate: number | null }
  demand: { total: number; by_branch: TotalPorNombre[]; by_specialty: TotalPorNombre[] }
  revenue: { by_currency: IngresoMoneda[]; by_branch: IngresoSucursal[] }
}

export interface FiltrosKpis {
  from: string
  to: string
  branch?: string
}

export const verKpis = (filtros: FiltrosKpis, contexto: Contexto, senal?: AbortSignal) => {
  const consulta = new URLSearchParams({ from: filtros.from, to: filtros.to })
  if (filtros.branch) consulta.set('branch', filtros.branch)
  return pedir<Kpis>(`/reporting/kpis/?${consulta}`, { ...contexto, senal })
}
