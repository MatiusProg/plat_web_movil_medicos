/**
 * US-51 — «Tu ficha, más que un comprobante».
 *
 * Lo que el paciente necesita para ir, que el sistema ya sabe: agregarla al
 * calendario (el `.ics` del backend, con la hora de La Paz y un aviso 24 h
 * antes), cómo llegar (el mapa de la sede, si tiene coordenadas), cómo
 * prepararse y cuánto falta. Más la preconsulta: el motivo y las preguntas que
 * después ve el médico al abrir la atención. Sin cobro adicional.
 */
import { useEffect, useState } from 'react'
import { descargarArchivo } from '@/api/cliente'
import type { Ficha } from '@/api/fichas'
import { guardarPreconsulta, leerPreconsulta } from '@/api/preconsulta'
import { useSesion } from '@/sesion/useSesion'
import { cuentaRegresiva } from './experiencia_plus'

const CAMPO = 'w-full rounded-xl border border-tinta-300 bg-white px-3.5 py-2.5 text-[1.0625rem] text-tinta-800 outline-none transition focus:border-marca-500 focus:ring-4 focus:ring-marca-500/20 dark:border-tinta-700 dark:bg-tinta-900 dark:text-tinta-100'
const TARJETA = 'flex flex-col gap-2 rounded-2xl border border-tinta-200 bg-tinta-50 p-4 dark:border-tinta-800 dark:bg-tinta-950/40'
const BOTON = 'mt-auto inline-flex items-center justify-center rounded-xl border border-marca-300 px-3 py-2 text-sm font-semibold text-marca-700 transition hover:bg-marca-50 disabled:opacity-50 dark:border-marca-800 dark:text-marca-300 dark:hover:bg-marca-950/40'

function Icono({ d }: { d: string }) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="size-5 text-marca-600 dark:text-marca-400" aria-hidden="true"><path d={d} /></svg>
}

export function ExperienciaPlus({ ficha, cerrar }: { ficha: Ficha; cerrar: () => void }) {
  const { token } = useSesion()
  const [reason, setReason] = useState('')
  const [questions, setQuestions] = useState('')
  const [cargando, setCargando] = useState(true)
  const [guardando, setGuardando] = useState(false)
  const [aviso, setAviso] = useState<{ ok: boolean; texto: string } | null>(null)
  const [bajando, setBajando] = useState(false)

  const confirmada = ficha.status === 'confirmed'
  const futura = new Date(ficha.starts_at).getTime() > Date.now()
  const editable = confirmada && futura
  const falta = confirmada ? cuentaRegresiva(ficha.starts_at, ficha.practitioner_name) : null
  const cuando = new Date(ficha.starts_at).toLocaleString('es-BO', { dateStyle: 'full', timeStyle: 'short', hourCycle: 'h23' })

  useEffect(() => {
    let vivo = true
    leerPreconsulta(ficha.id, { token })
      .then(d => { if (vivo) { setReason(d.reason); setQuestions(d.questions) } })
      .catch(() => { if (vivo) setAviso({ ok: false, texto: 'No se pudo cargar la preconsulta.' }) })
      .finally(() => { if (vivo) setCargando(false) })
    return () => { vivo = false }
  }, [ficha.id, token])

  const guardar = async () => {
    setGuardando(true); setAviso(null)
    try {
      await guardarPreconsulta(ficha.id, { reason, questions }, { token })
      setAviso({ ok: true, texto: 'Preconsulta guardada: tu médico la verá al atenderte.' })
    } catch {
      setAviso({ ok: false, texto: 'No se pudo guardar. Revisa tu conexión o el estado de la ficha.' })
    } finally { setGuardando(false) }
  }

  const calendario = async () => {
    setBajando(true)
    try { await descargarArchivo(`/appointments/appointments/${ficha.id}/calendar.ics`, { token }, 'ficha.ics') }
    catch { setAviso({ ok: false, texto: 'No se pudo bajar el archivo del calendario.' }) }
    finally { setBajando(false) }
  }

  const porQueNo = editable ? null : confirmada
    ? 'El turno ya empezó: la preconsulta se podía completar hasta ese momento.'
    : 'La preconsulta se completa antes del turno: esta ficha ya no está pendiente.'

  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm" onMouseDown={cerrar}>
    <div role="dialog" aria-modal="true" aria-labelledby="plus-titulo" onMouseDown={e => e.stopPropagation()}
      className="flex max-h-[calc(100dvh-2rem)] w-full max-w-2xl flex-col overflow-hidden rounded-3xl border border-tinta-200 bg-white shadow-2xl dark:border-tinta-800 dark:bg-tinta-900">
      <header className="flex shrink-0 items-start justify-between gap-4 border-b border-tinta-200 px-6 py-5 dark:border-tinta-800">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-marca-600 dark:text-marca-400">Tu ficha, más que un comprobante</p>
          <h2 id="plus-titulo" className="mt-1 text-xl font-bold text-tinta-900 dark:text-tinta-50">{ficha.practitioner_name}</h2>
          <p className="mt-0.5 text-sm text-tinta-500">{ficha.branch_name} · <span className="first-letter:uppercase">{cuando}</span></p>
        </div>
        <button type="button" onClick={cerrar} aria-label="Cerrar"
          className="flex size-10 shrink-0 items-center justify-center rounded-xl text-xl text-tinta-500 transition hover:bg-tinta-100 dark:hover:bg-tinta-800">×</button>
      </header>

      <div className="space-y-6 overflow-y-auto px-6 py-5">
        {falta && <p className="rounded-2xl bg-marca-50 px-4 py-3 text-center font-semibold text-marca-800 dark:bg-marca-950/40 dark:text-marca-200">
          {falta}
        </p>}

        <div className="grid gap-3 sm:grid-cols-3">
          {editable && <section className={TARJETA}>
            <Icono d="M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z" />
            <h3 className="font-semibold text-tinta-900 dark:text-tinta-50">Calendario</h3>
            <p className="text-sm text-tinta-600 dark:text-tinta-300">Agrégala con un aviso un día antes. Sirve para Google, Outlook y el celular.</p>
            <button type="button" className={BOTON} onClick={() => void calendario()} disabled={bajando}>{bajando ? 'Bajando…' : 'Agregar a mi calendario'}</button>
          </section>}
          {ficha.branch_maps_url && <section className={TARJETA}>
            <Icono d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21Zm0-9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z" />
            <h3 className="font-semibold text-tinta-900 dark:text-tinta-50">Cómo llegar</h3>
            <p className="text-sm text-tinta-600 dark:text-tinta-300">{ficha.branch_address || ficha.branch_name}</p>
            <a className={BOTON} href={ficha.branch_maps_url} target="_blank" rel="noreferrer">Abrir el mapa</a>
          </section>}
          <section className={TARJETA}>
            <Icono d="M9 11l3 3 8-8M20 12v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h9" />
            <h3 className="font-semibold text-tinta-900 dark:text-tinta-50">Cómo prepararte</h3>
            <ul className="list-disc space-y-1 pl-4 text-sm text-tinta-600 dark:text-tinta-300">
              <li>Llega 10 minutos antes.</li>
              <li>Lleva tu identificación y el comprobante con QR.</li>
              <li>Trae tus recetas y estudios anteriores.</li>
            </ul>
          </section>
        </div>

        <section className="space-y-3">
          <div>
            <h3 className="font-semibold text-tinta-900 dark:text-tinta-50">Preconsulta <span className="font-normal text-tinta-500">(opcional)</span></h3>
            <p className="text-sm text-tinta-500">{porQueNo ?? 'Cuéntale a tu médico el motivo y lo que quieres preguntarle: lo ve al abrir tu atención.'}</p>
          </div>
          {cargando ? <p role="status" className="text-sm text-tinta-500">Cargando…</p>
            : porQueNo ? (reason || questions
              ? <dl className="space-y-2 text-sm">
                {reason && <div><dt className="font-medium text-tinta-700 dark:text-tinta-300">Motivo de consulta</dt><dd className="whitespace-pre-wrap text-tinta-800 dark:text-tinta-100">{reason}</dd></div>}
                {questions && <div><dt className="font-medium text-tinta-700 dark:text-tinta-300">Preguntas para el médico</dt><dd className="whitespace-pre-wrap text-tinta-800 dark:text-tinta-100">{questions}</dd></div>}
              </dl>
              : <p className="text-sm text-tinta-500">No anotaste una preconsulta para esta ficha.</p>)
            : <>
              <label className="block space-y-1.5 text-sm">
                <span className="font-medium text-tinta-700 dark:text-tinta-300">Motivo de consulta</span>
                <textarea className={`${CAMPO} min-h-20 resize-y`} maxLength={1200} value={reason} onChange={e => setReason(e.target.value)} placeholder="Ej.: dolor de cabeza desde hace una semana" />
              </label>
              <label className="block space-y-1.5 text-sm">
                <span className="font-medium text-tinta-700 dark:text-tinta-300">Preguntas para el médico</span>
                <textarea className={`${CAMPO} min-h-20 resize-y`} maxLength={1200} value={questions} onChange={e => setQuestions(e.target.value)} placeholder="Ej.: ¿puedo seguir tomando ibuprofeno?" />
              </label>
              <button type="button" onClick={() => void guardar()} disabled={guardando}
                className="rounded-xl bg-marca-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-marca-700 disabled:opacity-50">
                {guardando ? 'Guardando…' : 'Guardar preconsulta'}</button>
            </>}
          {aviso && <p role="status" className={`text-sm font-medium ${aviso.ok ? 'text-marca-700 dark:text-marca-300' : 'text-alerta-600 dark:text-alerta-400'}`}>{aviso.texto}</p>}
          <p className="text-xs text-tinta-500">Esta información no sustituye una evaluación médica.</p>
        </section>
      </div>
    </div>
  </div>
}
