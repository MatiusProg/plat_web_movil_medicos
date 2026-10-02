/** US-32: servicios y estudios —precio y preparación— y la reindexación del asistente. */
import { pedir, type Contexto } from './cliente'

export type TipoServicio = 'consultation' | 'study' | 'procedure'

export const TIPOS_SERVICIO: { valor: TipoServicio; etiqueta: string }[] = [
  { valor: 'consultation', etiqueta: 'Consulta' },
  { valor: 'study', etiqueta: 'Estudio' },
  { valor: 'procedure', etiqueta: 'Procedimiento' },
]

export interface Servicio {
  id: string
  name: string
  kind: TipoServicio
  kind_display: string
  specialty: string | null
  specialty_name: string | null
  description: string
  preparation: string
  /** Decimal como texto ("80.00"). `null` es "a consultar". */
  price: string | null
  currency: string
  is_active: boolean
}

export type ServicioEscritura = Pick<
  Servicio, 'name' | 'kind' | 'specialty' | 'description' | 'preparation' | 'price'
>

export interface ResumenReindexado {
  specialties: number
  branches: number
  services: number
  fragments: number
  embedding_model: string
}

const services = '/catalog/services/'

export const listarServicios = (contexto: Contexto, senal?: AbortSignal) =>
  pedir<Servicio[]>(services, { ...contexto, senal })

export const crearServicio = (data: ServicioEscritura, contexto: Contexto) =>
  pedir<Servicio>(services, { ...contexto, metodo: 'POST', cuerpo: data })

export const editarServicio = (id: string, data: ServicioEscritura, contexto: Contexto) =>
  pedir<Servicio>(`${services}${encodeURIComponent(id)}/`, {
    ...contexto, metodo: 'PATCH', cuerpo: data,
  })

export const desactivarServicio = (id: string, contexto: Contexto) =>
  pedir<Servicio>(`${services}${encodeURIComponent(id)}/deactivate/`, {
    ...contexto, metodo: 'POST',
  })

/** Vuelve a calcular el índice del asistente con el catálogo actual. */
export const reindexarAsistente = (contexto: Contexto) =>
  pedir<ResumenReindexado>('/assistant/reindex/', { ...contexto, metodo: 'POST' })
