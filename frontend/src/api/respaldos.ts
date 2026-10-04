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
}

export interface RegistroRespaldo {
  id: string
  kind: 'backup' | 'restore'
  kind_label: string
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
export async function generarRespaldo({ token }: Contexto): Promise<string> {
  const respuesta = await fetch(`${BASE}/backups/create/`, {
    method: 'POST', headers: { Authorization: `Bearer ${token}` },
  })
  if (!respuesta.ok) throw await errorDe(respuesta)
  const disposicion = respuesta.headers.get('Content-Disposition') ?? ''
  const nombre = /filename="([^"]+)"/.exec(disposicion)?.[1] ?? 'respaldo.json'
  const url = URL.createObjectURL(await respuesta.blob())
  const enlace = Object.assign(document.createElement('a'), { href: url, download: nombre })
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  URL.revokeObjectURL(url)
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

/** Reemplaza los datos de la organización con los del archivo. */
export const restaurarRespaldo = (archivo: File, contexto: Contexto) =>
  subir<{ written: Record<string, number> }>('/backups/restore/', archivo, contexto, { confirm: 'true' })
