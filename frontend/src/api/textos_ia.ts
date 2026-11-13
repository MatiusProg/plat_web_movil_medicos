/**
 * US-42: los textos que escribe la IA para el paciente y su validación.
 *
 * El médico los ve en su bandeja con el texto del modelo, su corrección y la
 * diferencia entre los dos. El paciente sólo recibe los aprobados (regla 14
 * del Sprint 4): eso lo garantiza el backend, no esta pantalla.
 */
import { pedir, type Contexto } from './cliente'
import { pedirPagina } from './paginacion'

export type TipoTexto = 'consultation_summary' | 'preparation' | 'history_summary'
export type EstadoTexto = 'draft' | 'approved' | 'discarded'

export interface TramoDiferencia {
  op: 'equal' | 'insert' | 'delete'
  text: string
}

export interface TextoIa {
  id: string
  kind: TipoTexto
  kind_display: string
  status: EstadoTexto
  status_display: string
  patient: string
  patient_name: string
  encounter: string | null
  encounter_date: string | null
  medical_order: string | null
  order_description: string | null
  generated_text: string
  final_text: string
  generated_by: string
  was_edited: boolean
  diff: TramoDiferencia[]
  /** US-39: lo que conviene mirar dos veces antes de aprobar. */
  warnings: string[]
  reviewed_by_name: string | null
  reviewed_at: string | null
  created_at: string
}

const base = '/ai/texts/'
const ruta = (id: string, resto = '') => `${base}${encodeURIComponent(id)}/${resto}`

export const verBandeja = (estado: EstadoTexto | 'all', pagina: number, contexto: Contexto, senal?: AbortSignal) =>
  pedirPagina<TextoIa>(base, pagina, contexto, senal, { status: estado })

export const corregirTexto = (id: string, final_text: string, contexto: Contexto) =>
  pedir<TextoIa>(ruta(id), { ...contexto, metodo: 'PATCH', cuerpo: { final_text } })

export const aprobarTexto = (id: string, final_text: string | undefined, contexto: Contexto) =>
  pedir<TextoIa>(ruta(id, 'approve/'), {
    ...contexto, metodo: 'POST', cuerpo: final_text === undefined ? {} : { final_text },
  })

export const descartarTexto = (id: string, contexto: Contexto) =>
  pedir<TextoIa>(ruta(id, 'discard/'), { ...contexto, metodo: 'POST' })

/** US-39: qué pasó con el resumen para el paciente al firmar (o al reintentar). */
export interface ResultadoResumen {
  status: 'generated' | 'exists' | 'unavailable' | 'failed'
  message: string
  text_id: string | null
}

export const reintentarResumen = (encuentroId: string, contexto: Contexto) =>
  pedir<ResultadoResumen>(`/ai/encounters/${encodeURIComponent(encuentroId)}/summary/`, {
    ...contexto, metodo: 'POST',
  })

/**
 * US-39: lo que ve el paciente. `/ai/texts/mine/` sólo devuelve textos
 * **aprobados** por su médico (regla 14): un borrador nunca llega acá.
 */
export interface ResumenAprobado {
  id: string
  encounter: string | null
  text: string
  practitioner_name: string
  approved_at: string | null
}

/** Los resúmenes aprobados de las consultas de una persona, por atención. */
export async function verResumenesAprobados(paciente: string, contexto: Contexto, senal?: AbortSignal) {
  const query = new URLSearchParams({ patient: paciente, kind: 'consultation_summary', page_size: '100' })
  const datos = await pedir<{ results: ResumenAprobado[] }>(`${base}mine/?${query}`, { ...contexto, senal })
  const porAtencion = new Map<string, ResumenAprobado>()
  // Vienen del más reciente al más viejo: si hubiera dos, queda el último aprobado.
  for (const r of datos.results ?? []) {
    if (r.encounter && r.text.trim() && !porAtencion.has(r.encounter)) porAtencion.set(r.encounter, r)
  }
  return porAtencion
}
