/**
 * Característica general 6 — Copias de seguridad de la organización.
 *
 * La descarga y la subida no son JSON, así que no pasan por `pedir()`: van
 * con `fetch` directo, con el mismo token y la misma traducción de errores.
 */
import { pedir, type Contexto } from './cliente'
import { ErrorApi, type CodigoError } from './tipos'

const BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000/api'

export interface PoliticaRespaldo {
  plan_code: string | null
  plan_name: string | null
  /** `null` = a voluntad. */
  interval_hours: number | null
  last_backup_at: string | null
  next_available_at: string | null
  allowed_now: boolean
  description: string
  /** Las que genera el sistema solo. Ver `backups/automatic.py`. */
  automatic?: {
    enabled: boolean
    interval_hours: number | null
    /** Cuántas conserva el plan. */
    retention: number
    last_at: string | null
    next_at: string | null
    description: string
  }
}

export interface RegistroRespaldo {
  id: string
  kind: 'backup' | 'restore'
  kind_label: string
  trigger: 'manual' | 'automatic'
  trigger_label: string
  /** Una automática que el plan todavía conserva: se baja o se restaura desde acá. */
  downloadable: boolean
  filename: string
  size_bytes: number
  total_rows: number
  checksum: string
  performed_by_email: string | null
  created_at: string
}

export interface Inspeccion {
  organization: { id?: string; slug?: string; name?: string }
  generated_at: string | null
  counts: Record<string, number>
  labels: Record<string, string>
  belongs_to_my_organization: boolean
}

interface Pagina<T> { count: number; next: string | null; results: T[] }

export const verPolitica = (contexto: Contexto, senal?: AbortSignal) =>
  pedir<PoliticaRespaldo>('/backups/policy/', { ...contexto, senal })

/** Todo el historial, recorriendo las páginas: no sólo las primeras 25. */
export async function verHistorial(contexto: Contexto, senal?: AbortSignal) {
  const todos: RegistroRespaldo[] = []
  let pagina = 1
  for (;;) {
    const datos = await pedir<Pagina<RegistroRespaldo>>(`/backups/records/?page=${pagina}`, { ...contexto, senal })
    todos.push(...datos.results)
    if (!datos.next) return todos
    pagina += 1
  }
}

async function errorDe(respuesta: Response): Promise<ErrorApi> {
  let cuerpo: { detail?: string; code?: string } = {}
  try { cuerpo = await respuesta.json() } catch { /* sin cuerpo JSON */ }
  return new ErrorApi(cuerpo.detail ?? `Error ${respuesta.status}`,
    (cuerpo.code ?? 'desconocido') as CodigoError, respuesta.status)
}

/** Genera la copia y la baja como archivo. Devuelve el nombre del archivo. */
export const generarRespaldo = ({ token }: Contexto) =>
  bajar(`${BASE}/backups/create/`, 'POST', token)

/** Baja una copia automática guardada. */
export const descargarCopia = (id: string, { token }: Contexto) =>
  bajar(`${BASE}/backups/records/${id}/download/`, 'GET', token)

async function bajar(url: string, method: 'GET' | 'POST', token?: string | null): Promise<string> {
  const respuesta = await fetch(url, { method, headers: { Authorization: `Bearer ${token}` } })
  if (!respuesta.ok) throw await errorDe(respuesta)
  const disposicion = respuesta.headers.get('Content-Disposition') ?? ''
  const nombre = /filename="([^"]+)"/.exec(disposicion)?.[1] ?? 'respaldo.json'
  const enlaceUrl = URL.createObjectURL(await respuesta.blob())
  const enlace = Object.assign(document.createElement('a'), { href: enlaceUrl, download: nombre })
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  URL.revokeObjectURL(enlaceUrl)
  return nombre
}

async function subir<T>(ruta: string, archivo: File, { token }: Contexto, extra: Record<string, string> = {}) {
  const datos = new FormData()
  datos.append('file', archivo)
  for (const [clave, valor] of Object.entries(extra)) datos.append(clave, valor)
  const respuesta = await fetch(`${BASE}${ruta}`, {
    method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: datos,
  })
  if (!respuesta.ok) throw await errorDe(respuesta)
  return (await respuesta.json()) as T
}

/** Qué trae el archivo. No escribe nada. */
export const inspeccionarRespaldo = (archivo: File, contexto: Contexto) =>
  subir<Inspeccion>('/backups/inspect/', archivo, contexto)

export interface ResultadoRestauracion {
  written: Record<string, number>
  /** Lo posterior a la copia que la historia clínica o un pago no dejan borrar. */
  kept: Record<string, number>
}

/** Reemplaza los datos de la organización con los del archivo. */
export const restaurarRespaldo = (archivo: File, contexto: Contexto) =>
  subir<ResultadoRestauracion>('/backups/restore/', archivo, contexto, { confirm: 'true' })

/** Qué trae una copia automática del historial. No escribe nada. */
export const inspeccionarCopia = (id: string, contexto: Contexto) =>
  pedir<Inspeccion>('/backups/inspect/', { ...contexto, metodo: 'POST', cuerpo: { record: id } })

/** Restaura desde una copia automática del historial, sin subir ningún archivo. */
export const restaurarCopia = (id: string, contexto: Contexto) =>
  pedir<ResultadoRestauracion>('/backups/restore/', { ...contexto, metodo: 'POST', cuerpo: { record: id, confirm: true } })
