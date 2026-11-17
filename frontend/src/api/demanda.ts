/** US-38 — proyección de demanda de citas por especialidad y franja. */
import { pedir, type Contexto } from './cliente'

export interface FilaDemanda {
  week_start: string
  specialty_id: string
  specialty: string
  period: 'manana' | 'tarde' | 'noche'
  historical_count: number
  estimated_demand: number
  already_booked: number
  capacity: number
  expected_occupancy: number | null
  over_capacity: boolean
}
export interface ProyeccionDemanda {
  method: 'historical_weekly_average'
  history_weeks: number
  history_from: string
  history_to: string
  forecast_from: string
  forecast_to: string
  weeks: number
  historical_sample: number
  has_historical_data: boolean
  rows: FilaDemanda[]
  note: string
}
export function verProyeccionDemanda(weeks: number, branch: string, contexto: Contexto, senal?: AbortSignal) {
  const q = new URLSearchParams({ weeks: String(weeks) })
  if (branch) q.set('branch', branch)
  return pedir<ProyeccionDemanda>(`/reporting/demand/?${q}`, { ...contexto, senal })
}
