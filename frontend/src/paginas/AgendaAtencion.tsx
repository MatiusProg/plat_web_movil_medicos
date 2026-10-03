import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { abrirAtencion, verAgenda, type Agenda, type FichaAgenda } from '@/api/atencion'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'
import { INPUT, PANEL, SECONDARY, ErrorCatalogo, IconoCatalogo, mensajeError } from './catalogo_comun'

/** Hoy en la hora local del navegador, como AAAA-MM-DD. */
function hoy() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const hora = (iso: string) => new Date(iso).toLocaleTimeString('es-BO', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })

function edad(nacimiento: string | null) {
  if (!nacimiento) return null
  const n = new Date(nacimiento), h = new Date()
  let anios = h.getFullYear() - n.getFullYear()
  if (h < new Date(h.getFullYear(), n.getMonth(), n.getDate())) anios -= 1
  return anios
}

function EstadoAtencion({ ficha }: { ficha: FichaAgenda }) {
  const e = ficha.encounter
  const [texto, clase] = !e ? ['Sin atender', 'bg-tinta-100 text-tinta-600 dark:bg-tinta-800 dark:text-tinta-300']
    : e.status === 'signed' ? ['Firmada', 'bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-300']
    : ['Borrador', 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300']
  return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${clase}`}>{texto}</span>
}

/** US-24 — Las fichas del día del profesional, para abrir su atención. */
export function AgendaAtencion() {
  const { token, puede } = useSesion()
  useTitulo('Atención del día')
  const navegar = useNavigate()
  const leer = puede('encounters.encounter.read')
  const atender = puede('encounters.encounter.create')
  const [fecha, setFecha] = useState(hoy)
  const [agenda, setAgenda] = useState<Agenda | null>(null)
  const [cargando, setCargando] = useState(true)
  const [abriendo, setAbriendo] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const recargar = useCallback(async (signal?: AbortSignal) => {
    setCargando(true)
    try { setAgenda(await verAgenda(fecha, { token }, signal)); setError(null) }
    catch (e) { if (!(e instanceof DOMException && e.name === 'AbortError')) setError(mensajeError(e)) }
    finally { if (!signal?.aborted) setCargando(false) }
  }, [fecha, token])

  useEffect(() => {
    if (!leer) return
    const c = new AbortController(); void recargar(c.signal); return () => c.abort()
  }, [leer, recargar])

  const abrir = async (ficha: FichaAgenda) => {
    if (ficha.encounter) { navegar(`/atencion/${ficha.encounter.id}`); return }
    setAbriendo(ficha.id); setError(null)
    try { const e = await abrirAtencion(ficha.id, { token }); navegar(`/atencion/${e.id}`) }
    catch (e) { setError(mensajeError(e)) }
    finally { setAbriendo(null) }
  }

  if (!leer) return <main className="mx-auto max-w-4xl px-5 py-10 text-tinta-500">Esta pantalla es del profesional que atiende.</main>
  const fichas = agenda?.appointments ?? []
  return <main className="mx-auto max-w-5xl space-y-6 px-5 py-8 sm:py-10">
    <div className="surgir flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-marca-700 dark:text-marca-400">Historia clínica · US-24</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-tinta-900 dark:text-tinta-50">Atención del día</h1>
        <p className="mt-1.5 max-w-2xl text-[0.9375rem] text-tinta-500">{agenda ? `Fichas de ${agenda.practitioner}.` : 'Tus fichas del día.'} Abrí una para registrar la atención: motivo, evolución, diagnóstico, indicaciones y tratamiento.</p>
      </div>
      <div className="flex items-center gap-2">
        <label className="sr-only" htmlFor="fecha-agenda">Fecha</label>
        <input id="fecha-agenda" type="date" className={`${INPUT} w-auto`} value={fecha} onChange={e => setFecha(e.target.value || hoy())} />
        <button type="button" className={SECONDARY} disabled={cargando} onClick={() => void recargar()}><IconoCatalogo nombre="refresh" className="size-4" /> Actualizar</button>
      </div>
    </div>
    {error && <ErrorCatalogo mensaje={error} />}
    <section className={PANEL}>
      {cargando ? <p role="status" className="py-12 text-center text-sm text-tinta-500">Cargando fichas…</p>
        : fichas.length === 0 ? <div className="py-12 text-center"><h2 className="font-semibold">No tenés fichas este día</h2><p className="mt-1 text-sm text-tinta-500">Elegí otra fecha arriba.</p></div>
        : <ul className="divide-y divide-tinta-200 dark:divide-tinta-800">{fichas.map(f => {
          const anios = edad(f.patient.birth_date)
          return <li key={f.id} className="flex flex-wrap items-center gap-4 py-4">
            <div className="w-20 shrink-0 text-lg font-semibold tabular-nums text-tinta-900 dark:text-tinta-100">{hora(f.starts_at)}</div>
            <div className="min-w-0 flex-1">
              <p className="font-semibold text-tinta-900 dark:text-tinta-100">{f.patient.full_name}</p>
              <p className="text-sm text-tinta-500">{[f.patient.document_number && `CI ${f.patient.document_number}`, anios !== null && `${anios} años`, f.branch_name].filter(Boolean).join(' · ')}</p>
            </div>
            <EstadoAtencion ficha={f} />
            {(atender || f.encounter) && <button type="button" className={SECONDARY} disabled={abriendo === f.id} onClick={() => void abrir(f)}>
              {abriendo === f.id ? 'Abriendo…' : !f.encounter ? 'Atender' : f.encounter.status === 'signed' ? 'Ver' : 'Continuar'}
            </button>}
          </li>
        })}</ul>}
    </section>
  </main>
}
