/** US-51. La preconsulta no modifica pagos ni datos clínicos firmados. */
import { pedir, type Contexto } from './cliente'

export interface Preconsulta {
  reason: string
  questions: string
  updated_at: string | null
}
export function leerPreconsulta(id: string, contexto: Contexto): Promise<Preconsulta> {
  return pedir<Preconsulta>(`/appointments/appointments/${id}/preconsultation/`, contexto)
}
export function guardarPreconsulta(id: string, datos: Pick<Preconsulta, 'reason' | 'questions'>, contexto: Contexto): Promise<Preconsulta> {
  return pedir<Preconsulta>(`/appointments/appointments/${id}/preconsultation/`, {
    ...contexto, metodo: 'PUT', cuerpo: datos,
  })
}
