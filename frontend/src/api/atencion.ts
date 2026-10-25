/** US-24: la agenda del profesional, el encuentro clínico y sus enmiendas. */
import { pedir, type Contexto } from './cliente'
import { ErrorApi, type CodigoError } from './tipos'

const BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000/api'

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

/** US-26: lo enmendable de una atención firmada incluye la receta y las órdenes. */
export type SeccionEnmendable = Seccion | 'prescription' | 'orders'

export const ENMENDABLES: { campo: SeccionEnmendable; etiqueta: string }[] = [
  ...SECCIONES.map(({ campo, etiqueta }) => ({ campo, etiqueta })),
  { campo: 'prescription', etiqueta: 'Receta' },
  { campo: 'orders', etiqueta: 'Órdenes' },
]

/** US-26: un medicamento de la receta. */
export interface Medicamento {
  id: string
  medication: string
  dose: string
  frequency: string
  duration: string
  instructions: string
  created_at: string
}

export type DatosMedicamento = Omit<Medicamento, 'id' | 'created_at'>

export type TipoOrden = 'laboratory' | 'imaging' | 'other'

export const TIPOS_DE_ORDEN: { valor: TipoOrden; etiqueta: string }[] = [
  { valor: 'laboratory', etiqueta: 'Laboratorio' },
  { valor: 'imaging', etiqueta: 'Imagenología' },
  { valor: 'other', etiqueta: 'Otro estudio' },
]

/** US-26: una orden de laboratorio o de estudio. */
export interface Orden {
  id: string
  kind: TipoOrden
  kind_display: string
  description: string
  notes: string
  created_at: string
}

export type DatosOrden = Pick<Orden, 'kind' | 'description' | 'notes'>

export interface Enmienda {
  id: string
  section: SeccionEnmendable
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
  prescription_items: Medicamento[]
  orders: Orden[]
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

export const agregarEnmienda = (id: string, section: SeccionEnmendable, text: string, contexto: Contexto) =>
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

// --------------------------------------------------------------------------
//  US-26 — Receta y órdenes, mientras la atención es borrador
// --------------------------------------------------------------------------
// Cada operación devuelve la atención entera: la pantalla se redibuja con lo
// que dice el servidor.

const enc = (id: string) => `${base}${encodeURIComponent(id)}`

export const agregarMedicamento = (id: string, datos: DatosMedicamento, contexto: Contexto) =>
  pedir<Encuentro>(`${enc(id)}/prescription/`, { ...contexto, metodo: 'POST', cuerpo: datos })

export const quitarMedicamento = (id: string, renglon: string, contexto: Contexto) =>
  pedir<Encuentro>(`${enc(id)}/prescription/${encodeURIComponent(renglon)}/`, { ...contexto, metodo: 'DELETE' })

export const agregarOrden = (id: string, datos: DatosOrden, contexto: Contexto) =>
  pedir<Encuentro>(`${enc(id)}/orders/`, { ...contexto, metodo: 'POST', cuerpo: datos })

export const quitarOrden = (id: string, orden: string, contexto: Contexto) =>
  pedir<Encuentro>(`${enc(id)}/orders/${encodeURIComponent(orden)}/`, { ...contexto, metodo: 'DELETE' })

async function errorDe(respuesta: Response): Promise<ErrorApi> {
  let cuerpo: { detail?: string; code?: string } = {}
  try { cuerpo = await respuesta.json() } catch { /* sin cuerpo JSON */ }
  return new ErrorApi(cuerpo.detail ?? `Error ${respuesta.status}`,
    (cuerpo.code ?? 'desconocido') as CodigoError, respuesta.status)
}

/**
 * Baja la receta firmada en PDF. La pueden bajar el médico que atendió y
 * quien tiene alcance sobre el historial (el paciente, el titular de un
 * dependiente). El backend lo deja en la bitácora.
 */
export async function descargarReceta(id: string, { token }: Contexto): Promise<string> {
  const respuesta = await fetch(`${BASE}${enc(id)}/prescription.pdf`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!respuesta.ok) throw await errorDe(respuesta)
  const disposicion = respuesta.headers.get('Content-Disposition') ?? ''
  const nombre = /filename="([^"]+)"/.exec(disposicion)?.[1] ?? 'receta.pdf'
  const url = URL.createObjectURL(await respuesta.blob())
  const enlace = Object.assign(document.createElement('a'), { href: url, download: nombre })
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  URL.revokeObjectURL(url)
  return nombre
}
