/**
 * US-53 — Cómo evolucionan los signos vitales a lo largo de las atenciones
 * firmadas. SVG a mano, igual que el gráfico de Contabilidad: no hace falta
 * una librería para una línea y una franja.
 *
 * Se grafica lo que se firmó. Si el médico lo corrigió con una enmienda, el
 * punto va hueco y la corrección se lee en la línea de tiempo: la gráfica no
 * interpreta el texto de la enmienda.
 */
import { useState } from 'react'
import { SECONDARY } from './catalogo_comun'
import { SERIES, puntosDe, type ConSignos, type IdSerie, type Punto, type Serie } from './signos_vitales'

const ANCHO = 600, ALTO = 230, IZQ = 46, DER = 16, ARRIBA = 14, ABAJO = 32
const COLORES = [
  { linea: 'stroke-marca-600 dark:stroke-marca-400', punto: 'fill-marca-600 stroke-marca-600 dark:fill-marca-400 dark:stroke-marca-400', franja: 'fill-marca-500/10', muestra: 'bg-marca-600' },
  { linea: 'stroke-tinta-500 dark:stroke-tinta-300', punto: 'fill-tinta-500 stroke-tinta-500 dark:fill-tinta-300 dark:stroke-tinta-300', franja: 'fill-tinta-500/10', muestra: 'bg-tinta-500' },
]

const num = (v: number) => v.toLocaleString('es-BO', { maximumFractionDigits: 1 })
const corta = (iso: string) => new Date(iso).toLocaleDateString('es-BO', { day: 'numeric', month: 'short', year: '2-digit' })
const larga = (iso: string) => new Date(iso).toLocaleDateString('es-BO', { day: 'numeric', month: 'long', year: 'numeric' })

/** Una serie dibujada: la franja de referencia, la línea y un punto por atención. */
export function GraficoSigno({ serie, puntos }: { serie: Serie; puntos: Punto[] }) {
  const unidad = serie.unidad ? ` ${serie.unidad}` : ''
  if (puntos.length === 0) return <p className="text-sm text-tinta-500">Todavía no hay mediciones de {serie.etiqueta.toLowerCase()}.</p>

  const valores = puntos.flatMap(p => p.valores.filter((v): v is number => v != null))
  const bordes = serie.lineas.flatMap(l => l.franja ?? [])
  let min = Math.min(...valores, ...bordes), max = Math.max(...valores, ...bordes)
  const margen = (max - min || Math.abs(max) || 1) * 0.08
  min -= margen; max += margen
  const y = (v: number) => ARRIBA + ((max - v) / (max - min)) * (ALTO - ARRIBA - ABAJO)
  const x = (i: number) => puntos.length === 1 ? (IZQ + ANCHO - DER) / 2 : IZQ + (i * (ANCHO - IZQ - DER)) / (puntos.length - 1)

  // Marcas del eje: primero los bordes de la franja, después lo medido, sin
  // encimarse (si un valor cae pegado a un borde, gana el borde).
  const marcas: number[] = []
  for (const v of [...bordes, Math.min(...valores), Math.max(...valores)])
    if (marcas.every(m => Math.abs(y(m) - y(v)) >= 14)) marcas.push(v)
  // Con muchas atenciones, una fecha cada tantas para que se lean.
  const cada = Math.ceil(puntos.length / 7)

  return <figure className="space-y-2">
    <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} className="h-auto w-full" role="img"
      aria-label={`${serie.etiqueta}: ${puntos.length} ${puntos.length === 1 ? 'medición' : 'mediciones'}, la última el ${larga(puntos[puntos.length - 1].fecha)}`}>
      {serie.lineas.map((l, i) => l.franja && <rect key={l.campo} x={IZQ} width={ANCHO - IZQ - DER}
        y={y(l.franja[1])} height={y(l.franja[0]) - y(l.franja[1])} className={COLORES[i].franja} />)}
      {marcas.map(m => <g key={m}>
        <line x1={IZQ} x2={ANCHO - DER} y1={y(m)} y2={y(m)} className="stroke-tinta-200 dark:stroke-tinta-800" strokeDasharray="3 4" />
        <text x={IZQ - 6} y={y(m) + 4} textAnchor="end" className="fill-tinta-500 text-[11px] tabular-nums">{num(m)}</text>
      </g>)}
      {puntos.map((p, i) => (i % cada === 0 || i === puntos.length - 1) && <text key={p.encuentro} x={x(i)} y={ALTO - 10}
        textAnchor={puntos.length === 1 ? 'middle' : i === 0 ? 'start' : i === puntos.length - 1 ? 'end' : 'middle'} className="fill-tinta-500 text-[11px]">{corta(p.fecha)}</text>)}
      {serie.lineas.map((l, j) => {
        const conValor = puntos.map((p, i) => ({ p, i, v: p.valores[j] })).filter(q => q.v != null)
        return <g key={l.campo}>
          {conValor.length > 1 && <polyline fill="none" strokeWidth="2.5" strokeLinejoin="round" className={COLORES[j].linea}
            strokeDasharray={j === 1 ? '6 4' : undefined} points={conValor.map(q => `${x(q.i)},${y(q.v!)}`).join(' ')} />}
          {conValor.map(q => <circle key={q.p.encuentro} cx={x(q.i)} cy={y(q.v!)} r="5" strokeWidth="2.5"
            className={`${COLORES[j].punto} ${q.p.enmendado ? '!fill-white dark:!fill-tinta-950' : ''}`}>
            <title>{`${larga(q.p.fecha)} · ${l.etiqueta}: ${num(q.v!)}${unidad}${q.p.enmendado ? ' (tiene una enmienda)' : ''}`}</title>
          </circle>)}
        </g>
      })}
    </svg>
    <figcaption className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-tinta-500">
      {serie.lineas.map((l, i) => <span key={l.campo}>
        <span aria-hidden="true" className={`mr-1 inline-block h-0.5 w-4 align-middle ${COLORES[i].muestra}`} />{serie.lineas.length > 1 ? l.etiqueta : 'Medido'}
        {l.franja && ` · franja normal ${num(l.franja[0])}–${num(l.franja[1])}${unidad}`}
      </span>)}
      {puntos.some(p => p.enmendado) && <span>○ con enmienda: la corrección está en la atención</span>}
      {puntos.length === 1 && <span>Con una sola medición todavía no hay evolución.</span>}
    </figcaption>
    <table className="sr-only">
      <caption>{serie.etiqueta}{unidad && ` en${unidad}`}</caption>
      <thead><tr><th scope="col">Fecha</th>{serie.lineas.map(l => <th key={l.campo} scope="col">{l.etiqueta}</th>)}</tr></thead>
      <tbody>{puntos.map(p => <tr key={p.encuentro}><th scope="row">{larga(p.fecha)}</th>
        {p.valores.map((v, j) => <td key={j}>{v == null ? '—' : num(v)}{p.enmendado ? ' (con enmienda)' : ''}</td>)}</tr>)}</tbody>
    </table>
  </figure>
}

/** El médico: un selector con los signos que se tomaron alguna vez y su gráfica. */
export function EvolucionSignos({ encuentros }: { encuentros: ConSignos[] }) {
  const conDatos = SERIES.map(s => ({ serie: s, puntos: puntosDe(s, encuentros) })).filter(s => s.puntos.length > 0)
  const [elegida, setElegida] = useState<IdSerie>(conDatos[0]?.serie.id ?? 'presion')
  if (conDatos.length === 0) return <p className="text-sm text-tinta-500">En ninguna atención firmada se tomaron signos vitales.</p>
  const actual = conDatos.find(s => s.serie.id === elegida) ?? conDatos[0]
  return <section className="space-y-4" aria-label="Evolución de los signos vitales">
    <div className="flex flex-wrap gap-2" role="group" aria-label="Signo vital">
      {conDatos.map(({ serie, puntos }) => <button key={serie.id} type="button" aria-pressed={actual.serie.id === serie.id}
        className={actual.serie.id === serie.id ? 'rounded-xl bg-marca-600 px-4 py-2 text-sm font-semibold text-white' : SECONDARY}
        onClick={() => setElegida(serie.id)}>{serie.etiqueta} · {puntos.length}</button>)}
    </div>
    <GraficoSigno serie={actual.serie} puntos={actual.puntos} />
  </section>
}
