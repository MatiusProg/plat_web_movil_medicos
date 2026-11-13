/**
 * US-47: el chat entre el paciente atendido y el médico de esa atención.
 *
 * Una conversación por atención firmada. Quién es quién lo decide el backend
 * (`side`): la misma pantalla sirve al paciente y al médico. No hay tiempo
 * real: la pantalla abierta vuelve a pedir la conversación cada 10 segundos.
 */
import { pedir, type Contexto } from './cliente'

export type Lado = 'patient' | 'practitioner'

export interface MensajeChat {
  id: string
  side: Lado
  author_name: string
  body: string
  created_at: string
  mine: boolean
  flagged_emergency: boolean
}

export interface Conversacion {
  encounter: string
  side: Lado
  patient_name: string
  practitioner_name: string
  encounter_date: string | null
  signed_at: string | null
  closes_at: string | null
  can_write: boolean
  closed_reason: 'closed' | 'expired' | null
  window_days: number
  notice: string
  prescription: { medication: string; dose: string; frequency: string; duration: string; instructions: string }[]
  orders: { kind: string; kind_display: string; description: string }[]
  messages: MensajeChat[]
}

export interface Enviado {
  message: MensajeChat
  emergency: { message: string } | null
}

export interface FilaBandejaChat {
  encounter: string
  patient_name: string
  encounter_date: string | null
  last_message_at: string | null
  unread: number
  unread_emergency: number
  can_write: boolean
}

const ruta = (id: string, resto = '') => `/messaging/encounters/${encodeURIComponent(id)}/chat/${resto}`

export const verConversacion = (encuentroId: string, contexto: Contexto, senal?: AbortSignal) =>
  pedir<Conversacion>(ruta(encuentroId), { ...contexto, senal })

export const escribirMensaje = (encuentroId: string, body: string, contexto: Contexto) =>
  pedir<Enviado>(ruta(encuentroId, 'messages/'), { ...contexto, metodo: 'POST', cuerpo: { body } })

export const cerrarConversacion = (encuentroId: string, contexto: Contexto) =>
  pedir<Conversacion>(ruta(encuentroId, 'close/'), { ...contexto, metodo: 'POST' })

export const verBandejaChat = (contexto: Contexto, senal?: AbortSignal) =>
  pedir<{ results: FilaBandejaChat[]; unread_total: number }>('/messaging/inbox/', { ...contexto, senal })
