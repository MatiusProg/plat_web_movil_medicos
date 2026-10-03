/** US-24: la agenda del profesional, el encuentro clínico y sus enmiendas. */
import { pedir, type Contexto } from './cliente'

export type Seccion = 'reason' | 'evolution' | 'diagnosis' | 'indications' | 'treatment'

/** En el orden en que se escriben. */
export const SECCIONES: { campo: Seccion; etiqueta: string; ayuda: string }[] = [
  { campo: 'reason', etiqueta: 'Motivo de consulta', ayuda: 'Por qué vino, en sus palabras.' },
  { campo: 'evolution', etiqueta: 'Evolución', ayuda: 'Examen, hallazgos y cómo viene el cuadro.' },
  { campo: 'diagnosis', etiqueta: 'Diagnóstico', ayuda: 'Presuntivo o definitivo.' },
  { campo: 'indications', etiqueta: 'Indicaciones', ayuda: 'Reposo, estudios, controles.' },
  { campo: 'treatment', etiqueta: 'Tratamiento', ayuda: 'Medicación con dosis y frecuencia.' },
]

/** Lo mínimo para firmar; lo mismo que exige el backend. */
export const OBLIGATORIAS_PARA_FIRMAR: Seccion[] = ['reason', 'diagnosis']

export interface PacienteResumen {
  id: string
  full_name: string
  document_number: string | null
  birth_date: string | null
  sex: string | null
}

export interface FichaAgenda {
  id: string
  starts_at: string
  ends_at: string
  status: string
  status_display: string
  branch_name: string
  patient: PacienteResumen
  encounter: { id: string; status: 'draft' | 'signed'; status_display: string } | null
}

export interface Agenda {
  date: string
  practitioner: string
  appointments: FichaAgenda[]
}

export interface Enmienda {
  id: string
  section: Seccion
  section_display: string
  text: string
  author_name: string
  created_at: string
}

export interface Encuentro extends Record<Seccion, string> {
  id: string
  status: 'draft' | 'signed'
  status_display: string
  appointment: string
  appointment_starts_at: string
  patient: PacienteResumen
  practitioner_name: string
  branch_name: string
  signed_at: string | null
  signed_by_name: string | null
  amendments: Enmienda[]
  created_at: string
  updated_at: string
}

export interface Antecedente {
  id: string
  kind_label: string
  description: string
  severity: string | null
  severity_label: string | null
}

export interface Antecedentes {
  allergies: Antecedente[]
  conditions: Antecedente[]
  medications: Antecedente[]
  self_reported: boolean
}

const base = '/encounters/'

export const verAgenda = (fecha: string, contexto: Contexto, senal?: AbortSignal) =>
  pedir<Agenda>(`${base}agenda/?date=${encodeURIComponent(fecha)}`, { ...contexto, senal })

export const abrirAtencion = (fichaId: string, contexto: Contexto) =>
  pedir<Encuentro>(base, { ...contexto, metodo: 'POST', cuerpo: { appointment: fichaId } })

export const verEncuentro = (id: string, contexto: Contexto, senal?: AbortSignal) =>
  pedir<Encuentro>(`${base}${encodeURIComponent(id)}/`, { ...contexto, senal })

export const guardarBorrador = (id: string, datos: Partial<Record<Seccion, string>>, contexto: Contexto) =>
  pedir<Encuentro>(`${base}${encodeURIComponent(id)}/`, { ...contexto, metodo: 'PATCH', cuerpo: datos })

export const firmarEncuentro = (id: string, contexto: Contexto) =>
  pedir<Encuentro>(`${base}${encodeURIComponent(id)}/sign/`, { ...contexto, metodo: 'POST' })

export const agregarEnmienda = (id: string, section: Seccion, text: string, contexto: Contexto) =>
  pedir<Enmienda>(`${base}${encodeURIComponent(id)}/amendments/`, {
    ...contexto, metodo: 'POST', cuerpo: { section, text },
  })

/** Los antecedentes declarados del paciente (US-08). El backend lo audita. */
export const verAntecedentes = (pacienteId: string, contexto: Contexto, senal?: AbortSignal) =>
  pedir<Antecedentes>(`/patients/history/highlights/?patient=${encodeURIComponent(pacienteId)}`, {
    ...contexto, senal,
  })

/** US-25: el historial longitudinal del paciente, todas las sucursales. */
export interface Historial {
  patient: PacienteResumen
  scope: 'own' | 'professional'
  branches: { name: string; encounters: number }[]
  encounters: Encuentro[]
}

export const verHistorial = (pacienteId: string, contexto: Contexto, senal?: AbortSignal) =>
  pedir<Historial>(`${base}history/${encodeURIComponent(pacienteId)}/`, { ...contexto, senal })
