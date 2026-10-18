/**
 * Piezas de indicadores que comparten el panel de inicio y el panel de KPIs
 * (US-29): la tarjeta con título, la cifra grande y la barra de uso.
 */
import type { ReactNode } from 'react'
import { PANEL } from '@/paginas/catalogo_comun'

export function Bloque({ titulo, accion, children }: { titulo: string; accion?: ReactNode; children: ReactNode }) {
  return <section className={PANEL} aria-label={titulo}>
    <div className="mb-4 flex items-center justify-between gap-3">
      <h2 className="font-semibold text-tinta-900 dark:text-tinta-100">{titulo}</h2>
      {accion}
    </div>
    {children}
  </section>
}

export function Cifra({ valor, etiqueta, tono = 'normal' }: { valor: number | string; etiqueta: string; tono?: 'normal' | 'marca' | 'espera' | 'alerta' }) {
  const color = { normal: 'text-tinta-900 dark:text-tinta-50', marca: 'text-marca-700 dark:text-marca-300', espera: 'text-espera-700 dark:text-espera-200', alerta: 'text-alerta-700 dark:text-alerta-500' }[tono]
  return <div>
    <p className={`text-3xl font-semibold tabular-nums ${color}`}>{valor}</p>
    <p className="mt-1 text-sm text-tinta-500">{etiqueta}</p>
  </div>
}

/** Una barra de uso contra el tope del plan. Ámbar desde el 80 %, rojo al llegar. */
export function Uso({ etiqueta, usados, tope }: { etiqueta: string; usados: number; tope: number | null }) {
  const porcentaje = tope ? Math.min(100, Math.round((usados / tope) * 100)) : 0
  const color = !tope ? 'bg-marca-500' : porcentaje >= 100 ? 'bg-alerta-600' : porcentaje >= 80 ? 'bg-espera-600' : 'bg-marca-500'
  return <div>
    <div className="flex items-baseline justify-between gap-3 text-sm">
      <span className="text-tinta-700 dark:text-tinta-300">{etiqueta}</span>
      <span className="tabular-nums text-tinta-500">{usados}{tope !== null ? ` de ${tope}` : ' · sin límite'}</span>
    </div>
    <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-tinta-100 dark:bg-tinta-800" role="progressbar"
      aria-label={etiqueta} aria-valuenow={usados} aria-valuemin={0} aria-valuemax={tope ?? undefined}>
      <div className={`h-full rounded-full ${color}`} style={{ width: tope ? `${porcentaje}%` : '100%', opacity: tope ? 1 : 0.25 }} />
    </div>
  </div>
}
