/**
 * US-29 — El panel de indicadores de la organización.
 *
 * Ocupación de agenda, inasistencia, demanda por sucursal y especialidad, e
 * ingresos por fichas, con filtro por rango de fechas y por sucursal. Todo sale
 * de `GET /api/reporting/kpis/` (`api/kpis.ts`); la definición de cada número
 * está en `docs/sprints/sprint-3/us-29-indicadores.md`.
 *
 * Los gráficos son SVG y CSS propios, sin librería: barras y un anillo bastan
 * para estos cuatro indicadores y heredan el tema claro y oscuro.
 */
import { useEffect, useState } from 'react'
import { listarSucursales, type Sucursal } from '@/api/catalogo'
import { verKpis, type Kpis as DatosKpis, type TotalPorNombre } from '@/api/kpis'
import { Bloque, Cifra } from '@/componentes/Indicadores'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'
import { CampoSeleccion, ErrorCatalogo, INPUT, mensajeError } from './catalogo_comun'

const aIso = (fecha: Date) => fecha.toLocaleDateString('en-CA')

function rangoPorDefecto() {
  const hasta = new Date()
  const desde = new Date()
  desde.setDate(hasta.getDate() - 29)
  return { desde: aIso(desde), hasta: aIso(hasta) }
}

const porcentaje = (tasa: number | null) =>
  tasa === null ? '—' : `${(tasa * 100).toLocaleString('es-BO', { maximumFractionDigits: 1 })} %`

const dinero = (total: string, moneda: string) =>
  `${Number(total).toLocaleString('es-BO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${moneda}`

/** Un anillo con la tasa al centro. Sin tasa (`null`) queda vacío. */
function Anillo({ tasa, etiqueta, tono }: { tasa: number | null; etiqueta: string; tono: string }) {
  const radio = 42
  const largo = 2 * Math.PI * radio
  const lleno = tasa === null ? 0 : Math.min(1, Math.max(0, tasa)) * largo
  return <div className="relative size-28 shrink-0">
    <svg viewBox="0 0 100 100" className="size-full -rotate-90" role="img"
      aria-label={`${etiqueta}: ${porcentaje(tasa)}`}>
      <circle cx="50" cy="50" r={radio} fill="none" strokeWidth="9" className="stroke-tinta-100 dark:stroke-tinta-800" />
      <circle cx="50" cy="50" r={radio} fill="none" strokeWidth="9" strokeLinecap="round"
        strokeDasharray={`${lleno} ${largo}`} className={`${tono} motion-safe:transition-[stroke-dasharray] motion-safe:duration-500`} />
    </svg>
    <span className="absolute inset-0 grid place-items-center text-lg font-semibold tabular-nums text-tinta-900 dark:text-tinta-50">
      {porcentaje(tasa)}
    </span>
  </div>
}

/** Barras horizontales, la más larga al 100 %. */
function Barras({ filas, vacio }: { filas: TotalPorNombre[]; vacio: string }) {
  if (filas.length === 0) return <p className="text-sm text-tinta-500">{vacio}</p>
  const maximo = Math.max(...filas.map(f => f.total))
  return <ul className="space-y-3">{filas.map(f =>
    <li key={f.id ?? f.name}>
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="truncate text-tinta-700 dark:text-tinta-300">{f.name}</span>
        <span className="tabular-nums text-tinta-900 dark:text-tinta-100">{f.total}</span>
      </div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-tinta-100 dark:bg-tinta-800" role="progressbar"
        aria-label={f.name} aria-valuenow={f.total} aria-valuemin={0} aria-valuemax={maximo}>
        <div className="h-full rounded-full bg-marca-500 motion-safe:transition-[width] motion-safe:duration-500"
          style={{ width: `${maximo ? (f.total / maximo) * 100 : 0}%` }} />
      </div>
    </li>)}</ul>
}

export function Kpis() {
  const { token, puede } = useSesion()
  useTitulo('Indicadores')
  const inicial = rangoPorDefecto()
  const [desde, setDesde] = useState(inicial.desde)
  const [hasta, setHasta] = useState(inicial.hasta)
  const [sucursal, setSucursal] = useState('')
  const [sucursales, setSucursales] = useState<Sucursal[]>([])
  const [errorSucursales, setErrorSucursales] = useState<string | null>(null)
  // La respuesta lleva la clave de la consulta que la pidió: mientras no
  // coincida con los filtros actuales, la pantalla está cargando.
  const [respuesta, setRespuesta] = useState<{ clave: string; datos?: DatosKpis; error?: string } | null>(null)

  const autorizado = puede('reporting.kpi.read')
  const rangoInvertido = desde !== '' && hasta !== '' && desde > hasta
  const clave = `${desde}|${hasta}|${sucursal}`
  const cargando = autorizado && !rangoInvertido && desde !== '' && hasta !== '' && respuesta?.clave !== clave
  const datos = respuesta?.datos ?? null
  const error = errorSucursales ?? (respuesta?.clave === clave ? respuesta.error ?? null : null)

  useEffect(() => {
    if (!autorizado) return
    const c = new AbortController()
    listarSucursales({ token }, c.signal).then(setSucursales)
      .catch(e => { if (!(e instanceof DOMException)) setErrorSucursales(mensajeError(e)) })
    return () => c.abort()
  }, [token, autorizado])

  useEffect(() => {
    if (!autorizado || !desde || !hasta || rangoInvertido) return
    const c = new AbortController()
    verKpis({ from: desde, to: hasta, branch: sucursal || undefined }, { token }, c.signal)
      .then(datos => setRespuesta({ clave, datos }))
      .catch(e => { if (!(e instanceof DOMException)) setRespuesta({ clave, error: mensajeError(e) }) })
    return () => c.abort()
  }, [token, autorizado, desde, hasta, sucursal, rangoInvertido, clave])

  if (!autorizado) {
    return <main className="mx-auto max-w-6xl px-5 py-8">
      <ErrorCatalogo mensaje="No tienes permiso para ver los indicadores de la organización." />
    </main>
  }

  const kpis = datos && !datos.plataforma ? datos : null
  const sinActividad = kpis && kpis.demand.total === 0 && kpis.occupancy.offered === 0

  return <main className="mx-auto max-w-6xl space-y-6 px-5 py-8 sm:py-10">
    <div className="surgir">
      <p className="text-sm font-medium text-marca-700 dark:text-marca-400">Organización</p>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight text-tinta-900 dark:text-tinta-50">Indicadores</h1>
      <p className="mt-1.5 max-w-2xl text-[0.9375rem] text-tinta-500">
        Ocupación de la agenda, inasistencia, demanda e ingresos por fichas en el rango elegido.
      </p>
    </div>

    <div className="grid gap-3 sm:grid-cols-3">
      <CampoSeleccion etiqueta="Desde">
        <input type="date" className={INPUT} value={desde} max={hasta || undefined} onChange={e => setDesde(e.target.value)} />
      </CampoSeleccion>
      <CampoSeleccion etiqueta="Hasta">
        <input type="date" className={INPUT} value={hasta} min={desde || undefined} onChange={e => setHasta(e.target.value)} />
      </CampoSeleccion>
      <CampoSeleccion etiqueta="Sucursal">
        <select className={INPUT} value={sucursal} onChange={e => setSucursal(e.target.value)}>
          <option value="">Todas las sucursales</option>
          {sucursales.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </CampoSeleccion>
    </div>

    {rangoInvertido && <ErrorCatalogo mensaje="La fecha de inicio no puede ser posterior a la fecha final." />}
    {error && <ErrorCatalogo mensaje={error} />}
    {cargando && !kpis && <p role="status" className="text-sm text-tinta-500">Calculando indicadores…</p>}

    {kpis && <div className={`space-y-5 ${cargando ? 'opacity-60' : ''}`} aria-busy={cargando}>
      {sinActividad && <p className="rounded-xl border border-tinta-200 px-4 py-3 text-sm text-tinta-500 dark:border-tinta-800">
        No hay agendas ni fichas en este rango. Prueba con otras fechas u otra sucursal.</p>}

      <div className="grid gap-5 lg:grid-cols-3">
        <Bloque titulo="Ocupación de la agenda">
          <div className="flex items-center gap-5">
            <Anillo tasa={kpis.occupancy.rate} etiqueta="Ocupación" tono="stroke-marca-500" />
            <div className="space-y-3">
              <Cifra valor={kpis.occupancy.booked} etiqueta="Espacios ocupados" />
              <Cifra valor={kpis.occupancy.offered} etiqueta="Espacios ofrecidos" />
            </div>
          </div>
        </Bloque>

        <Bloque titulo="Inasistencia">
          <div className="flex items-center gap-5">
            <Anillo tasa={kpis.no_show.rate} etiqueta="Inasistencia" tono="stroke-espera-600" />
            <div className="space-y-3">
              <Cifra valor={kpis.no_show.missed} etiqueta="Fichas ausentes" tono={kpis.no_show.rate !== null && kpis.no_show.rate >= 0.15 ? 'espera' : 'normal'} />
              <Cifra valor={kpis.no_show.expected} etiqueta="Debían atenderse" />
            </div>
          </div>
          <p className="mt-4 text-xs text-tinta-500">Las fichas canceladas a tiempo no cuentan como inasistencia.</p>
        </Bloque>

        <Bloque titulo="Ingresos por fichas">
          {kpis.revenue.by_currency.length === 0
            ? <p className="text-sm text-tinta-500">No hay pagos cobrados en este rango.</p>
            : <div className="space-y-4">{kpis.revenue.by_currency.map(m =>
              <Cifra key={m.currency} tono="marca" valor={dinero(m.total, m.currency)}
                etiqueta={`${m.payments} ${m.payments === 1 ? 'pago cobrado' : 'pagos cobrados'}`} />)}</div>}
        </Bloque>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Bloque titulo="Demanda por sucursal"
          accion={<span className="text-sm tabular-nums text-tinta-500">{kpis.demand.total} fichas</span>}>
          <Barras filas={kpis.demand.by_branch} vacio="No hubo fichas en este rango." />
        </Bloque>

        <Bloque titulo="Demanda por especialidad">
          <Barras filas={kpis.demand.by_specialty} vacio="No hubo fichas en este rango." />
          <p className="mt-4 text-xs text-tinta-500">
            Un profesional con varias especialidades suma en cada una, así que el total por
            especialidad puede superar las {kpis.demand.total} fichas.</p>
        </Bloque>
      </div>

      {kpis.revenue.by_branch.length > 0 && <Bloque titulo="Ingresos por sucursal">
        <ul className="divide-y divide-tinta-200 dark:divide-tinta-800">{kpis.revenue.by_branch.map(i =>
          <li key={`${i.id}-${i.currency}`} className="flex items-baseline justify-between gap-3 py-2.5 text-sm">
            <span className="text-tinta-700 dark:text-tinta-300">{i.name}</span>
            <span className="tabular-nums font-medium text-tinta-900 dark:text-tinta-100">{dinero(i.total, i.currency)}</span>
          </li>)}</ul>
      </Bloque>}
    </div>}
  </main>
}
