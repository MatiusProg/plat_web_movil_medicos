/**
 * Cliente HTTP de la plataforma.
 *
 * Una sola puerta de salida hacia el backend, para que tres cosas estén
 * resueltas en un solo lugar y no repartidas por cada pantalla:
 *
 *   1. el encabezado `Authorization` con el token vigente,
 *   2. el encabezado `X-Organization`, que es como el backend resuelve el
 *      inquilino en las peticiones sin autenticar,
 *   3. la traducción de la respuesta de error a un `ErrorApi` con código.
 *
 * El refresco automático vive en `sesion.ts` y no acá: para renovar hace falta
 * saber qué hacer si la renovación también falla —cerrar la sesión y mandar al
 * login—, y eso es una decisión de la sesión, no del transporte.
 */

import { ErrorApi, type CodigoError } from './tipos'

const BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  'http://localhost:8000/api'

/** Lo que el cliente necesita saber de la sesión, sin depender de ella. */
export interface Contexto {
  token?: string | null
  organizacion?: string | null
}

interface Opciones extends Contexto {
  metodo?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  cuerpo?: unknown
  /** Aborta la petición si el usuario cierra el formulario a mitad de camino. */
  senal?: AbortSignal
}

export async function pedir<T>(ruta: string, opciones: Opciones = {}): Promise<T> {
  const { metodo = 'GET', cuerpo, token, organizacion, senal } = opciones

  const encabezados: Record<string, string> = {
    Accept: 'application/json',
  }
  if (cuerpo !== undefined) encabezados['Content-Type'] = 'application/json'
  if (token) encabezados.Authorization = `Bearer ${token}`
  if (organizacion) encabezados['X-Organization'] = organizacion

  let respuesta: Response
  try {
    respuesta = await fetch(`${BASE}${ruta}`, {
      method: metodo,
      headers: encabezados,
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
      signal: senal,
    })
  } catch (error) {
    // fetch sólo rechaza si la petición no llegó a salir: servidor caído, DNS,
    // CORS. Un 500 del backend NO pasa por acá, llega como respuesta.
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ErrorApi(
      'No se pudo conectar con el servidor. Revisá que el backend esté corriendo.',
      'sin_conexion',
      0,
    )
  }

  if (respuesta.status === 204) return undefined as T

  const datos = await leerJson(respuesta)

  if (!respuesta.ok) throw construirError(respuesta.status, datos)

  return datos as T
}

async function leerJson(respuesta: Response): Promise<unknown> {
  const tipo = respuesta.headers.get('Content-Type') ?? ''
  if (!tipo.includes('application/json')) return null
  try {
    return await respuesta.json()
  } catch {
    return null
  }
}

function construirError(estado: number, datos: unknown): ErrorApi {
  const cuerpo = (datos ?? {}) as Record<string, unknown>

  const codigo = (typeof cuerpo.code === 'string' ? cuerpo.code : null) as
    | CodigoError
    | null

  const detalle =
    typeof cuerpo.detail === 'string' ? cuerpo.detail : mensajePorDefecto(estado)

  // DRF devuelve las validaciones de forma como { campo: ["mensaje", ...] }.
  const porCampo: Record<string, string[]> = {}
  for (const [clave, valor] of Object.entries(cuerpo)) {
    if (clave === 'code' || clave === 'detail') continue
    if (Array.isArray(valor) && valor.every((v) => typeof v === 'string')) {
      porCampo[clave] = valor as string[]
    }
  }

  const primerCampo = Object.values(porCampo)[0]?.[0]

  return new ErrorApi(
    codigo && detalle !== mensajePorDefecto(estado)
      ? detalle
      : (primerCampo ?? detalle),
    codigo ?? 'desconocido',
    estado,
    {
      bloqueadaHasta:
        typeof cuerpo.locked_until === 'string' ? cuerpo.locked_until : undefined,
      porCampo: Object.keys(porCampo).length > 0 ? porCampo : undefined,
    },
  )
}

function mensajePorDefecto(estado: number): string {
  if (estado >= 500) return 'El servidor tuvo un problema. Intentá de nuevo en un momento.'
  if (estado === 404) return 'No se encontró lo que buscabas.'
  return 'La petición no se pudo completar.'
}
