/**
 * US-31, US-32 y US-34 — El asistente de orientación.
 *
 *   POST /api/assistant/suggest/   {"question": "…"}
 *
 * Es el mismo endpoint que usa el móvil (`mobile/lib/features/assistant/`):
 * la web no tiene un camino propio, y por eso tampoco una barrera de
 * emergencia propia. Lo que decide si algo es una urgencia es el backend
 * —las reglas de `triage.py` y la marca del modelo—; la pantalla sólo obedece
 * `emergency`.
 */

import { pedir, type Contexto } from './cliente'

export interface Fragmento {
  id: string
  text: string
  /** `specialty`, `branch`, `service`, `policy`, `medical_reference`, … */
  source_type: string
  source_id: string
  /** De dónde salió: el nombre de la especialidad o de la sucursal. */
  source_name: string
  similarity: number
}

export interface EspecialidadSugerida {
  id: string
  name: string
  similarity: number
}

export interface RespuestaAsistente {
  /** US-34: la descripción es compatible con una urgencia. */
  emergency: boolean
  /**
   * US-32: `orientacion` sugiere especialidad; `administrativa` contesta
   * horarios, sedes, precios o preparación, sin especialidad. No viene en una
   * derivación de emergencia.
   */
  kind?: 'orientacion' | 'administrativa'
  answer: string
  /** `gemini`, `plantilla` o `regla`. */
  generated_by: string
  specialty: EspecialidadSugerida | null
  alternatives: EspecialidadSugerida[]
  /** La evidencia: lo que se recuperó y sobre lo que se redactó la respuesta. */
  fragments: Fragmento[]
}

export function consultarAsistente(
  pregunta: string,
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<RespuestaAsistente> {
  return pedir<RespuestaAsistente>('/assistant/suggest/', {
    ...contexto,
    metodo: 'POST',
    // `question`, no `message`: así se llama en `assistant/serializers.py`.
    cuerpo: { question: pregunta },
    senal,
  })
}
