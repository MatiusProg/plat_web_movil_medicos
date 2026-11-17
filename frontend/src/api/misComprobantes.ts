/**
 * Mis comprobantes, pedidos hablando o escribiendo.
 *
 *     POST /api/payments/mine/receipts/interpret/   de la frase a la consulta
 *     GET  /api/payments/mine/receipts/             la lista, o el PDF con los QR
 *
 * Dos pasos, como el reporte por voz del personal: `interpretar` **propone**
 * una consulta y no devuelve datos; quien habló la ve y recién ahí se pide la
 * lista. La consulta no dice de quién son los datos: eso lo decide la sesión en
 * el backend (el paciente y sus dependientes), así que no hay un campo para
 * pedir los de otra persona.
 *
 * Las claves de la consulta van en español —son las de la consigna de la
 * historia— y el resto, en inglés, como lo manda el backend.
 */
import { descargarArchivo, pedir, type Contexto } from './cliente'

export type TipoDeComprobante = 'pagos' | 'fichas'

/** Cómo se muestra la lista. Solo presentación: no cambia qué entra. */
export type Agrupacion = 'mes' | 'sucursal' | 'especialidad' | 'profesional'

/** Lo que entendió el sistema. Se manda tal cual al listado. */
export interface Consulta {
  tipo: TipoDeComprobante
  cantidad: number | null
  /** AAAA-MM-DD */
  desde: string | null
  hasta: string | null
  /** Id de la especialidad del centro. */
  especialidad: string | null
  /** Solo para mostrarla; no viaja al listado. */
  especialidad_nombre: string | null
  /** Id del profesional del centro, si pidió «con la doctora Gómez». */
  profesional: string | null
  /** Solo para mostrarlo; no viaja al listado. */
  profesional_nombre: string | null
  /** Cómo agrupar la lista. Lo decide el backend desde la frase. */
  agrupar: Agrupacion | null
}

export interface Propuesta {
  understood: boolean
  consulta: Consulta | null
  /** La consulta en palabras, armada por el backend. */
  spoken_summary: string
  /** Lo que se pidió y no se pudo resolver, o avisos. */
  unresolved: string[]
  generated_by: 'gemini' | 'plantilla'
}

export interface Comprobante {
  /** Id del pago o de la ficha, según el tipo. */
  id: string
  appointment_id: string
  /** El contenido del QR. Lo dibuja la pantalla. */
  code: string
  date: string
  starts_at: string
  patient_name: string
  is_dependent: boolean
  practitioner_name: string
  specialties: string[]
  branch_name: string
  status: 'confirmed' | 'attended'
  /** Solo en los pagos. */
  amount: string | null
  currency: string | null
  provider: string | null
  paid_at: string | null
}

/** Un grupo de la lista, con lo que suma. Cada comprobante cae en uno solo. */
export interface Grupo {
  key: string
  label: string
  count: number
  /** Lo cobrado por moneda. Vacío en las fichas. */
  totals: { currency: string; amount: string }[]
  items: Comprobante[]
}

export interface ListaDeComprobantes {
  tipo: TipoDeComprobante
  count: number
  limit: number
  /** Había más de lo pedido. */
  truncated: boolean
  summary: string
  agrupar: Agrupacion | null
  /** Vacío si no se pidió agrupar. `items` sigue trayendo la lista completa. */
  groups: Grupo[]
  items: Comprobante[]
}

const RUTA = '/payments/mine/receipts/'

export const interpretarComprobantes = (
  texto: string,
  contexto: Contexto,
  senal?: AbortSignal,
) =>
  pedir<Propuesta>(`${RUTA}interpret/`, {
    ...contexto,
    senal,
    metodo: 'POST',
    cuerpo: { text: texto },
  })

/** Los parámetros de la URL. El nombre `formato` y no `format`: DRF reserva `?format=`. */
function parametros(consulta: Consulta, formato: 'json' | 'pdf'): string {
  const url = new URLSearchParams({ tipo: consulta.tipo, formato })
  if (consulta.cantidad !== null) url.set('cantidad', String(consulta.cantidad))
  if (consulta.desde) url.set('desde', consulta.desde)
  if (consulta.hasta) url.set('hasta', consulta.hasta)
  if (consulta.especialidad) url.set('especialidad', consulta.especialidad)
  if (consulta.profesional) url.set('profesional', consulta.profesional)
  if (consulta.agrupar) url.set('agrupar', consulta.agrupar)
  return url.toString()
}

export const listarComprobantes = (
  consulta: Consulta,
  contexto: Contexto,
  senal?: AbortSignal,
) => pedir<ListaDeComprobantes>(`${RUTA}?${parametros(consulta, 'json')}`, { ...contexto, senal })

/** Baja el PDF con los QR. Devuelve el nombre con el que se guardó. */
export const descargarComprobantesPdf = (consulta: Consulta, contexto: Contexto) =>
  descargarArchivo(
    `${RUTA}?${parametros(consulta, 'pdf')}`,
    contexto,
    `mis-comprobantes-de-${consulta.tipo}.pdf`,
  )
