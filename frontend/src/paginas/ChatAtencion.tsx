/**
 * US-47 — El chat de una atención entre el paciente y su médico.
 *
 * - `PanelChat`: la conversación, embebida en la atención del médico y en la
 *   página de una consulta.
 * - `ConsultaChat`: la página `/consultas/:encuentroId`, a la que llega el
 *   paciente desde su historia y el médico desde su bandeja.
 * - `ConsultasPacientes`: la bandeja del médico, `/consultas`, con los sin leer.
 *
 * La misma pantalla sirve a los dos lados: quién es quién lo dice el backend.
 * Sin tiempo real: la conversación abierta se vuelve a pedir cada 10 segundos
 * y la bandeja cada 30.
 */
import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  cerrarConversacion, escribirMensaje, verBandejaChat, verConversacion,
  type Conversacion, type FilaBandejaChat,
} from '@/api/chat'
import { Boton } from '@/componentes/Boton'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'
import { DANGER, ErrorCatalogo, INPUT, PANEL, SECONDARY, mensajeError } from './catalogo_comun'

const MAX = 2000
const CADA_MS = 10_000

const fechaHora = (iso: string) =>
  new Date(iso).toLocaleString('es-BO', { dateStyle: 'medium', timeStyle: 'short', hourCycle: 'h23' })
const fecha = (iso: string) => new Date(iso).toLocaleDateString('es-BO', { dateStyle: 'long' })

const esAbortado = (e: unknown) => e instanceof DOMException && e.name === 'AbortError'

/** Pide la conversación al montar y cada 10 s mientras la pestaña está visible. */
function useConversacion(encuentroId: string) {
  const { token } = useSesion()
  const [datos, setDatos] = useState<Conversacion | null>(null)
  const [error, setError] = useState<string | null>(null)

  const cargar = useCallback(async (signal?: AbortSignal) => {
    try { setDatos(await verConversacion(encuentroId, { token }, signal)); setError(null) }
    catch (e) { if (!esAbortado(e)) setError(mensajeError(e)) }
  }, [encuentroId, token])

  useEffect(() => {
    const c = new AbortController()
    void cargar(c.signal)
    const t = window.setInterval(() => { if (document.visibilityState === 'visible') void cargar(c.signal) }, CADA_MS)
    return () => { c.abort(); window.clearInterval(t) }
  }, [cargar])

  return { datos, setDatos, error, cargar }
}

function Receta({ datos }: { datos: Conversacion }) {
  if (datos.prescription.length === 0 && datos.orders.length === 0) return null
  return <details className="rounded-xl bg-tinta-50 px-4 py-3 text-sm dark:bg-tinta-900" open={datos.side === 'patient'}>
    <summary className="cursor-pointer font-medium text-tinta-700 dark:text-tinta-200">Receta y órdenes de esta atención</summary>
    <ul className="mt-2 space-y-1 text-tinta-700 dark:text-tinta-300">
      {datos.prescription.map((p, i) => <li key={`p${i}`}>
        <span className="font-medium text-tinta-900 dark:text-tinta-100">{p.medication}</span> · {p.dose} · {p.frequency} · {p.duration}
        {p.instructions && <span className="text-tinta-500"> — {p.instructions}</span>}
      </li>)}
      {datos.orders.map((o, i) => <li key={`o${i}`}><span className="font-medium">{o.kind_display}:</span> {o.description}</li>)}
    </ul>
  </details>
}

/** La conversación de una atención: mensajes, aviso de urgencias y caja para escribir. */
export function PanelChat({ encuentroId, titulo = true }: { encuentroId: string; titulo?: boolean }) {
  const { token } = useSesion()
  const { datos, setDatos, error, cargar } = useConversacion(encuentroId)
  const [texto, setTexto] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [errorEnvio, setErrorEnvio] = useState<string | null>(null)
  const [urgencia, setUrgencia] = useState<string | null>(null)
  const [confirmarCierre, setConfirmarCierre] = useState(false)
  const fin = useRef<HTMLDivElement>(null)
  const cuantos = datos?.messages.length ?? 0

  useEffect(() => { fin.current?.scrollIntoView({ block: 'nearest' }) }, [cuantos])

  const enviar = async (e?: Pick<FormEvent, 'preventDefault'>) => {
    e?.preventDefault()
    const body = texto.trim()
    if (!body || enviando) return
    setEnviando(true); setErrorEnvio(null)
    try {
      const r = await escribirMensaje(encuentroId, body, { token })
      setTexto('')
      setUrgencia(r.emergency?.message ?? null)
      await cargar()
    } catch (err) { setErrorEnvio(mensajeError(err)); void cargar() }
    finally { setEnviando(false) }
  }

  const cerrar = async () => {
    setConfirmarCierre(false); setErrorEnvio(null)
    try { setDatos(await cerrarConversacion(encuentroId, { token })) }
    catch (err) { setErrorEnvio(mensajeError(err)) }
  }

  if (error) return <ErrorCatalogo mensaje={error} />
  if (!datos) return <p role="status" className="text-sm text-tinta-500">Cargando la conversación…</p>

  const medico = datos.side === 'practitioner'
  const conQuien = medico ? datos.patient_name : `Dr(a). ${datos.practitioner_name}`

  return <section className={`${PANEL} space-y-4`} aria-label="Chat con el médico">
    {titulo && <header className="flex flex-wrap items-start justify-between gap-2">
      <div>
        <h2 className="font-semibold text-tinta-900 dark:text-tinta-100">{medico ? 'Consultas del paciente' : 'Chat con tu médico'}</h2>
        <p className="text-sm text-tinta-500">
          {conQuien}{datos.encounter_date && ` · atención del ${fecha(datos.encounter_date)}`}
        </p>
      </div>
      {medico && datos.can_write && (confirmarCierre
        ? <div className="flex items-center gap-2 text-sm">
          <span className="text-tinta-500">¿Cerrar? El paciente ya no podrá escribir.</span>
          <button type="button" className={DANGER} onClick={() => void cerrar()}>Sí, cerrar</button>
          <button type="button" className={SECONDARY} onClick={() => setConfirmarCierre(false)}>No</button>
        </div>
        : <button type="button" className={SECONDARY} onClick={() => setConfirmarCierre(true)}>Cerrar conversación</button>)}
    </header>}

    <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
      {datos.notice}
    </p>

    <Receta datos={datos} />

    {urgencia && <div role="alert" className="rounded-xl border border-alerta-300 bg-alerta-50 px-4 py-3 text-[0.9375rem] font-medium text-alerta-800 dark:border-alerta-500/40 dark:bg-alerta-500/15 dark:text-alerta-200">
      {urgencia}
      <span className="mt-1 block text-sm font-normal">Tu mensaje le llegó a tu médico igual, pero no esperes su respuesta para ir.</span>
    </div>}

    <div className="max-h-[28rem] space-y-3 overflow-y-auto pr-1" aria-live="polite">
      {datos.messages.length === 0
        ? <p className="py-6 text-center text-sm text-tinta-500">
          {medico ? 'El paciente todavía no escribió.' : 'Escribe tu duda sobre la medicación o las indicaciones de esta atención.'}
        </p>
        : datos.messages.map(m => <div key={m.id} className={`flex ${m.mine ? 'justify-end' : 'justify-start'}`}>
          <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${m.mine
            ? 'bg-marca-600 text-white'
            : m.flagged_emergency
              ? 'border border-alerta-300 bg-alerta-50 text-tinta-900 dark:border-alerta-500/40 dark:bg-alerta-500/15 dark:text-tinta-50'
              : 'bg-tinta-100 text-tinta-900 dark:bg-tinta-800 dark:text-tinta-50'}`}>
            {m.flagged_emergency && <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-alerta-700 dark:text-alerta-300">Posible urgencia: se le indicó ir a emergencias</p>}
            <p className="whitespace-pre-wrap text-[0.9375rem] leading-6">{m.body}</p>
            <p className={`mt-1 text-xs ${m.mine ? 'text-marca-100' : 'text-tinta-500'}`}>{m.mine ? 'Tú' : m.author_name} · {fechaHora(m.created_at)}</p>
          </div>
        </div>)}
      <div ref={fin} />
    </div>

    {errorEnvio && <ErrorCatalogo mensaje={errorEnvio} />}

    {datos.can_write
      ? <form onSubmit={e => void enviar(e)} className="space-y-2">
        <label className="block">
          <span className="sr-only">Mensaje</span>
          <textarea className={`${INPUT} min-h-20 resize-y`} value={texto} maxLength={MAX}
            placeholder={medico ? 'Responde al paciente…' : 'Escribe tu consulta…'}
            onChange={e => setTexto(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) void enviar(e) }} />
        </label>
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-tinta-500">
            {datos.closes_at && `Puedes escribir hasta el ${fecha(datos.closes_at)}.`} {texto.length}/{MAX}
          </span>
          <Boton type="submit" className="w-auto" cargando={enviando} textoCargando="Enviando…" disabled={!texto.trim()}>Enviar</Boton>
        </div>
      </form>
      : <div className="rounded-xl bg-tinta-50 px-4 py-3 text-sm text-tinta-600 dark:bg-tinta-900 dark:text-tinta-300">
        {datos.closed_reason === 'closed' ? 'El médico cerró esta conversación.' : `La conversación se cerró: pasaron ${datos.window_days} días desde la atención.`}
        {!medico && <> Para una consulta nueva, <Link to="/buscar-profesionales" className="font-medium text-marca-700 hover:underline dark:text-marca-400">reserva una ficha</Link>.</>}
      </div>}
  </section>
}

/** `/consultas/:encuentroId` — la conversación sola, para el paciente y para el médico. */
export function ConsultaChat() {
  const { encuentroId = '' } = useParams()
  const { puede } = useSesion()
  useTitulo('Chat con el médico')
  const medico = puede('encounters.encounter.read')
  return <main className="mx-auto max-w-3xl space-y-4 px-5 py-8 sm:py-10">
    <Link to={medico ? '/consultas' : '/mi-historia'} className="text-sm font-medium text-marca-700 hover:underline dark:text-marca-400">
      ← {medico ? 'Consultas de pacientes' : 'Mi historia clínica'}</Link>
    <PanelChat encuentroId={encuentroId} />
  </main>
}

/** `/consultas` — la bandeja del médico: las conversaciones de sus atenciones. */
export function ConsultasPacientes() {
  const { token, puede } = useSesion()
  useTitulo('Consultas de pacientes')
  const permitido = puede('encounters.chat') && puede('encounters.encounter.read')
  const [filas, setFilas] = useState<FilaBandejaChat[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!permitido) return
    const c = new AbortController()
    const cargar = () => verBandejaChat({ token }, c.signal)
      .then(d => { setFilas(d.results); setError(null) })
      .catch(e => { if (!esAbortado(e)) setError(mensajeError(e)) })
    void cargar()
    const t = window.setInterval(() => { if (document.visibilityState === 'visible') void cargar() }, 30_000)
    return () => { c.abort(); window.clearInterval(t) }
  }, [permitido, token])

  if (!permitido) return <main className="mx-auto max-w-4xl px-5 py-10 text-tinta-500">Esta pantalla es del médico que responde las consultas de sus pacientes.</main>

  return <main className="mx-auto max-w-4xl space-y-6 px-5 py-8 sm:py-10">
    <div className="surgir">
      <p className="text-sm font-medium text-marca-700 dark:text-marca-400">Atención</p>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight text-tinta-900 dark:text-tinta-50">Consultas de pacientes</h1>
      <p className="mt-1.5 max-w-2xl text-[0.9375rem] text-tinta-500">
        Lo que te escribieron los pacientes que atendiste, sobre la medicación o las indicaciones de esa atención. Arriba, lo que no leíste.
      </p>
    </div>
    {error && <ErrorCatalogo mensaje={error} />}
    {!filas && !error && <p role="status" className="text-sm text-tinta-500">Cargando…</p>}
    {filas && filas.length === 0 && <div className={`${PANEL} text-center text-sm text-tinta-500`}>Ningún paciente te escribió todavía.</div>}
    {filas && filas.length > 0 && <ul className="space-y-3">
      {filas.map(f => <li key={f.encounter}>
        <Link to={`/consultas/${f.encounter}`} className={`${PANEL} flex flex-wrap items-center justify-between gap-3 transition hover:border-marca-300`}>
          <div>
            <p className="font-semibold text-tinta-900 dark:text-tinta-100">{f.patient_name}</p>
            <p className="text-sm text-tinta-500">
              {f.encounter_date && `Atención del ${fecha(f.encounter_date)}`}
              {f.last_message_at && ` · último mensaje ${fechaHora(f.last_message_at)}`}
              {!f.can_write && ' · cerrada'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {f.unread_emergency > 0 && <span className="rounded-full bg-alerta-600 px-2.5 py-0.5 text-xs font-semibold text-white">Posible urgencia</span>}
            {f.unread > 0 && <span className="rounded-full bg-marca-600 px-2.5 py-0.5 text-xs font-semibold text-white">{f.unread} sin leer</span>}
          </div>
        </Link>
      </li>)}
    </ul>}
  </main>
}
