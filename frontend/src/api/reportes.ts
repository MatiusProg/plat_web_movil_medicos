/**
 * Característica general 5 — El constructor de reportes.
 *
 *     GET  /api/reporting/datasets/   qué se puede reportar y con qué filtros
 *     POST /api/reporting/run/        ejecutar la definición armada
 *     POST /api/reporting/interpret/  traducir un pedido dictado por voz
 *
 * La vista previa viaja como JSON y pasa por `pedir()`. La exportación no: un
 * Excel o un PDF son binarios, así que van con `fetch` directo y la misma
 * traducción de errores, igual que hace `api/respaldos.ts`.
 */
import { pedir, type Contexto } from './cliente'
import { ErrorApi, type CodigoError } from './tipos'

const BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000/api'

/** Los tipos que el formulario sabe dibujar. Los declara el backend. */
export type TipoDeCampo = 'text' | 'number' | 'date' | 'datetime' | 'boolean' | 'choice'

export type Formato = 'json' | 'csv' | 'xlsx' | 'html' | 'pdf'

export interface OpcionDeCampo {
  value: string
  label: string
}

export interface CampoDeReporte {
  code: string
  label: string
  kind: TipoDeCampo
  choices: OpcionDeCampo[] | null
  /** Sólo en los filtros: qué comparaciones admite este campo. */
  operators?: string[]
}

export interface ConjuntoDeDatos {
  code: string
  label: string
  description: string
  columns: CampoDeReporte[]
  filters: CampoDeReporte[]
  default_columns: string[]
}

export interface CatalogoDeReportes {
  datasets: ConjuntoDeDatos[]
  formats: string[]
  max_rows: number
}

export interface CriterioDeFiltro {
  field: string
  operator: string
  value: string | number | boolean
}

export interface DefinicionDeReporte {
  dataset: string
  columns: string[]
  filters: CriterioDeFiltro[]
  order_by: string[]
  format?: Formato
}

export interface VistaPrevia {
  dataset: string
  title: string
  columns: { code: string; label: string; kind: TipoDeCampo }[]
  rows: (string | number | null)[][]
  truncated: boolean
}

/** Lo que el backend entendió de un pedido dictado. */
export interface Interpretacion {
  understood: boolean
  definition: DefinicionDeReporte | null
  spoken_summary: string
  unresolved: string[]
  /** `plantilla` = el modelo de lenguaje no participó. */
  generated_by: 'gemini' | 'plantilla'
}

/** Las comparaciones, en palabras. El backend manda el código. */
export const COMPARACIONES: Record<string, string> = {
  eq: 'es igual a',
  contains: 'contiene',
  starts: 'empieza con',
  lt: 'es anterior a',
  lte: 'hasta',
  gt: 'es posterior a',
  gte: 'desde',
  in: 'está entre',
}

export const listarConjuntos = (contexto: Contexto, senal?: AbortSignal) =>
  pedir<CatalogoDeReportes>('/reporting/datasets/', { ...contexto, senal })

/** La vista previa: las primeras filas, sin generar ningún archivo. */
export const previsualizar = (
  definicion: DefinicionDeReporte,
  contexto: Contexto,
  senal?: AbortSignal,
) =>
  pedir<VistaPrevia>('/reporting/run/', {
    ...contexto,
    senal,
    metodo: 'POST',
    cuerpo: { ...definicion, format: 'json' },
  })

export const interpretarPorVoz = (
  texto: string,
  dataset: string,
  contexto: Contexto,
  senal?: AbortSignal,
) =>
  pedir<Interpretacion>('/reporting/interpret/', {
    ...contexto,
    senal,
    metodo: 'POST',
    cuerpo: { text: texto, dataset },
  })

/** Manda el reporte por correo. Devuelve a cuántas casillas salió. */
export const enviarPorCorreo = (
  definicion: DefinicionDeReporte,
  destinatarios: string[],
  titulo: string,
  contexto: Contexto,
) =>
  pedir<{ sent_to: string[] }>('/reporting/run/', {
    ...contexto,
    metodo: 'POST',
    cuerpo: { ...definicion, title: titulo, recipients: destinatarios },
  })

async function errorDe(respuesta: Response): Promise<ErrorApi> {
  let cuerpo: { detail?: string; code?: string } = {}
  try {
    cuerpo = await respuesta.json()
  } catch {
    /* sin cuerpo JSON */
  }
  return new ErrorApi(
    cuerpo.detail ?? `Error ${respuesta.status}`,
    (cuerpo.code ?? 'desconocido') as CodigoError,
    respuesta.status,
  )
}

/** Genera el archivo y lo baja. Devuelve el nombre con el que se guardó. */
export async function exportar(
  definicion: DefinicionDeReporte,
  formato: Exclude<Formato, 'json'>,
  titulo: string,
  { token, organizacion }: Contexto,
): Promise<string> {
  const encabezados: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) encabezados.Authorization = `Bearer ${token}`
  if (organizacion) encabezados['X-Organization'] = organizacion

  const respuesta = await fetch(`${BASE}/reporting/run/`, {
    method: 'POST',
    headers: encabezados,
    body: JSON.stringify({ ...definicion, format: formato, title: titulo }),
  })
  if (!respuesta.ok) throw await errorDe(respuesta)

  const disposicion = respuesta.headers.get('Content-Disposition') ?? ''
  const nombre = /filename="([^"]+)"/.exec(disposicion)?.[1] ?? `reporte.${formato}`
  const url = URL.createObjectURL(await respuesta.blob())
  const enlace = Object.assign(document.createElement('a'), { href: url, download: nombre })
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  URL.revokeObjectURL(url)
  return nombre
}
