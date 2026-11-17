/** US-38 — demanda esperada y ocupación de las próximas semanas. */
import { useEffect, useRef, useState } from 'react'
import { listarSucursales, type Sucursal } from '@/api/catalogo'
import { verProyeccionDemanda, type ProyeccionDemanda as Datos } from '@/api/demanda'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'
import { mensajeError } from './catalogo_comun'

const periodos = { manana: 'Mañana', tarde: 'Tarde', noche: 'Noche' }
const porcentaje = (v: number | null) => v === null ? 'Sin cupos' : `${(v * 100).toLocaleString('es-BO', { maximumFractionDigits: 1 })}%`

type FilterOption = { value: string; label: string }

type FilterDropdownProps = {
  label: string
  value: string
  options: FilterOption[]
  onChange: (value: string) => void
}

function FilterDropdown({ label, value, options, onChange }: FilterDropdownProps) {
  const [open, setOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const selected = options.find(option => option.value === value)

  useEffect(() => {
    if (!open) return
    const closeOutside = (event: PointerEvent) => {
      if (!wrapperRef.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', closeOutside)
    return () => document.removeEventListener('pointerdown', closeOutside)
  }, [open])

  const moveSelection = (delta: number) => {
    const current = Math.max(options.findIndex(option => option.value === value), 0)
    const next = Math.max(0, Math.min(options.length - 1, current + delta))
    if (options[next]) onChange(options[next].value)
  }

  return <div ref={wrapperRef} className="relative min-w-0">
    <span className="mb-2 block text-sm font-medium text-tinta-800 dark:text-tinta-100">{label}</span>
    <button
      ref={buttonRef}
      type="button"
      aria-label={label}
      aria-expanded={open}
      aria-haspopup="listbox"
      onClick={() => setOpen(previous => !previous)}
      onKeyDown={event => {
        if (event.key === 'Escape') { setOpen(false); return }
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
          event.preventDefault()
          moveSelection(event.key === 'ArrowDown' ? 1 : -1)
        }
        if (event.key === 'Home' && options[0]) { event.preventDefault(); onChange(options[0].value) }
        if (event.key === 'End' && options.length) { event.preventDefault(); onChange(options[options.length - 1].value) }
      }}
      className="flex w-full items-center justify-between gap-3 rounded-lg border border-tinta-300 bg-white px-3 py-2.5 text-left text-sm text-tinta-900 transition hover:border-marca-500 focus:outline-none focus:ring-2 focus:ring-marca-500 dark:border-tinta-700 dark:bg-tinta-950 dark:text-tinta-50"
    >
      <span className="truncate">{selected?.label ?? 'Seleccionar'}</span>
      <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={`h-4 w-4 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}>
        <path d="m6 9 6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </button>
    {open && <div
      role="listbox"
      aria-label={label}
      className="absolute left-0 right-0 top-full z-50 mt-1 max-h-60 overflow-y-auto rounded-lg border border-tinta-200 bg-white p-1 shadow-xl dark:border-tinta-700 dark:bg-tinta-950"
    >
      {options.map(option => <button
        key={option.value}
        type="button"
        role="option"
        aria-selected={option.value === value}
        className={`block w-full rounded-md px-3 py-2 text-left text-sm transition ${option.value === value
          ? 'bg-marca-100 font-semibold text-marca-900 dark:bg-marca-900 dark:text-marca-100'
          : 'text-tinta-800 hover:bg-tinta-100 dark:text-tinta-100 dark:hover:bg-tinta-800'}`}
        onClick={() => { onChange(option.value); setOpen(false); buttonRef.current?.focus() }}
      >{option.label}</button>)}
    </div>}
  </div>
}

export function ProyeccionDemanda() {
  useTitulo('Proyección de demanda')
  const { token, puede } = useSesion()
  const autorizado = puede('reporting.kpi.read')
  const [weeks, setWeeks] = useState(4)
  const [branch, setBranch] = useState('')
  const [branches, setBranches] = useState<Sucursal[]>([])
  const [data, setData] = useState<Datos | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!autorizado) return
    const ctrl = new AbortController()
    listarSucursales({ token }, ctrl.signal).then(setBranches).catch(() => {})
    return () => ctrl.abort()
  }, [token, autorizado])

  useEffect(() => {
    if (!autorizado) return
    const ctrl = new AbortController()
    setLoading(true)
    setError('')
    setData(null)
    verProyeccionDemanda(weeks, branch, { token }, ctrl.signal)
      .then(setData)
      .catch(e => { if (!ctrl.signal.aborted) setError(mensajeError(e)) })
      .finally(() => { if (!ctrl.signal.aborted) setLoading(false) })
    return () => ctrl.abort()
  }, [token, autorizado, weeks, branch])

  if (!autorizado) return <main className="mx-auto max-w-6xl px-5 py-8">
    <p role="alert">No tienes permiso para ver la proyección de demanda.</p>
  </main>

  const totalDemanda = data?.rows.reduce((sum, row) => sum + row.estimated_demand, 0) ?? 0
  const totalCupos = data?.rows.reduce((sum, row) => sum + row.capacity, 0) ?? 0
  const totalReservadas = data?.rows.reduce((sum, row) => sum + row.already_booked, 0) ?? 0

  return <main className="mx-auto max-w-6xl space-y-6 px-5 py-8 sm:py-10">
    <header>
      <p className="text-sm font-medium text-marca-700 dark:text-marca-400">Organización · US-38</p>
      <h1 className="mt-1 text-2xl font-semibold text-tinta-900 dark:text-tinta-50">Proyección de demanda de citas</h1>
      <p className="mt-2 text-sm text-tinta-500">Estimación de próximas semanas basada en las últimas ocho semanas de fichas.</p>
    </header>
    <section className="grid gap-4 rounded-2xl border border-tinta-200 bg-white p-5 dark:border-tinta-800 dark:bg-tinta-900 sm:grid-cols-2" aria-label="Filtros">
      <FilterDropdown
        label="Semanas a proyectar"
        value={String(weeks)}
        onChange={value => setWeeks(Number(value))}
        options={[1, 2, 3, 4, 6, 8].map(n => ({ value: String(n), label: `${n} semanas` }))}
      />
      <FilterDropdown
        label="Sucursal"
        value={branch}
        onChange={setBranch}
        options={[{ value: '', label: 'Todas las sucursales' }, ...branches.map(b => ({ value: String(b.id), label: b.name }))]}
      />
    </section>
    {loading && <p role="status">Calculando proyección…</p>}
    {error && <p role="alert" className="text-alerta-700">{error}</p>}
    {data && <>
      {!data.has_historical_data && <p role="status" className="rounded-xl border border-espera-300 p-4">No hay fichas históricas suficientes para estimar la demanda. Los valores estimados serán cero.</p>}
      <div className="grid gap-3 sm:grid-cols-3">
        {[
          ['Demanda estimada', totalDemanda.toLocaleString('es-BO', { maximumFractionDigits: 1 })],
          ['Fichas ya reservadas', String(totalReservadas)],
          ['Cupos disponibles en agenda', String(totalCupos)],
        ].map(([label, value]) => <div key={label} className="rounded-2xl border border-tinta-200 bg-white p-5 dark:border-tinta-800 dark:bg-tinta-900">
          <p className="text-sm text-tinta-500">{label}</p><p className="mt-2 text-2xl font-semibold tabular-nums">{value}</p>
        </div>)}
      </div>
      <section className="overflow-x-auto rounded-2xl border border-tinta-200 bg-white dark:border-tinta-800 dark:bg-tinta-900">
        <h2 className="p-5 text-lg font-semibold">Especialidades por semana y franja horaria</h2>
        <table className="w-full min-w-[750px] text-left text-sm">
          <thead className="border-y border-tinta-200 bg-tinta-50 dark:border-tinta-800 dark:bg-tinta-950"><tr>
            {['Semana', 'Especialidad', 'Franja', 'Estimadas', 'Reservadas', 'Capacidad', 'Ocupación esperada'].map(v => <th key={v} className="px-3 py-3 font-semibold">{v}</th>)}
          </tr></thead>
          <tbody>{data.rows.map((r, i) => <tr key={`${r.week_start}-${r.specialty_id}-${r.period}-${i}`} className="border-b border-tinta-100 dark:border-tinta-800">
            <td className="px-3 py-3 tabular-nums">{r.week_start}</td><td className="px-3 py-3">{r.specialty}</td>
            <td className="px-3 py-3">{periodos[r.period]}</td>
            <td className="px-3 py-3 tabular-nums">{r.estimated_demand}</td>
            <td className="px-3 py-3 tabular-nums">{r.already_booked}</td>
            <td className="px-3 py-3 tabular-nums">{r.capacity}</td>
            <td className="px-3 py-3"><span className={r.over_capacity ? 'font-semibold text-alerta-700' : ''}>{porcentaje(r.expected_occupancy)}</span>
              {r.expected_occupancy !== null && <div className="mt-1 h-1.5 w-24 rounded-full bg-tinta-100 dark:bg-tinta-700"><div className="h-full rounded-full bg-marca-500" style={{ width: `${r.expected_occupancy * 100}%` }}/></div>}
            </td>
          </tr>)}</tbody>
        </table>
        {data.rows.length === 0 && <p className="p-5 text-sm text-tinta-500">No hay agendas ni fichas que mostrar para estos filtros.</p>}
      </section>
      <p className="text-xs text-tinta-500">Método: promedio semanal histórico de {data.history_weeks} semanas. No es una predicción generada por IA. {data.note}</p>
    </>}
  </main>
}
