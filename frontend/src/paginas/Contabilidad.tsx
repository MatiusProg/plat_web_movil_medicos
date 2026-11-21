/**
 * US-50 — Contabilidad: ingresos, devoluciones, comisión, honorarios, gastos y
 * utilidad, por moneda, agrupables y exportables, con preguntas por voz.
 *
 * Todo el cálculo es del backend (`reporting/finance.py`): acá solo se muestra.
 * Los montos llegan como texto y van por moneda; nunca se suman entre monedas.
 * Los gráficos son SVG propio, igual que en Indicadores, y heredan el tema.
 *
 * Es de los planes Pro y Premium: ante un 403 `plan_limit` se explica en vez de
 * mostrar una pantalla rota.
 */
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { listarProfesionalesTodos, listarSucursales, type ProfesionalTarjeta, type Sucursal } from '@/api/catalogo'
import {
  AGRUPACIONES, CATEGORIAS, borrarGasto, crearGasto, descargarContabilidad, guardarComision,
  listarGastos, preguntarPorVoz, verComision, verResumen, verSerie,
  type Agrupacion, type Campo, type Categoria, type Cifras, type FormatoArchivo, type Gasto,
  type PorMoneda, type RespuestaDeVoz, type Resumen, type Serie,
} from '@/api/finanzas'
import { esErrorDePlan } from '@/api/riesgo'
import { Boton } from '@/componentes/Boton'
import { EntradaDeVoz } from '@/componentes/EntradaDeVoz'
import { Bloque } from '@/componentes/Indicadores'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'
import { CampoSeleccion, ErrorCatalogo, INPUT, SECONDARY, mensajeError } from './catalogo_comun'

const aIso = (fecha: Date) => fecha.toLocaleDateString('en-CA')

function mesActual() {
  const hoy = new Date()
  return { desde: aIso(new Date(hoy.getFullYear(), hoy.getMonth(), 1)), hasta: aIso(hoy) }
}

const dinero = (valor: string | null, moneda: string) =>
  valor === null ? '—' : `${Number(valor).toLocaleString('es-BO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${moneda}`

const MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
const nombreDeMes = (aaaamm: string) => {
  const [anio, mes] = aaaamm.split('-')
  return `${MESES_CORTOS[Number(mes) - 1]} ${anio.slice(2)}`
}

type Pestana = 'resumen' | 'gastos' | 'ajustes'

// Las tarjetas. `suma` dice si que suba es bueno (ingresos, utilidad) o malo.
const TARJETAS: { campo: Campo; titulo: string; suma: boolean }[] = [
  { campo: 'ingresos', titulo: 'Ingresos', suma: true },
  { campo: 'devoluciones', titulo: 'Devoluciones', suma: false },
  { campo: 'comision', titulo: 'Comisión de la pasarela', suma: false },
  { campo: 'honorarios', titulo: 'Honorarios', suma: false },
  { campo: 'gastos', titulo: 'Gastos', suma: false },
  { campo: 'utilidad', titulo: 'Utilidad', suma: true },
]

/** La variación contra el período anterior, con flecha y texto: no solo color. */
function Variacion({ porcentaje, suma }: { porcentaje: string | null | undefined; suma: boolean }) {
  if (porcentaje === undefined) return null
  if (porcentaje === null) return <p className="mt-1 text-xs text-tinta-500">Sin período anterior con qué comparar</p>
  const numero = Number(porcentaje)
  if (numero === 0) return <p className="mt-1 text-xs text-tinta-500">Igual que el período anterior</p>
  const bueno = (numero > 0) === suma
  return <p className={`mt-1 text-xs font-medium ${bueno ? 'text-marca-700 dark:text-marca-400' : 'text-alerta-600 dark:text-alerta-500'}`}>
    <span aria-hidden="true">{numero > 0 ? '▲' : '▼'}</span>{' '}
    {Math.abs(numero).toLocaleString('es-BO', { maximumFractionDigits: 1 })} % {numero > 0 ? 'más' : 'menos'} que el período anterior
  </p>
}

function Tarjetas({ moneda }: { moneda: PorMoneda }) {
  const t = moneda.totals
  return <div className="space-y-3">
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {TARJETAS.map(({ campo, titulo, suma }) =>
        <div key={campo} className={`rounded-2xl border p-4 ${campo === 'utilidad'
          ? 'border-marca-500/40 bg-marca-50/50 dark:bg-marca-500/10'
          : 'border-tinta-200 bg-white dark:border-tinta-800 dark:bg-tinta-900/50'}`}>
          <p className="text-sm text-tinta-500">{titulo}</p>
          <p className={`mt-1 text-2xl font-semibold tabular-nums ${campo === 'utilidad' && Number(t.utilidad) < 0
            ? 'text-alerta-600 dark:text-alerta-500' : 'text-tinta-900 dark:text-tinta-50'}`}>
            {dinero(t[campo], moneda.currency)}</p>
          {/* Cero contra cero no es una comparación: no se repite el aviso. */}
          {!(Number(t[campo]) === 0 && Number(moneda.compare?.previous_totals[campo]) === 0) &&
            <Variacion porcentaje={moneda.compare?.change_percent[campo]} suma={suma} />}
        </div>)}
    </div>
    <p className="text-sm text-tinta-500">
      {t.pagos} {t.pagos === 1 ? 'pago cobrado' : 'pagos cobrados'}
      {t.ticket_promedio !== null && <> · ticket promedio {dinero(t.ticket_promedio, moneda.currency)}</>}
      {' · '}Utilidad = ingresos − devoluciones − comisión − honorarios − gastos.
    </p>
  </div>
}

function TablaDeGrupos({ moneda, agrupar }: { moneda: PorMoneda; agrupar: Agrupacion }) {
  const etiqueta = AGRUPACIONES.find(a => a.valor === agrupar)?.etiqueta ?? ''
  const filas: { clave: string; nombre: string; cifras: Cifras }[] = [
    ...moneda.groups.map(g => ({ clave: g.key, nombre: g.label, cifras: g })),
    { clave: '__total', nombre: 'Total', cifras: moneda.totals },
  ]
  const columnas: { campo: Campo; titulo: string }[] = [
    { campo: 'ingresos', titulo: 'Ingresos' }, { campo: 'devoluciones', titulo: 'Devol.' },
    { campo: 'comision', titulo: 'Comisión' }, { campo: 'honorarios', titulo: 'Honorarios' },
    { campo: 'gastos', titulo: 'Gastos' }, { campo: 'utilidad', titulo: 'Utilidad' },
  ]
  return <div className="overflow-x-auto">
    <table className="w-full text-left text-sm">
      <caption className="sr-only">{moneda.currency} por {etiqueta.toLowerCase()}</caption>
      <thead className="text-tinta-500">
        <tr>
          <th scope="col" className="py-2 pr-3 font-medium">{etiqueta}</th>
          {columnas.map(c => <th key={c.campo} scope="col" className="px-2 py-2 text-right font-medium">{c.titulo}</th>)}
        </tr>
      </thead>
      <tbody className="divide-y divide-tinta-200 text-tinta-800 dark:divide-tinta-800 dark:text-tinta-100">
        {filas.map(f => <tr key={f.clave} className={f.clave === '__total' ? 'font-semibold' : ''}>
          <th scope="row" className="py-2 pr-3 font-normal">{f.nombre}</th>
          {columnas.map(c => <td key={c.campo} className="px-2 py-2 text-right tabular-nums">
            {Number(f.cifras[c.campo]).toLocaleString('es-BO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>)}
        </tr>)}
      </tbody>
    </table>
  </div>
}

/** Ingresos y utilidad de los últimos 6 meses, barras de SVG. */
function GraficoDeSeisMeses({ serie, moneda }: { serie: Serie; moneda: string }) {
  const datos = serie.currencies.find(c => c.currency === moneda)
  if (!datos) return <p className="text-sm text-tinta-500">Sin movimientos en los últimos 6 meses.</p>
  const valores = datos.months.flatMap(m => [Number(m.ingresos), Number(m.utilidad)])
  const tope = Math.max(0, ...valores)
  const piso = Math.min(0, ...valores)
  const rango = tope - piso || 1
  const alto = 150
  const y = (v: number) => ((tope - v) / rango) * alto + 10
  const ancho = 100 / datos.months.length
  return <div>
    <svg viewBox="0 0 600 200" className="h-auto w-full" role="img"
      aria-label={`Ingresos y utilidad en ${moneda} de los últimos 6 meses`}>
      <line x1="0" x2="600" y1={y(0)} y2={y(0)} className="stroke-tinta-300 dark:stroke-tinta-700" />
      {datos.months.map((m, i) => {
        const x0 = (i * ancho * 6) + 14
        const barra = (valor: number, desplazo: number, clase: string, etiqueta: string) => {
          const alturaBarra = Math.abs(y(valor) - y(0))
          return <rect x={x0 + desplazo} y={valor >= 0 ? y(valor) : y(0)} width={34} height={alturaBarra} rx="3" className={clase}>
            <title>{`${nombreDeMes(m.month)} · ${etiqueta}: ${dinero(String(valor), moneda)}`}</title>
          </rect>
        }
        return <g key={m.month}>
          {barra(Number(m.ingresos), 0, 'fill-marca-500', 'Ingresos')}
          {barra(Number(m.utilidad), 38, 'fill-tinta-400 dark:fill-tinta-500', 'Utilidad')}
          <text x={x0 + 36} y="192" textAnchor="middle" className="fill-tinta-500 text-[11px]">{nombreDeMes(m.month)}</text>
        </g>
      })}
    </svg>
    <p className="mt-2 flex flex-wrap gap-x-4 text-xs text-tinta-500">
      <span><span aria-hidden="true" className="mr-1 inline-block size-2.5 rounded-sm bg-marca-500" />Ingresos</span>
      <span><span aria-hidden="true" className="mr-1 inline-block size-2.5 rounded-sm bg-tinta-400 dark:bg-tinta-500" />Utilidad</span>
    </p>
  </div>
}

export function Contabilidad() {
  const { token, puede } = useSesion()
  useTitulo('Contabilidad')
  const inicial = mesActual()
  const [pestana, setPestana] = useState<Pestana>('resumen')
  const [desde, setDesde] = useState(inicial.desde)
  const [hasta, setHasta] = useState(inicial.hasta)
  const [sucursal, setSucursal] = useState('')
  const [profesional, setProfesional] = useState('')
  const [agrupar, setAgrupar] = useState<Agrupacion | ''>('')
  const [comparar, setComparar] = useState(false)
  const [sucursales, setSucursales] = useState<Sucursal[]>([])
  const [profesionales, setProfesionales] = useState<ProfesionalTarjeta[]>([])
  const [respuesta, setRespuesta] = useState<{ clave: string; datos?: Resumen; serie?: Serie; error?: string; sinPlan?: boolean } | null>(null)
  const [voz, setVoz] = useState<RespuestaDeVoz | null>(null)
  const [preguntando, setPreguntando] = useState(false)
  const [errorVoz, setErrorVoz] = useState<string | null>(null)
  const [bajando, setBajando] = useState<FormatoArchivo | null>(null)
  const [errorArchivo, setErrorArchivo] = useState<string | null>(null)

  const autorizado = puede('finance.accounting.read')
  const puedeCargar = puede('finance.expense.manage')
  const rangoInvertido = desde !== '' && hasta !== '' && desde > hasta
  const filtros = useMemo(
    () => ({ desde, hasta, sucursal, profesional, agrupar, comparar }),
    [desde, hasta, sucursal, profesional, agrupar, comparar],
  )
  const clave = JSON.stringify(filtros)
  const listo = autorizado && !rangoInvertido && desde !== '' && hasta !== ''
  const cargando = listo && respuesta?.clave !== clave
  const actual = respuesta?.clave === clave ? respuesta : null

  useEffect(() => {
    if (!autorizado) return
    const c = new AbortController()
    listarSucursales({ token }, c.signal).then(setSucursales).catch(() => undefined)
    listarProfesionalesTodos({ token }, c.signal).then(setProfesionales).catch(() => undefined)
    return () => c.abort()
  }, [token, autorizado])

  useEffect(() => {
    if (!listo) return
    const c = new AbortController()
    Promise.all([verResumen(filtros, { token }, c.signal), verSerie(filtros, { token }, c.signal)])
      .then(([datos, serie]) => setRespuesta({ clave, datos, serie }))
      .catch(e => {
        if (e instanceof DOMException) return
        setRespuesta(esErrorDePlan(e) ? { clave, sinPlan: true } : { clave, error: mensajeError(e) })
      })
    return () => c.abort()
  }, [token, listo, clave, filtros])

  const preguntar = (texto: string) => {
    setPreguntando(true)
    setErrorVoz(null)
    preguntarPorVoz(texto, { token })
      .then(setVoz)
      .catch(e => setErrorVoz(mensajeError(e)))
      .finally(() => setPreguntando(false))
  }

  /** Lleva a la tabla lo que se entendió de la frase. */
  const verEnLaTabla = () => {
    const q = voz?.query
    if (!q) return
    setDesde(q.desde)
    setHasta(q.hasta)
    setAgrupar(q.agrupar ?? '')
    setSucursal(q.sede ?? '')
    setProfesional(q.profesional ?? '')
    setComparar(q.comparar)
    setPestana('resumen')
  }

  const bajar = (formato: FormatoArchivo) => {
    setBajando(formato)
    setErrorArchivo(null)
    descargarContabilidad(filtros, formato, { token })
      .catch(e => setErrorArchivo(mensajeError(e)))
      .finally(() => setBajando(null))
  }

  const periodo = (dias: 'hoy' | 'siete' | 'mes' | 'pasado' | 'tres') => {
    const hoy = new Date()
    if (dias === 'hoy') { setDesde(aIso(hoy)); setHasta(aIso(hoy)) }
    if (dias === 'siete') { setDesde(aIso(new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - 6))); setHasta(aIso(hoy)) }
    if (dias === 'mes') { const m = mesActual(); setDesde(m.desde); setHasta(m.hasta) }
    if (dias === 'pasado') {
      setDesde(aIso(new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1)))
      setHasta(aIso(new Date(hoy.getFullYear(), hoy.getMonth(), 0)))
    }
    if (dias === 'tres') { setDesde(aIso(new Date(hoy.getFullYear(), hoy.getMonth() - 2, 1))); setHasta(aIso(hoy)) }
  }

  if (!autorizado) {
    return <main className="mx-auto max-w-6xl px-5 py-8">
      <ErrorCatalogo mensaje="No tienes permiso para ver la contabilidad de la organización." />
    </main>
  }

  const datos = actual?.datos && !actual.datos.plataforma ? actual.datos : null
  const monedas = datos?.currencies ?? []

  return <main className="mx-auto max-w-6xl space-y-6 px-5 py-8 sm:py-10">
    <div className="surgir">
      <p className="text-sm font-medium text-marca-700 dark:text-marca-400">Organización</p>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight text-tinta-900 dark:text-tinta-50">Contabilidad</h1>
      <p className="mt-1.5 max-w-2xl text-[1.0625rem] text-tinta-500">
        Cuánto entra, cuánto se devuelve, cuánto va a la pasarela y a los profesionales, cuánto se gasta y qué queda.
      </p>
    </div>

    <Bloque titulo="Pregúntale a tus números">
      <EntradaDeVoz alEnviar={preguntar} ocupado={preguntando} etiqueta="Dicta o escribe tu pregunta"
        placeholder="Por ejemplo: cuánto ganamos este mes" />
      {errorVoz && <p role="alert" className="mt-3 text-sm text-alerta-600 dark:text-alerta-500">{errorVoz}</p>}
      {voz && <div className="mt-4 space-y-2" aria-live="polite">
        {voz.understood
          ? <p className="rounded-xl bg-marca-50 px-4 py-3 text-[1.0625rem] text-tinta-900 dark:bg-marca-500/10 dark:text-tinta-50">{voz.spoken_summary}</p>
          : <ul className="space-y-1 rounded-xl border border-tinta-200 px-4 py-3 text-sm text-tinta-600 dark:border-tinta-800 dark:text-tinta-300">
            {voz.unresolved.map(m => <li key={m}>{m}</li>)}</ul>}
        {voz.understood && <button type="button" className={SECONDARY} onClick={verEnLaTabla}>Ver en la tabla</button>}
      </div>}
    </Bloque>

    <div role="tablist" aria-label="Secciones de contabilidad" className="flex gap-1 border-b border-tinta-200 dark:border-tinta-800">
      {([['resumen', 'Resumen'], ['gastos', 'Gastos'], ['ajustes', 'Comisión']] as const).map(([id, etiqueta]) =>
        <button key={id} role="tab" type="button" aria-selected={pestana === id} onClick={() => setPestana(id)}
          className={`-mb-px border-b-2 px-4 py-2.5 text-sm font-medium transition ${pestana === id
            ? 'border-marca-500 text-marca-700 dark:text-marca-400'
            : 'border-transparent text-tinta-500 hover:text-tinta-800 dark:hover:text-tinta-200'}`}>{etiqueta}</button>)}
    </div>

    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
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
      <CampoSeleccion etiqueta="Médico">
        <select className={INPUT} value={profesional} onChange={e => setProfesional(e.target.value)}>
          <option value="">Todos los médicos</option>
          {profesionales.map(p => <option key={p.id} value={p.id}>{p.full_name}</option>)}
        </select>
      </CampoSeleccion>
    </div>
    <div className="flex flex-wrap items-center gap-2">
      {([['hoy', 'Hoy'], ['siete', '7 días'], ['mes', 'Este mes'], ['pasado', 'Mes pasado'], ['tres', '3 meses']] as const).map(([id, etiqueta]) =>
        <button key={id} type="button" className={SECONDARY} onClick={() => periodo(id)}>{etiqueta}</button>)}
    </div>

    {rangoInvertido && <ErrorCatalogo mensaje="La fecha de inicio no puede ser posterior a la fecha final." />}

    {pestana === 'resumen' && <>
      <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
        <CampoSeleccion etiqueta="Agrupar por">
          <select className={INPUT} value={agrupar} onChange={e => setAgrupar(e.target.value as Agrupacion | '')}>
            <option value="">Sin agrupar</option>
            {AGRUPACIONES.map(a => <option key={a.valor} value={a.valor}>{a.etiqueta}</option>)}
          </select>
        </CampoSeleccion>
        <label className="flex items-center gap-2 pb-3 text-sm text-tinta-700 dark:text-tinta-200">
          <input type="checkbox" checked={comparar} onChange={e => setComparar(e.target.checked)} className="size-4 accent-marca-500" />
          Comparar con el período anterior
        </label>
      </div>

      {actual?.sinPlan && <ErrorCatalogo mensaje="La contabilidad es de los planes Pro y Premium. Para tenerla, el centro tiene que cambiar a un plan superior." />}
      {actual?.error && <ErrorCatalogo mensaje={actual.error} />}
      {cargando && !datos && <p role="status" className="text-sm text-tinta-500">Calculando…</p>}

      {datos && <div className={`space-y-5 ${cargando ? 'opacity-60' : ''}`} aria-busy={cargando}>
        {monedas.length === 0 && <p className="rounded-xl border border-tinta-200 px-4 py-3 text-sm text-tinta-500 dark:border-tinta-800">
          No hay pagos ni gastos en este rango. Prueba con otras fechas o quita algún filtro.</p>}

        {monedas.map(m => <Bloque key={m.currency} titulo={`Cuentas en ${m.currency}`}>
          <div className="space-y-6">
            <Tarjetas moneda={m} />
            {datos.group_by && <TablaDeGrupos moneda={m} agrupar={datos.group_by} />}
          </div>
        </Bloque>)}

        {monedas.length > 0 && actual?.serie && <Bloque titulo="Últimos 6 meses">
          <div className="space-y-6">{monedas.map(m => <div key={m.currency}>
            {monedas.length > 1 && <p className="mb-1 text-sm font-medium text-tinta-700 dark:text-tinta-300">{m.currency}</p>}
            <GraficoDeSeisMeses serie={actual.serie!} moneda={m.currency} />
          </div>)}</div>
        </Bloque>}

        {monedas.length > 0 && <Bloque titulo="Exportar la tabla">
          <div className="flex flex-wrap gap-2">
            {(['pdf', 'xlsx', 'csv'] as const).map(f =>
              <button key={f} type="button" className={SECONDARY} disabled={bajando !== null} onClick={() => bajar(f)}>
                {bajando === f ? 'Preparando…' : f === 'xlsx' ? 'Excel' : f.toUpperCase()}</button>)}
          </div>
          {errorArchivo && <p role="alert" className="mt-3 text-sm text-alerta-600 dark:text-alerta-500">{errorArchivo}</p>}
        </Bloque>}
      </div>}
    </>}

    {pestana === 'gastos' && <PestanaGastos desde={desde} hasta={hasta} sucursal={sucursal} sucursales={sucursales}
      token={token} puedeCargar={puedeCargar} alCambiar={() => setRespuesta(null)} />}
    {pestana === 'ajustes' && <PestanaComision token={token} puedeCargar={puedeCargar} alCambiar={() => setRespuesta(null)} />}
  </main>
}

function PestanaGastos({ desde, hasta, sucursal, sucursales, token, puedeCargar, alCambiar }: {
  desde: string; hasta: string; sucursal: string; sucursales: Sucursal[]
  token: string | null | undefined; puedeCargar: boolean; alCambiar: () => void
}) {
  const [categoria, setCategoria] = useState<Categoria | ''>('')
  const [gastos, setGastos] = useState<Gasto[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [version, setVersion] = useState(0)
  const [guardando, setGuardando] = useState(false)
  const [aBorrar, setAborrar] = useState<string | null>(null)
  const [form, setForm] = useState({
    category: 'insumos' as Categoria, branch: '', amount: '', currency: 'BOB',
    spent_on: aIso(new Date()), note: '',
  })

  useEffect(() => {
    if (!desde || !hasta || desde > hasta) return
    const c = new AbortController()
    listarGastos({ desde, hasta, sucursal }, categoria, { token }, c.signal)
      .then(g => { setGastos(g); setError(null) })
      .catch(e => { if (!(e instanceof DOMException)) setError(mensajeError(e)) })
    return () => c.abort()
  }, [token, desde, hasta, sucursal, categoria, version])

  const cargar = (evento: FormEvent) => {
    evento.preventDefault()
    setGuardando(true)
    setError(null)
    crearGasto({
      category: form.category, branch: form.branch || null, amount: form.amount,
      currency: form.currency.trim().toUpperCase(), spent_on: form.spent_on, note: form.note.trim(),
    }, { token })
      .then(() => { setForm(f => ({ ...f, amount: '', note: '' })); setVersion(v => v + 1); alCambiar() })
      .catch(e => setError(mensajeError(e)))
      .finally(() => setGuardando(false))
  }

  const borrar = (id: string) => {
    borrarGasto(id, { token })
      .then(() => { setAborrar(null); setVersion(v => v + 1); alCambiar() })
      .catch(e => setError(mensajeError(e)))
  }

  const total = (gastos ?? []).reduce<Record<string, number>>((acc, g) => ({ ...acc, [g.currency]: (acc[g.currency] ?? 0) + Number(g.amount) }), {})

  return <div className="space-y-5">
    {puedeCargar && <Bloque titulo="Cargar un gasto">
      <form onSubmit={cargar} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <CampoSeleccion etiqueta="Categoría">
          <select className={INPUT} value={form.category} onChange={e => setForm({ ...form, category: e.target.value as Categoria })}>
            {CATEGORIAS.map(c => <option key={c.valor} value={c.valor}>{c.etiqueta}</option>)}
          </select>
        </CampoSeleccion>
        <CampoSeleccion etiqueta="Sucursal">
          <select className={INPUT} value={form.branch} onChange={e => setForm({ ...form, branch: e.target.value })}>
            <option value="">General (todo el centro)</option>
            {sucursales.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </CampoSeleccion>
        <CampoSeleccion etiqueta="Fecha">
          <input type="date" className={INPUT} required value={form.spent_on} onChange={e => setForm({ ...form, spent_on: e.target.value })} />
        </CampoSeleccion>
        <CampoSeleccion etiqueta="Monto">
          <input type="number" inputMode="decimal" min="0.01" step="0.01" required className={INPUT} value={form.amount}
            onChange={e => setForm({ ...form, amount: e.target.value })} />
        </CampoSeleccion>
        <CampoSeleccion etiqueta="Moneda">
          <input type="text" maxLength={3} required className={INPUT} value={form.currency}
            onChange={e => setForm({ ...form, currency: e.target.value })} />
        </CampoSeleccion>
        <CampoSeleccion etiqueta="Nota (opcional)">
          <input type="text" maxLength={200} className={INPUT} value={form.note} onChange={e => setForm({ ...form, note: e.target.value })} />
        </CampoSeleccion>
        <div className="sm:col-span-2 lg:col-span-3">
          <Boton type="submit" className="w-auto" cargando={guardando} textoCargando="Guardando…">Cargar gasto</Boton>
        </div>
      </form>
    </Bloque>}

    <Bloque titulo="Gastos del rango"
      accion={<select aria-label="Filtrar por categoría" className={`${INPUT} !w-auto !py-1.5 !text-sm`} value={categoria}
        onChange={e => setCategoria(e.target.value as Categoria | '')}>
        <option value="">Todas las categorías</option>
        {CATEGORIAS.map(c => <option key={c.valor} value={c.valor}>{c.etiqueta}</option>)}
      </select>}>
      {error && <p role="alert" className="mb-3 text-sm text-alerta-600 dark:text-alerta-500">{error}</p>}
      {gastos === null && !error && <p role="status" className="text-sm text-tinta-500">Cargando…</p>}
      {gastos?.length === 0 && <p className="text-sm text-tinta-500">No hay gastos cargados en este rango.</p>}
      {gastos && gastos.length > 0 && <>
        <ul className="divide-y divide-tinta-200 dark:divide-tinta-800">{gastos.map(g =>
          <li key={g.id} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 py-2.5 text-sm">
            <div className="min-w-0">
              <p className="font-medium text-tinta-800 dark:text-tinta-100">{g.category_label}
                <span className="ml-2 font-normal text-tinta-500">{g.branch_name ?? 'General'}</span></p>
              <p className="text-xs text-tinta-500">{new Date(`${g.spent_on}T12:00:00`).toLocaleDateString('es-BO')}{g.note && ` · ${g.note}`}</p>
            </div>
            <div className="flex items-center gap-3">
              <span className="tabular-nums font-medium text-tinta-900 dark:text-tinta-100">{dinero(g.amount, g.currency)}</span>
              {puedeCargar && (aBorrar === g.id
                ? <span className="flex items-center gap-2 text-xs">
                  <button type="button" className="font-semibold text-alerta-600 dark:text-alerta-500" onClick={() => borrar(g.id)}>Sí, borrar</button>
                  <button type="button" className="text-tinta-500" onClick={() => setAborrar(null)}>No</button>
                </span>
                : <button type="button" className="text-xs text-tinta-500 hover:text-alerta-600" onClick={() => setAborrar(g.id)}
                  aria-label={`Borrar el gasto de ${g.category_label} del ${g.spent_on}`}>Borrar</button>)}
            </div>
          </li>)}</ul>
        <p className="mt-3 text-sm font-medium text-tinta-700 dark:text-tinta-300">
          Total: {Object.entries(total).map(([moneda, valor]) => dinero(String(valor), moneda)).join(' · ')}</p>
      </>}
    </Bloque>
  </div>
}

function PestanaComision({ token, puedeCargar, alCambiar }: {
  token: string | null | undefined; puedeCargar: boolean; alCambiar: () => void
}) {
  const [valor, setValor] = useState<string | null>(null)
  const [guardando, setGuardando] = useState(false)
  const [mensaje, setMensaje] = useState<{ ok: boolean; texto: string } | null>(null)

  useEffect(() => {
    const c = new AbortController()
    verComision({ token }, c.signal).then(r => setValor(r.stripe_percent))
      .catch(e => { if (!(e instanceof DOMException)) setMensaje({ ok: false, texto: mensajeError(e) }) })
    return () => c.abort()
  }, [token])

  const guardar = (evento: FormEvent) => {
    evento.preventDefault()
    if (valor === null) return
    setGuardando(true)
    setMensaje(null)
    guardarComision(valor, { token })
      .then(r => { setValor(r.stripe_percent); setMensaje({ ok: true, texto: 'Comisión guardada.' }); alCambiar() })
      .catch(e => setMensaje({ ok: false, texto: mensajeError(e) }))
      .finally(() => setGuardando(false))
  }

  return <Bloque titulo="Comisión de la pasarela">
    <form onSubmit={guardar} className="max-w-md space-y-3">
      <CampoSeleccion etiqueta="Porcentaje que se queda la pasarela de cada pago en línea (%)">
        <input type="number" inputMode="decimal" min="0" max="100" step="0.01" required className={INPUT}
          value={valor ?? ''} disabled={!puedeCargar || valor === null} onChange={e => setValor(e.target.value)} />
      </CampoSeleccion>
      <p className="text-sm text-tinta-500">
        El efectivo en ventanilla no paga comisión. El honorario (%) de cada profesional se
        define en su ficha, en Profesionales.</p>
      {puedeCargar && <Boton type="submit" className="w-auto" cargando={guardando} textoCargando="Guardando…">Guardar</Boton>}
      {mensaje && <p role={mensaje.ok ? 'status' : 'alert'}
        className={`text-sm ${mensaje.ok ? 'text-marca-700 dark:text-marca-400' : 'text-alerta-600 dark:text-alerta-500'}`}>{mensaje.texto}</p>}
    </form>
  </Bloque>
}
