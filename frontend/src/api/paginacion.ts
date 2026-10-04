/**
 * Las listas paginadas de la API (`config/pagination.py`): 25 por página, y
 * hasta 100 con `?page_size=`.
 *
 * Dos formas de consumirlas, y la regla para elegir:
 *
 * - **Una lista que el usuario recorre** (usuarios, bloqueos, organizaciones)
 *   se muestra **paginada en la interfaz**, con el componente `Paginador`.
 *   Nunca se trunca a la primera página: es lo que pasó el 03/10/26 con la
 *   pantalla de usuarios, que mostraba 25 de ~80 sin avisar.
 * - **Un desplegable** (elegir profesional, actor, plan) no se puede paginar:
 *   se llena con `todasLasPaginas`.
 */
import { pedir, type Contexto } from './cliente'

export interface Pagina<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

/** Tamaño de página por defecto del backend. */
export const TAMANO_PAGINA = 25

function conParametros(ruta: string, parametros: Record<string, string | number | undefined>) {
  const [base, consulta = ''] = ruta.split('?')
  const p = new URLSearchParams(consulta)
  for (const [clave, valor] of Object.entries(parametros)) {
    if (valor !== undefined && valor !== '') p.set(clave, String(valor))
  }
  const texto = p.toString()
  return texto ? `${base}?${texto}` : base
}

/** Una página concreta de una lista. */
export function pedirPagina<T>(
  ruta: string, pagina: number, contexto: Contexto, senal?: AbortSignal,
  extra: Record<string, string | number | undefined> = {},
) {
  return pedir<Pagina<T>>(conParametros(ruta, { ...extra, page: pagina }), { ...contexto, senal })
}

/** La lista completa, recorriendo las páginas de a 100. Para desplegables. */
export async function todasLasPaginas<T>(
  ruta: string, contexto: Contexto, senal?: AbortSignal,
): Promise<T[]> {
  const todos: T[] = []
  for (let pagina = 1; ; pagina += 1) {
    const datos = await pedir<Pagina<T>>(
      conParametros(ruta, { page: pagina, page_size: 100 }), { ...contexto, senal },
    )
    todos.push(...datos.results)
    if (!datos.next) return todos
  }
}
