import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  OBLIGATORIAS_PARA_FIRMAR, SECCIONES, agregarEnmienda, firmarEncuentro, guardarBorrador,
  verAntecedentes, verEncuentro, type Antecedentes, type Encuentro, type Seccion,
} from '@/api/atencion'
import { Boton } from '@/componentes/Boton'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'
import { AvisoCatalogo, ErrorCatalogo, INPUT, PANEL, SECONDARY, mensajeError } from './catalogo_comun'

type Borrador = Record<Seccion, string>
const fechaHora = (iso: string) => new Date(iso).toLocaleString('es-BO', { dateStyle: 'medium', timeStyle: 'short', hourCycle: 'h23' })
const aBorrador = (e: Encuentro): Borrador =>
  Object.fromEntries(SECCIONES.map(s => [s.campo, e[s.campo]])) as Borrador

/** Los antecedentes declarados de US-08, arriba de todo: una alergia cambia una receta. */
function PanelAntecedentes({ datos }: { datos: Antecedentes | null }) {
  if (!datos) return null
  const grupos = [
    { titulo: 'Alergias', items: datos.allergies, alerta: true },
    { titulo: 'Condiciones crónicas', items: datos.conditions, alerta: false },
    { titulo: 'Medicación habitual', items: datos.medications, alerta: false },
  ]
  const vacio = grupos.every(g => g.items.length === 0)
  return <section className={PANEL} aria-labelledby="antecedentes-titulo">
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <h2 id="antecedentes-titulo" className="font-semibold text-tinta-900 dark:text-tinta-100">Antecedentes</h2>
      {datos.self_reported && <span className="text-xs text-tinta-500">Declarados por el paciente</span>}
    </div>
    {vacio ? <p className="mt-2 text-sm text-tinta-500">No tiene antecedentes declarados.</p> :
      <div className="mt-3 grid gap-4 sm:grid-cols-3">{grupos.map(g => <div key={g.titulo}>
        <h3 className="text-sm font-medium text-tinta-700 dark:text-tinta-300">{g.titulo}</h3>
        {g.items.length === 0 ? <p className="mt-1 text-sm text-tinta-400">Ninguna</p> :
          <ul className="mt-1 space-y-1 text-sm">{g.items.map(a => <li key={a.id} className={g.alerta && a.severity && ['anaphylactic', 'severe'].includes(a.severity) ? 'font-semibold text-alerta-700 dark:text-alerta-300' : 'text-tinta-600 dark:text-tinta-300'}>
            {a.description}{a.severity_label ? ` · ${a.severity_label}` : ''}
          </li>)}</ul>}
      </div>)}</div>}
  </section>
}

/** US-24 — Registrar, firmar y enmendar la atención de una ficha. */
export function Atencion() {
  const { id = '' } = useParams()
  const { token, puede } = useSesion()
  useTitulo('Atención')
  const enmendar = puede('encounters.encounter.amend')
  const [encuentro, setEncuentro] = useState<Encuentro | null>(null)
  const [borrador, setBorrador] = useState<Borrador | null>(null)
  const [antecedentes, setAntecedentes] = useState<Antecedentes | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)
  const [guardando, setGuardando] = useState(false)
  const [confirmarFirma, setConfirmarFirma] = useState(false)
  const [enmienda, setEnmienda] = useState<{ section: Seccion; text: string }>({ section: 'reason', text: '' })

  const cargar = useCallback(async (signal?: AbortSignal) => {
    try {
      const e = await verEncuentro(id, { token }, signal)
      setEncuentro(e); setBorrador(aBorrador(e)); setError(null)
      // Los antecedentes son un extra: si fallan, la atención se registra igual.
      verAntecedentes(e.patient.id, { token }, signal).then(setAntecedentes).catch(() => {})
    } catch (e) { if (!(e instanceof DOMException && e.name === 'AbortError')) setError(mensajeError(e)) }
  }, [id, token])

  useEffect(() => { const c = new AbortController(); void cargar(c.signal); return () => c.abort() }, [cargar])

  const cambios = encuentro && borrador ? SECCIONES.some(s => borrador[s.campo] !== encuentro[s.campo]) : false

  const guardar = async (e?: FormEvent) => {
    e?.preventDefault()
    if (!encuentro || !borrador || guardando) return null
    setGuardando(true); setError(null)
    try {
      const nuevo = await guardarBorrador(encuentro.id, borrador, { token })
      setEncuentro(nuevo); setAviso('Borrador guardado.')
      return nuevo
    } catch (err) { setError(mensajeError(err)); return null }
    finally { setGuardando(false) }
  }

  const firmar = async () => {
    if (!encuentro || guardando) return
    setConfirmarFirma(false)
    if (cambios && !(await guardar())) return
    setGuardando(true); setError(null)
    try { const f = await firmarEncuentro(encuentro.id, { token }); setEncuentro(f); setBorrador(aBorrador(f)); setAviso('Atención firmada. Ya no se puede editar: las correcciones van como enmienda.') }
    catch (err) { setError(mensajeError(err)) }
    finally { setGuardando(false) }
  }

  const enviarEnmienda = async (e: FormEvent) => {
    e.preventDefault()
    if (!encuentro || !enmienda.text.trim() || guardando) return
    setGuardando(true); setError(null)
    try {
      await agregarEnmienda(encuentro.id, enmienda.section, enmienda.text.trim(), { token })
      setEnmienda({ ...enmienda, text: '' }); setAviso('Enmienda agregada.')
      setEncuentro(await verEncuentro(encuentro.id, { token }))
    } catch (err) { setError(mensajeError(err)) }
    finally { setGuardando(false) }
  }

  if (!encuentro || !borrador) return <main className="mx-auto max-w-4xl space-y-4 px-5 py-10">
    {error ? <ErrorCatalogo mensaje={error} /> : <p role="status" className="text-sm text-tinta-500">Cargando atención…</p>}
    <Link to="/atencion" className={SECONDARY}>← Volver a la agenda</Link>
  </main>

  const firmado = encuentro.status === 'signed'
  const faltan = OBLIGATORIAS_PARA_FIRMAR.filter(c => !borrador[c].trim())
  return <main className="mx-auto max-w-4xl space-y-6 px-5 py-8 sm:py-10">
    <div className="surgir flex flex-wrap items-end justify-between gap-4">
      <div>
        <Link to="/atencion" className="text-sm font-medium text-marca-700 hover:underline dark:text-marca-400">← Atención del día</Link>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-tinta-900 dark:text-tinta-50">{encuentro.patient.full_name}</h1>
        <p className="mt-1 text-[0.9375rem] text-tinta-500">{[encuentro.patient.document_number && `CI ${encuentro.patient.document_number}`, fechaHora(encuentro.appointment_starts_at), encuentro.branch_name].filter(Boolean).join(' · ')}</p>
      </div>
      <span className={`rounded-full px-3 py-1 text-sm font-medium ${firmado ? 'bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-300' : 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300'}`}>
        {firmado ? `Firmada por ${encuentro.signed_by_name} · ${fechaHora(encuentro.signed_at!)}` : 'Borrador'}
      </span>
    </div>
    {aviso && <AvisoCatalogo mensaje={aviso} onCerrar={() => setAviso(null)} />}
    {error && <ErrorCatalogo mensaje={error} />}
    <PanelAntecedentes datos={antecedentes} />

    <form onSubmit={e => void guardar(e)} className={`${PANEL} space-y-5`}>
      {SECCIONES.map(s => <label key={s.campo} className="block space-y-1.5 text-sm">
        <span className="font-medium text-tinta-700 dark:text-tinta-300">{s.etiqueta}{!firmado && OBLIGATORIAS_PARA_FIRMAR.includes(s.campo) && <span className="text-alerta-600"> *</span>}</span>
        {firmado ? <p className="whitespace-pre-wrap rounded-xl bg-tinta-50 px-3.5 py-2.5 text-[0.9375rem] text-tinta-800 dark:bg-tinta-900 dark:text-tinta-100">{encuentro[s.campo] || '—'}</p>
          : <textarea className={`${INPUT} min-h-24 resize-y`} value={borrador[s.campo]} maxLength={s.campo === 'evolution' ? 10000 : 5000}
            onChange={e => setBorrador({ ...borrador, [s.campo]: e.target.value })} placeholder={s.ayuda} />}
        {firmado && encuentro.amendments.filter(a => a.section === s.campo).map(a => <div key={a.id} className="ml-3 border-l-2 border-marca-400 pl-3 text-sm">
          <p className="text-xs text-tinta-500">Enmienda de {a.author_name} · {fechaHora(a.created_at)}</p>
          <p className="whitespace-pre-wrap text-tinta-800 dark:text-tinta-100">{a.text}</p>
        </div>)}
      </label>)}
      {!firmado && <div className="flex flex-wrap items-center justify-end gap-3 border-t border-tinta-200 pt-4 dark:border-tinta-800">
        {faltan.length > 0 && <p className="mr-auto text-sm text-tinta-500">Para firmar falta: {faltan.map(c => SECCIONES.find(s => s.campo === c)!.etiqueta.toLowerCase()).join(' y ')}.</p>}
        <button type="submit" className={SECONDARY} disabled={guardando || !cambios}>Guardar borrador</button>
        <Boton type="button" className="w-auto" disabled={faltan.length > 0} cargando={guardando} onClick={() => setConfirmarFirma(true)}>Firmar atención</Boton>
      </div>}
    </form>

    {firmado && enmendar && <form onSubmit={e => void enviarEnmienda(e)} className={`${PANEL} space-y-4`}>
      <div><h2 className="font-semibold text-tinta-900 dark:text-tinta-100">Agregar una enmienda</h2><p className="mt-1 text-sm text-tinta-500">La atención firmada no se modifica. La corrección queda al lado del texto original, con tu nombre y la fecha.</p></div>
      <label className="block space-y-1.5 text-sm"><span className="font-medium text-tinta-700 dark:text-tinta-300">Sección</span>
        <select className={INPUT} value={enmienda.section} onChange={e => setEnmienda({ ...enmienda, section: e.target.value as Seccion })}>{SECCIONES.map(s => <option key={s.campo} value={s.campo}>{s.etiqueta}</option>)}</select></label>
      <label className="block space-y-1.5 text-sm"><span className="font-medium text-tinta-700 dark:text-tinta-300">Corrección</span>
        <textarea className={`${INPUT} min-h-20 resize-y`} value={enmienda.text} maxLength={5000} onChange={e => setEnmienda({ ...enmienda, text: e.target.value })} placeholder="Qué se corrige y por qué…" /></label>
      <div className="flex justify-end"><Boton type="submit" className="w-auto" cargando={guardando} disabled={!enmienda.text.trim()}>Agregar enmienda</Boton></div>
    </form>}

    {confirmarFirma && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="presentation" onMouseDown={e => { if (e.target === e.currentTarget) setConfirmarFirma(false) }}>
      <div role="alertdialog" aria-modal="true" aria-labelledby="firma-titulo" className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-tinta-900">
        <h2 id="firma-titulo" className="text-lg font-semibold">Firmar la atención</h2>
        <p className="mt-2 text-sm leading-6 text-tinta-500">Una vez firmada no se puede editar ni borrar: las correcciones se agregan como enmienda. La ficha queda marcada como atendida.</p>
        <div className="mt-6 flex justify-end gap-3"><button type="button" className={SECONDARY} onClick={() => setConfirmarFirma(false)}>Cancelar</button><button type="button" className="rounded-xl bg-marca-600 px-4 py-2.5 text-sm font-semibold text-white" onClick={() => void firmar()}>Firmar</button></div>
      </div>
    </div>}
  </main>
}
