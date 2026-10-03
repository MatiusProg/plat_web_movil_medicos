import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { SECCIONES, verHistorial, type Historial as DatosHistorial } from '@/api/atencion'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'
import { ErrorCatalogo, PANEL, SECONDARY, mensajeError } from './catalogo_comun'

const fecha = (iso: string) => new Date(iso).toLocaleDateString('es-BO', { day: 'numeric', month: 'long', year: 'numeric' })
const fechaHora = (iso: string) => new Date(iso).toLocaleString('es-BO', { dateStyle: 'medium', timeStyle: 'short', hourCycle: 'h23' })

/** US-25 — Todos los encuentros firmados del paciente, de todas las sucursales. */
export function Historial() {
  const { pacienteId = '' } = useParams()
  const { token, puede } = useSesion()
  useTitulo('Historial clínico')
  const leer = puede('encounters.history.read')
  const [datos, setDatos] = useState<DatosHistorial | null>(null)
  const [sucursal, setSucursal] = useState<string>('todas')
  const [error, setError] = useState<string | null>(null)

  const cargar = useCallback(async (signal?: AbortSignal) => {
    try { setDatos(await verHistorial(pacienteId, { token }, signal)); setError(null) }
    catch (e) { if (!(e instanceof DOMException && e.name === 'AbortError')) setError(mensajeError(e)) }
  }, [pacienteId, token])

  useEffect(() => {
    if (!leer) return
    const c = new AbortController(); void cargar(c.signal); return () => c.abort()
  }, [leer, cargar])

  if (!leer) return <main className="mx-auto max-w-4xl px-5 py-10 text-tinta-500">No tenés permiso para consultar historiales clínicos.</main>
  if (!datos) return <main className="mx-auto max-w-4xl space-y-4 px-5 py-10">
    {error ? <ErrorCatalogo mensaje={error} /> : <p role="status" className="text-sm text-tinta-500">Cargando historial…</p>}
    <Link to="/atencion" className={SECONDARY}>← Volver a la agenda</Link>
  </main>

  const encuentros = datos.encounters.filter(e => sucursal === 'todas' || e.branch_name === sucursal)
  return <main className="mx-auto max-w-4xl space-y-6 px-5 py-8 sm:py-10">
    <div className="surgir">
      <Link to="/atencion" className="text-sm font-medium text-marca-700 hover:underline dark:text-marca-400">← Atención del día</Link>
      <p className="mt-3 text-sm font-medium text-marca-700 dark:text-marca-400">Historia clínica</p>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight text-tinta-900 dark:text-tinta-50">{datos.patient.full_name}</h1>
      <p className="mt-1.5 max-w-2xl text-[0.9375rem] text-tinta-500">
        {datos.encounters.length === 0 ? 'Todavía no tiene atenciones firmadas.'
          : `${datos.encounters.length} ${datos.encounters.length === 1 ? 'atención firmada' : 'atenciones firmadas'} en ${datos.branches.length} ${datos.branches.length === 1 ? 'sucursal' : 'sucursales'}, en una sola línea de tiempo.`}
      </p>
    </div>

    {datos.branches.length > 1 && <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por sucursal">
      {[{ name: 'todas', encounters: datos.encounters.length }, ...datos.branches].map(s => <button key={s.name} type="button"
        className={sucursal === s.name ? 'rounded-xl bg-marca-600 px-4 py-2 text-sm font-semibold text-white' : SECONDARY}
        onClick={() => setSucursal(s.name)}>{s.name === 'todas' ? 'Todas' : s.name} · {s.encounters}</button>)}
    </div>}

    {encuentros.length > 0 && <ol className="relative space-y-6 border-l-2 border-tinta-200 pl-6 dark:border-tinta-800">
      {encuentros.map(e => <li key={e.id} className="relative">
        <span className="absolute -left-[33px] top-5 size-4 rounded-full border-2 border-white bg-marca-600 dark:border-tinta-950" aria-hidden="true" />
        <article className={PANEL}>
          <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-tinta-200 pb-3 dark:border-tinta-800">
            <h2 className="font-semibold text-tinta-900 dark:text-tinta-100">{fecha(e.appointment_starts_at)}</h2>
            <p className="text-sm text-tinta-500">{e.branch_name} · {e.practitioner_name}</p>
          </header>
          <dl className="mt-3 space-y-3 text-sm">
            {SECCIONES.filter(s => e[s.campo] || e.amendments.some(a => a.section === s.campo)).map(s => <div key={s.campo}>
              <dt className="font-medium text-tinta-700 dark:text-tinta-300">{s.etiqueta}</dt>
              <dd className="whitespace-pre-wrap text-tinta-800 dark:text-tinta-100">{e[s.campo] || '—'}</dd>
              {e.amendments.filter(a => a.section === s.campo).map(a => <dd key={a.id} className="ml-3 mt-1 border-l-2 border-marca-400 pl-3">
                <span className="block text-xs text-tinta-500">Enmienda de {a.author_name} · {fechaHora(a.created_at)}</span>
                <span className="whitespace-pre-wrap text-tinta-800 dark:text-tinta-100">{a.text}</span>
              </dd>)}
            </div>)}
          </dl>
          <p className="mt-3 text-xs text-tinta-500">Firmada por {e.signed_by_name} · {e.signed_at && fechaHora(e.signed_at)}</p>
        </article>
      </li>)}
    </ol>}
  </main>
}
