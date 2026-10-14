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
 *
 * US-33 agrega la reserva conversacional:
 *
 *   POST /api/assistant/slots/   {"specialty", "preference"}  → turnos reales
 *   POST /api/assistant/book/    el turno que el paciente confirmó
 *
 * Los turnos salen de la disponibilidad, no del modelo, y nada se reserva sin
 * que el paciente toque *Confirmar*.
 */

import { pedir, type Contexto } from './cliente'
import type { Ficha } from './fichas'

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
  kind?: 'orientacion' | 'administrativa' | 'reserva'
  answer: string
  /** `gemini`, `plantilla` o `regla`. */
  generated_by: string
  specialty: EspecialidadSugerida | null
  alternatives: EspecialidadSugerida[]
  /** La evidencia: lo que se recuperó y sobre lo que se redactó la respuesta. */
  fragments: Fragmento[]
  /**
   * US-33: si se pueden pedir turnos y de qué especialidad. No viene en una
   * derivación de emergencia, ni de un backend anterior a US-33.
   */
  booking?: PistaDeReserva
}

export interface PistaDeReserva {
  /** El paciente puede reservar y hay una especialidad a la que apuntar. */
  available: boolean
  /** La pregunta ya pedía reservar: los turnos se piden sin preguntar. */
  booking_intent: boolean
  specialty: { id: string; name: string } | null
}

/** Un turno ofrecido. Sale de `consolidated_availability`, tal cual. */
export interface TurnoOfrecido {
  practitioner: { id: string; full_name: string }
  branch: { id: string; name: string }
  schedule: { id: string }
  start: string
  end: string
}

export interface PreferenciaEntendida {
  date_from: string
  date_to: string
  days: string[]
  part_of_day: 'manana' | 'tarde' | 'noche' | null
}

/** Lo que devuelve `slots/`, o una derivación si la preferencia era urgente. */
export type RespuestaTurnos =
  | {
      emergency: false
      kind: 'reserva'
      answer: string
      specialty: { id: string; name: string }
      preference: PreferenciaEntendida
      /** `false`: lo pedido no tenía turnos y éstos son los más próximos. */
      matched_preference: boolean
      /** Qué se soltó para encontrar turnos: otra hora el mismo día, otro
       * día en la misma franja, o lo más próximo. `null` si cumple. */
      relaxed: 'mismo_dia' | 'misma_franja' | 'proximos' | null
      offers: TurnoOfrecido[]
    }
  | { emergency: true; answer: string }

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

export function pedirTurnos(
  especialidad: string,
  preferencia: string,
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<RespuestaTurnos> {
  return pedir<RespuestaTurnos>('/assistant/slots/', {
    ...contexto,
    metodo: 'POST',
    cuerpo: { specialty: especialidad, preference: preferencia },
    senal,
  })
}

export interface ReservarDesdeAsistenteDatos {
  /** Vacío: la ficha es del titular de la cuenta. */
  patient?: string
  turno: TurnoOfrecido
}

export function reservarDesdeAsistente(
  { patient, turno }: ReservarDesdeAsistenteDatos,
  contexto: Contexto,
): Promise<Ficha> {
  return pedir<Ficha>('/assistant/book/', {
    ...contexto,
    metodo: 'POST',
    cuerpo: {
      patient: patient || null,
      practitioner: turno.practitioner.id,
      branch: turno.branch.id,
      schedule: turno.schedule.id,
      starts_at: turno.start,
    },
  })
}
