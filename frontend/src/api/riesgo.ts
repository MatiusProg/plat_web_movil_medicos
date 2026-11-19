/**
 * US-35 — Riesgo de inasistencia de las fichas futuras.
 *
 *   GET /api/noshow/appointments/?from=&to=&branch=&level=&page=&page_size=
 *   GET /api/noshow/model/
 *
 * El nivel y la probabilidad los calcula un modelo en el backend; acá sólo se
 * muestran. Sin `from`/`to` el backend toma de hoy a hoy + 14 días. La función
 * es del plan Premium: si el plan del centro no la incluye, ambos endpoints
 * responden 403 con `code: "plan_limit"` (ver `esErrorDePlan`).
 */
import { pedir, type Contexto } from './cliente'
import { pedirPagina, type Pagina } from './paginacion'
import { ErrorApi } from './tipos'

export type NivelRiesgo = 'low' | 'medium' | 'high'

/** Cómo se lee el nivel en pantalla; el backend manda el código en inglés. */
export const ETIQUETA_NIVEL: Record<NivelRiesgo, string> = {
  low: 'Riesgo bajo',
  medium: 'Riesgo medio',
  high: 'Riesgo alto',
}

export interface FactorRiesgo {
  key: string
  /** Ya viene en español. */
  label: string
  /** `up` empuja la probabilidad hacia arriba; `down`, hacia abajo. */
  direction: 'up' | 'down'
}

export interface FichaEnRiesgo {
  appointment_id: string
  patient_name: string
  practitioner_name: string
  branch_name: string
  /** ISO 8601. */
  starts_at: string
  status: 'confirmed' | 'pending_payment'
  level: NivelRiesgo
  /** Fracción entre 0 y 1. */
  probability: number
  /** Hasta tres. */
  factors: FactorRiesgo[]
  computed_at: string
}

export interface MetricasModelo {
  auc: number | null
  brier: number | null
  brier_baseline: number | null
  accuracy_baseline: number | null
  recall_high: number | null
  precision_high: number | null
}

export interface ModeloVigente {
  version: number
  status: 'active'
  trained_at: string
  n_train: number
  n_test: number
  base_rate: number
  beats_baseline: boolean
  metrics: MetricasModelo
  cutoffs: { medium: number; high: number }
}

export interface ModeloRechazado {
  version: number
  trained_at: string
  metrics: MetricasModelo
}

export type MotivoSinModelo = 'sin_datos' | 'sin_modelo' | 'no_supera_base'

export interface EstadoModelo {
  model: ModeloVigente | null
  /** El último modelo que no superó la línea base «siempre asiste». */
  rejected: ModeloRechazado | null
  reason: MotivoSinModelo | null
  message: string | null
}

export interface FiltrosRiesgo {
  from?: string
  to?: string
  branch?: string
  level?: NivelRiesgo
  page?: number
}

export const listarRiesgo = (
  filtros: FiltrosRiesgo,
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Pagina<FichaEnRiesgo>> =>
  pedirPagina<FichaEnRiesgo>('/noshow/appointments/', filtros.page ?? 1, contexto, senal, {
    from: filtros.from,
    to: filtros.to,
    branch: filtros.branch,
    level: filtros.level,
  })

export const verModeloRiesgo = (contexto: Contexto, senal?: AbortSignal) =>
  pedir<EstadoModelo>('/noshow/model/', { ...contexto, senal })

/** El 403 de «tu plan no incluye esta función»; el mensaje lo pone el backend. */
export const esErrorDePlan = (error: unknown): error is ErrorApi =>
  error instanceof ErrorApi && error.estado === 403 && (error.codigo as string) === 'plan_limit'

/** US-38: auditoría de versiones, restringida al mismo permiso del riesgo. */
export interface VersionRiesgo {
  version: number
  status: 'active' | 'candidate' | 'rejected' | 'retired'
  trained_at: string
  n_train: number
  n_test: number
  beats_baseline: boolean
  auc: number | null
  brier: number | null
  comparison: {
    holdout_n?: number
    incumbent_version?: number
    incumbent_brier?: number
    candidate_brier?: number
    improvement?: number
    reason?: string
  } | null
}

export const listarVersionesRiesgo = (contexto: Contexto, senal?: AbortSignal) =>
  pedir<{ results: VersionRiesgo[] }>('/noshow/versions/', { ...contexto, senal })
