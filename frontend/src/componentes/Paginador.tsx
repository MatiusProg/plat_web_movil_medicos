import { TAMANO_PAGINA } from '@/api/paginacion'

/**
 * Anterior · Página X de Y · Siguiente, con el total de elementos.
 *
 * Va debajo de toda lista que el usuario recorre. No se oculta cuando hay una
 * sola página: el "1 de 1 · 12 en total" también le dice a quien mira que no
 * hay nada más.
 */
export function Paginador({ pagina, total, tamano = TAMANO_PAGINA, cargando = false, onCambiar }: {
  pagina: number
  total: number
  tamano?: number
  cargando?: boolean
  onCambiar: (pagina: number) => void
}) {
  const paginas = Math.max(1, Math.ceil(total / tamano))
  const desde = total === 0 ? 0 : (pagina - 1) * tamano + 1
  const hasta = Math.min(total, pagina * tamano)
  const boton = 'rounded-xl border border-tinta-300 px-3 py-2 text-sm font-medium text-tinta-700 transition hover:bg-tinta-100 disabled:opacity-40 dark:border-tinta-700 dark:text-tinta-200 dark:hover:bg-tinta-800'
  return <nav aria-label="Paginación" className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-tinta-200 pt-4 text-sm dark:border-tinta-800">
    <p className="text-tinta-500">{total === 0 ? 'Sin resultados' : `${desde}–${hasta} de ${total}`}</p>
    <div className="flex items-center gap-2">
      <button type="button" className={boton} disabled={cargando || pagina <= 1} onClick={() => onCambiar(pagina - 1)}>← Anterior</button>
      <span className="px-1 tabular-nums text-tinta-600 dark:text-tinta-300">Página {pagina} de {paginas}</span>
      <button type="button" className={boton} disabled={cargando || pagina >= paginas} onClick={() => onCambiar(pagina + 1)}>Siguiente →</button>
    </div>
  </nav>
}
