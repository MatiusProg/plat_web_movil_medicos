/**
 * US-35 — Riesgo de inasistencia de las fichas futuras.
 *
 * Arriba, el estado del modelo vigente (cuándo se entrenó, con cuántos datos y
 * si mejora a la línea base «siempre asiste»); debajo, las fichas de los
 * próximos días con su nivel de riesgo y los factores que más pesaron. Todo
 * sale de `api/riesgo.ts`.
 *
 * Si no hay un modelo que supere la línea base, **no se muestra ningún
 * listado**: sin un modelo confiable un nivel de riesgo sería inventado, así
 * que la pantalla sólo explica por qué no hay (`reason` / `message`).
 *
 * El nivel se ve con texto e icono además del color, para que no dependa de
 * distinguir colores. La función es del plan Premium: ante un 403 `plan_limit`
 * se muestra el aviso del backend en lugar del contenido.
 */
import { useEffect, useState, type ReactNode } from 'react'
import { listarSucursales, type Sucursal } from '@/api/catalogo'
import { ETIQUETA_ESTADO_FICHA } from '@/api/fichas'
import type { Pagina } from '@/api/paginacion'
import {
  ETIQUETA_NIVEL, esErrorDePlan, listarRiesgo, verModeloRiesgo, listarVersionesRiesgo,
  type EstadoModelo, type FichaEnRiesgo, type MetricasModelo, type NivelRiesgo, type VersionRiesgo,
} from '@/api/riesgo'
import { IconoCandado } from '@/componentes/iconos'
import { Paginador } from '@/componentes/Paginador'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'
import { CampoSeleccion, ErrorCatalogo, INPUT, PANEL, mensajeError } from './catalogo_comun'

const PERMISO = 'appointments.noshow.read'
const DIAS_POR_DEFECTO = 14

const aIso = (fecha: Date) => fecha.toLocaleDateString('en-CA')

function rangoPorDefecto() {
  const desde = new Date()
  const hasta = new Date()
  hasta.setDate(desde.getDate() + DIAS_POR_DEFECTO)
  return { desde: aIso(desde), hasta: aIso(hasta) }
}

const decimal = (n: number) => n.toLocaleString('es-BO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const porcentaje = (fraccion: number, decimales = 0) =>
  `${(fraccion * 100).toLocaleString('es-BO', { maximumFractionDigits: decimales })} %`
const cantidad = (n: number) => n.toLocaleString('es-BO')
const fechaLarga = (iso: string) =>
  new Date(iso).toLocaleDateString('es-BO', { day: 'numeric', month: 'long', year: 'numeric' })
const fechaHora = (iso: string) =>
  new Date(iso).toLocaleString('es-BO', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })

/** Un error ya listo para mostrar; `plan` distingue el aviso de plan del error común. */
interface ErrorPantalla { mensaje: string; plan: boolean }

const aErrorPantalla = (e: unknown): ErrorPantalla => ({ mensaje: mensajeError(e), plan: esErrorDePlan(e) })

// --- Insignia de nivel -------------------------------------------------------

const TONO_NIVEL: Record<NivelRiesgo, string> = {
  low: 'border-marca-200 bg-marca-50 text-marca-800 dark:border-marca-800 dark:bg-marca-950 dark:text-marca-200',
  medium: 'border-espera-200 bg-espera-50 text-espera-700 dark:border-espera-600/40 dark:bg-espera-600/10 dark:text-espera-200',
  high: 'border-alerta-200 bg-alerta-50 text-alerta-700 dark:border-alerta-500/40 dark:bg-alerta-500/10 dark:text-alerta-200',
}

/** Tres formas distintas, no sólo tres colores: círculo con visto, triángulo y octágono. */
function IconoNivel({ nivel }: { nivel: NivelRiesgo }) {
  const trazo = { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2,
    strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, className: 'size-4 shrink-0', 'aria-hidden': true }
  if (nivel === 'low') return <svg {...trazo}><circle cx="12" cy="12" r="9" /><path d="m8.5 12.3 2.5 2.5 4.5-5" /></svg>
  if (nivel === 'medium') return <svg {...trazo}><path d="M12 3.5 21.5 20h-19L12 3.5Z" /><path d="M12 10v4.5M12 17.4v.1" /></svg>
  return <svg {...trazo}><path d="M8.2 3h7.6L21 8.2v7.6L15.8 21H8.2L3 15.8V8.2L8.2 3Z" /><path d="M12 7.5v5.5M12 16.4v.1" /></svg>
}

function InsigniaNivel({ nivel }: { nivel: NivelRiesgo }) {
  return <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-1 text-xs font-semibold ${TONO_NIVEL[nivel]}`}>
    <IconoNivel nivel={nivel} />
    {ETIQUETA_NIVEL[nivel]}
  </span>
}

/** Los factores con flecha, y el sentido dicho también en texto para lectores de pantalla. */
function Factores({ factores }: { factores: FichaEnRiesgo['factors'] }) {
  if (factores.length === 0) return <span className="text-tinta-400">—</span>
  return <ul className="space-y-1">{factores.map(f => {
    const sube = f.direction === 'up'
    return <li key={f.key} className="flex items-start gap-1.5 text-sm text-tinta-700 dark:text-tinta-300">
      <span aria-hidden="true" className={`font-semibold ${sube ? 'text-espera-700 dark:text-espera-200' : 'text-marca-700 dark:text-marca-300'}`}>
        {sube ? '↑' : '↓'}</span>
      <span className="sr-only">{sube ? 'Aumenta el riesgo: ' : 'Reduce el riesgo: '}</span>
      <span>{f.label}</span>
    </li>
  })}</ul>
}

// --- Tarjeta del modelo ------------------------------------------------------

/** «Brier 0,08 vs 0,11 de siempre-asiste», o lo que se pueda decir con lo que haya. */
function ComparacionBrier({ metricas }: { metricas: MetricasModelo }) {
  if (metricas.brier === null || metricas.brier_baseline === null) return null
  return <>Error de las probabilidades (Brier, más bajo es mejor): {decimal(metricas.brier)} contra{' '}
    {decimal(metricas.brier_baseline)} de «siempre asiste».</>
}

function TarjetaModelo({ estado, cargando }: { estado: EstadoModelo | null; cargando: boolean }) {
  if (!estado) {
    return <section className={PANEL} aria-label="Modelo de predicción">
      <p role="status" className="text-sm text-tinta-500">{cargando ? 'Consultando el modelo…' : ''}</p>
    </section>
  }
  const { model, rejected, reason, message } = estado

  if (reason !== null || !model) {
    const aviso = {
      sin_datos: 'Todavía no hay suficientes datos',
      sin_modelo: 'Todavía no hay un modelo entrenado',
      no_supera_base: 'El modelo no supera la línea base',
    }[reason ?? 'sin_modelo']
    const ambar = reason === 'no_supera_base'
    return <section aria-label="Modelo de predicción" className={`rounded-2xl border p-5 ${ambar
      ? 'border-espera-200 bg-espera-50 dark:border-espera-600/40 dark:bg-espera-600/10'
      : 'border-tinta-200 bg-tinta-50 dark:border-tinta-800 dark:bg-tinta-900/50'}`}>
      <h2 className="font-semibold text-tinta-900 dark:text-tinta-100">{aviso}</h2>
      <p className="mt-1.5 max-w-3xl text-sm leading-6 text-tinta-700 dark:text-tinta-300">
        {message ?? 'Por ahora no se puede estimar el riesgo de las fichas.'}</p>
      {reason === 'no_supera_base' && rejected && <p className="mt-3 max-w-3xl text-xs leading-5 text-tinta-600 dark:text-tinta-400">
        Último modelo probado: versión {rejected.version}, entrenado el {fechaLarga(rejected.trained_at)}.{' '}
        <ComparacionBrier metricas={rejected.metrics} /> No se usa para calificar fichas.</p>}
      <p className="mt-3 text-xs text-tinta-500">Mientras tanto no se muestra ningún riesgo: sería un número sin respaldo.</p>
    </section>
  }

  const m = model.metrics
  return <section className={PANEL} aria-label="Modelo de predicción">
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <h2 className="font-semibold text-tinta-900 dark:text-tinta-100">Modelo vigente · versión {model.version}</h2>
      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${model.beats_baseline
        ? 'bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-300'
        : 'bg-espera-50 text-espera-700 dark:bg-espera-600/10 dark:text-espera-200'}`}>
        {model.beats_baseline ? '✓ Mejor que la línea base' : 'No mejora la línea base'}</span>
    </div>

    <dl className="mt-4 grid gap-x-8 gap-y-4 sm:grid-cols-3">
      <Dato titulo="Entrenado el">{fechaLarga(model.trained_at)}</Dato>
      <Dato titulo="Datos usados">
        {cantidad(model.n_train)} fichas para aprender y {cantidad(model.n_test)} para comprobar</Dato>
      <Dato titulo="Tasa base de inasistencia">
        {porcentaje(model.base_rate, 1)} de las fichas pasadas terminaron en ausencia</Dato>
    </dl>

    <div className="mt-5 space-y-2 border-t border-tinta-200 pt-4 text-sm leading-6 text-tinta-700 dark:border-tinta-800 dark:text-tinta-300">
      <p className="text-xs font-medium text-tinta-500">
        La línea base es la regla más simple: decir que todos los pacientes van a asistir.</p>
      {(m.brier !== null && m.brier_baseline !== null) && <p><ComparacionBrier metricas={m} /></p>}
      {m.accuracy_baseline !== null && <p>
        Decir «siempre asiste» acierta {porcentaje(m.accuracy_baseline, 1)} de las veces, pero no avisa de ninguna ausencia.</p>}
      {m.auc !== null && <p>
        Ordena bien las fichas (AUC {decimal(m.auc)}; 0,50 sería al azar y 1,00 perfecto).</p>}
      {(m.precision_high !== null || m.recall_high !== null) && <p>
        {m.precision_high !== null && <>De las fichas marcadas con riesgo alto, {porcentaje(m.precision_high)} faltaron de verdad. </>}
        {m.recall_high !== null && <>Esas fichas cubren {porcentaje(m.recall_high)} de todas las ausencias.</>}</p>}
      <p className="text-xs text-tinta-500">
        Riesgo medio desde {porcentaje(model.cutoffs.medium)} de probabilidad y riesgo alto desde {porcentaje(model.cutoffs.high)}.
        Es una estimación para priorizar recordatorios, no una certeza sobre cada paciente.</p>
    </div>
  </section>
}

function Dato({ titulo, children }: { titulo: string; children: ReactNode }) {
  return <div>
    <dt className="text-xs font-medium text-tinta-500">{titulo}</dt>
    <dd className="mt-0.5 text-sm text-tinta-900 dark:text-tinta-100">{children}</dd>
  </div>
}

// --- Aviso de plan -----------------------------------------------------------

function AvisoPlan({ mensaje }: { mensaje: string }) {
  return <div role="alert" className="surgir flex gap-3 rounded-2xl border border-espera-200 bg-espera-50 p-5 text-espera-700 dark:border-espera-600/40 dark:bg-espera-600/10 dark:text-espera-200">
    <IconoCandado className="mt-0.5 size-5 shrink-0" />
    <div className="space-y-1">
      <p className="font-semibold">Esta función no está incluida en tu plan</p>
      <p className="text-sm leading-6">{mensaje}</p>
    </div>
  </div>
}

// --- Página ------------------------------------------------------------------

export function RiesgoInasistencia() {
  const { token, puede } = useSesion()
  useTitulo('Riesgo de inasistencia')
  const inicial = rangoPorDefecto()
  const [desde, setDesde] = useState(inicial.desde)
  const [hasta, setHasta] = useState(inicial.hasta)
  const [sucursal, setSucursal] = useState('')
  const [nivel, setNivel] = useState<'' | NivelRiesgo>('')
  const [pagina, setPagina] = useState(1)
  const [sucursales, setSucursales] = useState<Sucursal[]>([])
  const [errorSucursales, setErrorSucursales] = useState<string | null>(null)
  const [modelo, setModelo] = useState<{ datos?: EstadoModelo; error?: ErrorPantalla } | null>(null)
  const [versiones, setVersiones] = useState<VersionRiesgo[]>([])
  // La respuesta lleva la clave de la consulta que la pidió: mientras no
  // coincida con los filtros actuales, el listado está cargando.
  const [respuesta, setRespuesta] = useState<{ clave: string; datos?: Pagina<FichaEnRiesgo>; error?: ErrorPantalla } | null>(null)

  const autorizado = puede(PERMISO)
  const rangoInvertido = desde !== '' && hasta !== '' && desde > hasta
  const clave = `${desde}|${hasta}|${sucursal}|${nivel}|${pagina}`
  // Sólo se pide el listado cuando hay un modelo vigente que supera la línea base.
  const hayModelo = Boolean(modelo?.datos?.model) && modelo?.datos?.reason === null
  const puedeListar = autorizado && hayModelo && desde !== '' && hasta !== '' && !rangoInvertido
  const cargandoModelo = autorizado && modelo === null
  const cargandoLista = puedeListar && respuesta?.clave !== clave
  const lista = respuesta?.datos ?? null
  const errorLista = respuesta?.clave === clave ? respuesta.error ?? null : null
  const errorPlan = modelo?.error?.plan ? modelo.error : errorLista?.plan ? errorLista : null
  const errorComun = errorSucursales ?? (errorPlan ? null : modelo?.error?.mensaje ?? errorLista?.mensaje ?? null)

  useEffect(() => {
    if (!autorizado) return
    const c = new AbortController()
    verModeloRiesgo({ token }, c.signal)
      .then(datos => setModelo({ datos }))
      .catch(e => { if (!(e instanceof DOMException)) setModelo({ error: aErrorPantalla(e) }) })
    return () => c.abort()
  }, [token, autorizado])

  useEffect(() => {
    if (!autorizado) return
    const c = new AbortController()
    listarVersionesRiesgo({ token }, c.signal)
      .then(data => setVersiones(data.results))
      .catch(() => { /* Modelo no disponible o sin permiso/plan: no mostrar versiones. */ })
    return () => c.abort()
  }, [token, autorizado])

  useEffect(() => {
    if (!autorizado) return
    const c = new AbortController()
    listarSucursales({ token }, c.signal).then(setSucursales)
      .catch(e => { if (!(e instanceof DOMException)) setErrorSucursales(mensajeError(e)) })
    return () => c.abort()
  }, [token, autorizado])

  useEffect(() => {
    if (!puedeListar) return
    const c = new AbortController()
    listarRiesgo(
      { from: desde, to: hasta, branch: sucursal || undefined, level: nivel || undefined, page: pagina },
      { token }, c.signal,
    )
      .then(datos => setRespuesta({ clave, datos }))
      .catch(e => { if (!(e instanceof DOMException)) setRespuesta({ clave, error: aErrorPantalla(e) }) })
    return () => c.abort()
  }, [token, puedeListar, desde, hasta, sucursal, nivel, pagina, clave])

  if (!autorizado) {
    return <main className="mx-auto max-w-6xl px-5 py-8">
      <ErrorCatalogo mensaje="No tienes permiso para ver el riesgo de inasistencia." />
    </main>
  }

  // Al cambiar un filtro se vuelve a la primera página.
  const filtro = <T,>(poner: (v: T) => void) => (valor: T) => { poner(valor); setPagina(1) }
  const sinPlan = errorPlan !== null
  const filas = lista?.results ?? []

  return <main className="mx-auto max-w-6xl space-y-6 px-5 py-8 sm:py-10">
    <div className="surgir">
      <p className="text-sm font-medium text-marca-700 dark:text-marca-400">Organización</p>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight text-tinta-900 dark:text-tinta-50">Riesgo de inasistencia</h1>
      <p className="mt-1.5 max-w-2xl text-[0.9375rem] text-tinta-500">
        Qué fichas de los próximos días tienen más probabilidad de que el paciente no llegue,
        para priorizar recordatorios y confirmaciones.
      </p>
    </div>

    {errorComun && <ErrorCatalogo mensaje={errorComun} />}
    {errorPlan && <AvisoPlan mensaje={errorPlan.mensaje} />}

    {!sinPlan && <>
      <TarjetaModelo estado={modelo?.datos ?? null} cargando={cargandoModelo} />
      {versiones.length > 0 && <section className={PANEL} aria-label="Historial de versiones No-Show">
        <h2 className="font-semibold">Historial de reentrenamientos</h2>
        <div className="mt-3 overflow-x-auto"><table className="w-full text-left text-sm">
          <thead><tr><th className="p-2">Versión</th><th className="p-2">Estado</th><th className="p-2">Entrenamiento</th><th className="p-2">Brier</th><th className="p-2">Comparación con vigente anterior</th></tr></thead>
          <tbody>{versiones.map(v => <tr key={v.version} className="border-t border-tinta-200 dark:border-tinta-800">
            <td className="p-2">v{v.version}</td><td className="p-2">{({ active: 'Vigente', candidate: 'Candidato', rejected: 'Rechazado', retired: 'Retirado' } as const)[v.status]}</td>
            <td className="p-2">{fechaLarga(v.trained_at)}</td><td className="p-2">{v.brier === null ? '—' : decimal(v.brier)}</td>
            <td className="p-2">{v.comparison?.incumbent_brier !== undefined && v.comparison.candidate_brier !== undefined
              ? `Anterior ${decimal(v.comparison.incumbent_brier)} · Candidato ${decimal(v.comparison.candidate_brier)} (mismas ${v.comparison.holdout_n} fichas)`
              : v.comparison?.reason ?? 'Entrenamiento inicial'}</td>
          </tr>)}</tbody>
        </table></div>
      </section>}

      {hayModelo && <>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <CampoSeleccion etiqueta="Desde">
            <input type="date" className={INPUT} value={desde} max={hasta || undefined} onChange={e => filtro(setDesde)(e.target.value)} />
          </CampoSeleccion>
          <CampoSeleccion etiqueta="Hasta">
            <input type="date" className={INPUT} value={hasta} min={desde || undefined} onChange={e => filtro(setHasta)(e.target.value)} />
          </CampoSeleccion>
          <CampoSeleccion etiqueta="Sucursal">
            <select className={INPUT} value={sucursal} onChange={e => filtro(setSucursal)(e.target.value)}>
              <option value="">Todas las sucursales</option>
              {sucursales.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </CampoSeleccion>
          <CampoSeleccion etiqueta="Nivel de riesgo">
            <select className={INPUT} value={nivel} onChange={e => filtro(setNivel)(e.target.value as '' | NivelRiesgo)}>
              <option value="">Todos los niveles</option>
              {(['high', 'medium', 'low'] as const).map(n => <option key={n} value={n}>{ETIQUETA_NIVEL[n]}</option>)}
            </select>
          </CampoSeleccion>
        </div>

        {rangoInvertido && <ErrorCatalogo mensaje="La fecha de inicio no puede ser posterior a la fecha final." />}

        <div aria-live="polite">
          {cargandoLista && !lista && <p role="status" className="text-sm text-tinta-500">Calculando el riesgo de las fichas…</p>}
          {lista && !cargandoLista && !errorLista && <p className="sr-only">
            {lista.count === 0 ? 'Sin resultados.' : `${lista.count} fichas encontradas.`}</p>}
        </div>

        {lista && <section className={`${PANEL} ${cargandoLista ? 'opacity-60' : ''}`} aria-label="Fichas con su riesgo" aria-busy={cargandoLista}>
          {filas.length === 0
            ? <p className="py-6 text-center text-sm text-tinta-500">
                No hay fichas futuras con estos filtros. Prueba con otras fechas, otra sucursal u otro nivel.</p>
            : <>
              <TablaRiesgo filas={filas} />
              <ListaRiesgo filas={filas} />
              <Paginador pagina={pagina} total={lista.count} cargando={cargandoLista} onCambiar={setPagina} />
            </>}
        </section>}
      </>}
    </>}
  </main>
}

const CELDA = 'px-3 py-3 align-top'

/** En pantallas anchas, una tabla. */
function TablaRiesgo({ filas }: { filas: FichaEnRiesgo[] }) {
  return <div className="hidden overflow-x-auto md:block">
    <table className="w-full text-left text-sm">
      <caption className="sr-only">Fichas futuras ordenadas con su nivel de riesgo de inasistencia</caption>
      <thead className="border-b border-tinta-200 text-xs font-medium text-tinta-500 dark:border-tinta-800">
        <tr>
          <th scope="col" className={CELDA}>Paciente</th>
          <th scope="col" className={CELDA}>Profesional y sucursal</th>
          <th scope="col" className={CELDA}>Fecha y hora</th>
          <th scope="col" className={CELDA}>Riesgo</th>
          <th scope="col" className={CELDA}>Qué influye</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-tinta-200 dark:divide-tinta-800">{filas.map(f =>
        <tr key={f.appointment_id}>
          <td className={`${CELDA} font-medium text-tinta-900 dark:text-tinta-100`}>{f.patient_name}</td>
          <td className={`${CELDA} text-tinta-700 dark:text-tinta-300`}>
            <p>{f.practitioner_name}</p>
            <p className="text-xs text-tinta-500">{f.branch_name}</p>
          </td>
          <td className={`${CELDA} text-tinta-700 dark:text-tinta-300`}>
            <p className="tabular-nums">{fechaHora(f.starts_at)}</p>
            <p className="text-xs text-tinta-500">{ETIQUETA_ESTADO_FICHA[f.status] ?? f.status}</p>
          </td>
          <td className={CELDA}>
            <InsigniaNivel nivel={f.level} />
            <p className="mt-1.5 text-sm tabular-nums text-tinta-700 dark:text-tinta-300">{porcentaje(f.probability)} de probabilidad</p>
          </td>
          <td className={CELDA}><Factores factores={f.factors} /></td>
        </tr>)}
      </tbody>
    </table>
  </div>
}

/** En móvil, una tarjeta por ficha. */
function ListaRiesgo({ filas }: { filas: FichaEnRiesgo[] }) {
  return <ul className="space-y-3 md:hidden" aria-label="Fichas con su riesgo">{filas.map(f =>
    <li key={f.appointment_id} className="rounded-xl border border-tinta-200 p-4 dark:border-tinta-800">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <InsigniaNivel nivel={f.level} />
        <span className="text-sm font-semibold tabular-nums text-tinta-900 dark:text-tinta-100">{porcentaje(f.probability)}</span>
      </div>
      <p className="mt-3 font-medium text-tinta-900 dark:text-tinta-100">{f.patient_name}</p>
      <p className="text-sm text-tinta-700 dark:text-tinta-300">{f.practitioner_name} · {f.branch_name}</p>
      <p className="mt-1 text-sm tabular-nums text-tinta-500">
        {fechaHora(f.starts_at)} · {ETIQUETA_ESTADO_FICHA[f.status] ?? f.status}</p>
      {f.factors.length > 0 && <div className="mt-3 border-t border-tinta-200 pt-3 dark:border-tinta-800">
        <p className="mb-1 text-xs font-medium text-tinta-500">Qué influye</p>
        <Factores factores={f.factors} />
      </div>}
    </li>)}
  </ul>
}
