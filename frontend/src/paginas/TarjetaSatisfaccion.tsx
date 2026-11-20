/**
 * US-48 — La tarjeta «Satisfacción» del panel de indicadores.
 *
 * Pide lo suyo a `GET /api/reporting/satisfaction/` con los mismos filtros que
 * el resto del panel: el promedio grande, las barras de 1 a 5, una tabla por
 * médico, especialidad o sede que se ordena, y los últimos comentarios **sin
 * el nombre del paciente** (el backend ni lo manda).
 *
 * Vive aparte de `Kpis.tsx` para que el panel sólo tenga que montarla.
 */
import { useEffect, useMemo, useState } from 'react'
import {
  promedio, verMisEstrellas, verSatisfaccion,
  type PromedioPorNombre, type ResumenEstrellas, type Satisfaccion,
} from '@/api/calificaciones'
import { Bloque } from '@/componentes/Indicadores'
import { useSesion } from '@/sesion/useSesion'
import { mensajeError } from './catalogo_comun'
import { estrellasEnTexto } from './CalificarAtencion'

type Vista = 'by_practitioner' | 'by_specialty' | 'by_branch'
const VISTAS: { clave: Vista; etiqueta: string; columna: string }[] = [
  { clave: 'by_practitioner', etiqueta: 'Por médico', columna: 'Médico' },
  { clave: 'by_specialty', etiqueta: 'Por especialidad', columna: 'Especialidad' },
  { clave: 'by_branch', etiqueta: 'Por sede', columna: 'Sede' },
]
type Orden = 'name' | 'average' | 'count'

function Distribucion({ datos }: { datos: Satisfaccion }) {
  const maximo = Math.max(1, ...datos.distribution.map(d => d.total))
  return <ul className="space-y-1.5" aria-label="Distribución de 1 a 5 estrellas">
    {[...datos.distribution].reverse().map(d =>
      <li key={d.stars} className="flex items-center gap-2 text-sm">
        <span className="w-8 shrink-0 tabular-nums text-tinta-600 dark:text-tinta-300">{d.stars} ★</span>
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-tinta-100 dark:bg-tinta-800" role="progressbar"
          aria-label={`${d.stars} estrellas`} aria-valuenow={d.total} aria-valuemin={0} aria-valuemax={maximo}>
          <div className="h-full rounded-full bg-amber-400 motion-safe:transition-[width] motion-safe:duration-500"
            style={{ width: `${(d.total / maximo) * 100}%` }} />
        </div>
        <span className="w-8 shrink-0 text-right tabular-nums text-tinta-500">{d.total}</span>
      </li>)}
  </ul>
}

function Tabla({ filas, columna }: { filas: PromedioPorNombre[]; columna: string }) {
  const [orden, setOrden] = useState<{ campo: Orden; asc: boolean }>({ campo: 'average', asc: false })
  const ordenadas = useMemo(() => [...filas].sort((a, b) => {
    const signo = orden.asc ? 1 : -1
    if (orden.campo === 'name') return signo * a.name.localeCompare(b.name, 'es')
    return signo * (a[orden.campo] - b[orden.campo])
  }), [filas, orden])

  const cabecera = (campo: Orden, texto: string, derecha = false) => {
    const activo = orden.campo === campo
    return <th scope="col" aria-sort={activo ? (orden.asc ? 'ascending' : 'descending') : 'none'}
      className={`py-2 font-medium ${derecha ? 'text-right' : 'text-left'}`}>
      <button type="button" className="hover:text-tinta-900 dark:hover:text-tinta-100"
        onClick={() => setOrden({ campo, asc: activo ? !orden.asc : campo === 'name' })}>
        {texto}{activo ? (orden.asc ? ' ↑' : ' ↓') : ''}
      </button>
    </th>
  }

  if (filas.length === 0) return <p className="text-sm text-tinta-500">Sin calificaciones en este rango.</p>
  return <div className="overflow-x-auto"><table className="w-full text-sm">
    <thead className="border-b border-tinta-200 text-tinta-500 dark:border-tinta-800">
      <tr>{cabecera('name', columna)}{cabecera('average', 'Promedio', true)}{cabecera('count', 'Calificaciones', true)}</tr>
    </thead>
    <tbody className="divide-y divide-tinta-100 dark:divide-tinta-800">{ordenadas.map(f =>
      <tr key={f.id ?? f.name}>
        <td className="py-2 text-tinta-700 dark:text-tinta-300">{f.name}</td>
        <td className="py-2 text-right tabular-nums font-medium text-tinta-900 dark:text-tinta-100">★ {promedio(f.average)}</td>
        <td className="py-2 text-right tabular-nums text-tinta-500">{f.count}</td>
      </tr>)}</tbody>
  </table></div>
}

export function TarjetaSatisfaccion({ desde, hasta, sucursal }: { desde: string; hasta: string; sucursal: string }) {
  const { token } = useSesion()
  const clave = `${desde}|${hasta}|${sucursal}`
  const [respuesta, setRespuesta] = useState<{ clave: string; datos?: Satisfaccion; error?: string } | null>(null)
  const [vista, setVista] = useState<Vista>('by_practitioner')

  useEffect(() => {
    if (!desde || !hasta || desde > hasta) return
    const c = new AbortController()
    verSatisfaccion({ from: desde, to: hasta, branch: sucursal || undefined }, { token }, c.signal)
      .then(datos => setRespuesta({ clave, datos }))
      .catch(e => { if (!(e instanceof DOMException)) setRespuesta({ clave, error: mensajeError(e) }) })
    return () => c.abort()
  }, [token, desde, hasta, sucursal, clave])

  const datos = respuesta?.datos && !respuesta.datos.plataforma ? respuesta.datos : null
  const cargando = respuesta?.clave !== clave
  const columna = VISTAS.find(v => v.clave === vista)!.columna

  return <Bloque titulo="Satisfacción"
    accion={datos && <span className="text-sm tabular-nums text-tinta-500">
      {datos.count} {datos.count === 1 ? 'calificación' : 'calificaciones'}</span>}>
    {respuesta?.error && <p role="alert" className="text-sm text-alerta-600">{respuesta.error}</p>}
    {!datos && !respuesta?.error && <p role="status" className="text-sm text-tinta-500">Calculando…</p>}
    {datos && <div className={`space-y-6 ${cargando ? 'opacity-60' : ''}`} aria-busy={cargando}>
      <div className="grid gap-6 md:grid-cols-[auto_1fr] md:items-center">
        <div>
          <p className="text-5xl font-semibold tabular-nums text-tinta-900 dark:text-tinta-50">
            <span className="text-amber-400">★</span> {promedio(datos.average)}</p>
          <p className="mt-1 text-sm text-tinta-500">
            {datos.count === 0 ? 'Todavía nadie calificó en este rango.' : `de ${datos.count} ${datos.count === 1 ? 'calificación' : 'calificaciones'}`}</p>
        </div>
        <Distribucion datos={datos} />
      </div>

      <div>
        <div className="mb-3 flex flex-wrap gap-1" role="tablist" aria-label="Agrupar por">
          {VISTAS.map(v => <button key={v.clave} type="button" role="tab" aria-selected={vista === v.clave}
            onClick={() => setVista(v.clave)}
            className={`rounded-full px-3 py-1 text-sm font-medium transition ${vista === v.clave
              ? 'bg-marca-600 text-white'
              : 'text-tinta-600 hover:bg-tinta-100 dark:text-tinta-300 dark:hover:bg-tinta-800'}`}>{v.etiqueta}</button>)}
        </div>
        <Tabla key={vista} filas={datos[vista]} columna={columna} />
        {vista === 'by_specialty' && datos.by_specialty.length > 0 && <p className="mt-2 text-xs text-tinta-500">
          Un médico con varias especialidades suma en cada una.</p>}
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold text-tinta-800 dark:text-tinta-100">Últimos comentarios</h3>
        {datos.latest_comments.length === 0
          ? <p className="text-sm text-tinta-500">No hay comentarios en este rango.</p>
          : <ul className="divide-y divide-tinta-100 dark:divide-tinta-800">{datos.latest_comments.map((c, i) =>
            <li key={i} className="py-2.5 text-sm">
              <p className="text-tinta-800 dark:text-tinta-100">
                <span className="mr-2 text-amber-500" aria-label={`${c.stars} de 5 estrellas`}>{estrellasEnTexto(c.stars)}</span>
                «{c.comment}»</p>
              <p className="mt-0.5 text-xs text-tinta-500">
                {c.practitioner_name} · {c.branch_name} · {new Date(c.created_at).toLocaleDateString('es-BO', { dateStyle: 'medium' })}</p>
            </li>)}</ul>}
        <p className="mt-2 text-xs text-tinta-500">Los comentarios se muestran sin el nombre del paciente.</p>
      </div>
    </div>}
  </Bloque>
}

/**
 * El médico ve su promedio en *Atención del día*, y nada de quién lo
 * calificó: el endpoint sólo trae el promedio y la distribución.
 */
export function MiPromedio() {
  const { token } = useSesion()
  const [datos, setDatos] = useState<ResumenEstrellas | null>(null)
  useEffect(() => {
    const c = new AbortController()
    verMisEstrellas({ token }, c.signal).then(setDatos).catch(() => {})
    return () => c.abort()
  }, [token])
  if (!datos || datos.count === 0) return null
  return <p className="mt-2 inline-flex items-center gap-2 rounded-full bg-amber-50 px-3 py-1 text-sm text-amber-800 dark:bg-amber-500/10 dark:text-amber-200"
    title="Lo calcula el sistema con las calificaciones de tus pacientes. No muestra quién calificó.">
    <span aria-hidden>★</span>
    <span>Tu promedio: <strong className="tabular-nums">{promedio(datos.average)}</strong> de {datos.count} {datos.count === 1 ? 'calificación' : 'calificaciones'}</span>
  </p>
}
