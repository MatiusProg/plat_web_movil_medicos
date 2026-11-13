import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  aprobarTexto, corregirTexto, descartarTexto, reintentarResumen, verBandeja,
  type EstadoTexto, type ResultadoResumen, type TextoIa, type TramoDiferencia,
} from '@/api/textos_ia'
import { Boton } from '@/componentes/Boton'
import { Paginador } from '@/componentes/Paginador'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'
import {
  AvisoCatalogo, DANGER, ErrorCatalogo, INPUT, IconoCatalogo, PANEL, SECONDARY, mensajeError,
} from './catalogo_comun'

const PESTANAS: { estado: EstadoTexto; etiqueta: string }[] = [
  { estado: 'draft', etiqueta: 'Pendientes' },
  { estado: 'approved', etiqueta: 'Aprobados' },
  { estado: 'discarded', etiqueta: 'Descartados' },
]

const fechaHora = (iso: string) =>
  new Date(iso).toLocaleString('es-BO', { dateStyle: 'medium', timeStyle: 'short', hourCycle: 'h23' })

/** Lo que cambió el médico: lo tachado lo escribió la IA, lo resaltado lo puso él. */
function Diferencia({ tramos }: { tramos: TramoDiferencia[] }) {
  return <p className="whitespace-pre-wrap text-[0.9375rem] leading-7 text-tinta-800 dark:text-tinta-100">
    {tramos.map((t, i) => t.op === 'equal' ? <span key={i}>{t.text}</span>
      : t.op === 'delete'
        ? <del key={i} className="rounded bg-alerta-50 px-0.5 text-alerta-700 dark:bg-alerta-500/15 dark:text-alerta-300">{t.text}</del>
        : <ins key={i} className="rounded bg-marca-50 px-0.5 text-marca-800 no-underline dark:bg-marca-950 dark:text-marca-200">{t.text}</ins>)}
  </p>
}

function Origen({ texto }: { texto: TextoIa }) {
  return <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-tinta-500">
    <span className="inline-flex rounded-full bg-marca-50 px-2 py-0.5 text-xs font-medium text-marca-700 dark:bg-marca-950 dark:text-marca-300">{texto.kind_display}</span>
    {texto.encounter_date && <span>Atención del {fechaHora(texto.encounter_date)}</span>}
    {texto.order_description && <span>· Orden: {texto.order_description}</span>}
    <span>· Generado el {fechaHora(texto.created_at)}{texto.generated_by && ` con ${texto.generated_by}`}</span>
  </div>
}

/** Un texto pendiente: se corrige en el lugar y se aprueba o se descarta. */
function Pendiente({ texto, onDecidido }: { texto: TextoIa; onDecidido: (t: TextoIa, aviso: string) => void }) {
  const { token } = useSesion()
  const guardado = texto.final_text || texto.generated_text
  const [actual, setActual] = useState(texto)
  const [valor, setValor] = useState(guardado)
  const [ocupado, setOcupado] = useState<'guardar' | 'aprobar' | 'descartar' | null>(null)
  const [confirmarDescarte, setConfirmarDescarte] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sinGuardar = valor !== (actual.final_text || actual.generated_text)
  const vacio = valor.trim() === ''

  const hacer = async (accion: 'guardar' | 'aprobar' | 'descartar') => {
    setOcupado(accion); setError(null)
    try {
      if (accion === 'guardar') setActual(await corregirTexto(texto.id, valor, { token }))
      else if (accion === 'aprobar') {
        const t = await aprobarTexto(texto.id, sinGuardar ? valor : undefined, { token })
        onDecidido(t, `Aprobado. ${t.patient_name} ya puede leerlo.`)
      } else {
        const t = await descartarTexto(texto.id, { token })
        onDecidido(t, 'Descartado. El paciente no lo verá.')
      }
    } catch (e) { setError(mensajeError(e)) }
    finally { setOcupado(null); setConfirmarDescarte(false) }
  }

  return <article className={`${PANEL} space-y-4`}>
    <div>
      <h2 className="font-semibold text-tinta-900 dark:text-tinta-100">{texto.patient_name}</h2>
      <div className="mt-1"><Origen texto={texto} /></div>
    </div>

    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-tinta-700 dark:text-tinta-300">Texto para el paciente</span>
      <textarea className={`${INPUT} min-h-72 resize-y leading-7`} value={valor} maxLength={4000}
        onChange={e => setValor(e.target.value)} />
    </label>

    {actual.warnings.length > 0 && <div role="note" className="rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-2.5 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
      <p className="font-medium">Revísalo antes de aprobar:</p>
      <ul className="mt-1 list-disc pl-5">{actual.warnings.map(w => <li key={w}>{w}</li>)}</ul>
    </div>}

    {actual.was_edited && !sinGuardar && <details className="text-sm">
      <summary className="cursor-pointer font-medium text-tinta-700 dark:text-tinta-300">Qué cambiaste respecto de lo que escribió la IA</summary>
      <div className="mt-2 rounded-xl bg-tinta-50 p-3 dark:bg-tinta-900"><Diferencia tramos={actual.diff} /></div>
    </details>}
    {sinGuardar && <details className="text-sm">
      <summary className="cursor-pointer font-medium text-tinta-700 dark:text-tinta-300">Ver lo que escribió la IA</summary>
      <p className="mt-2 whitespace-pre-wrap rounded-xl bg-tinta-50 p-3 text-tinta-600 dark:bg-tinta-900 dark:text-tinta-300">{texto.generated_text}</p>
    </details>}

    {error && <ErrorCatalogo mensaje={error} />}

    <div className="flex flex-wrap items-center gap-2">
      <Boton type="button" className="w-auto" cargando={ocupado === 'aprobar'} textoCargando="Aprobando…"
        disabled={ocupado !== null || vacio} onClick={() => void hacer('aprobar')}>
        <IconoCatalogo nombre="check" className="size-4" /> {sinGuardar ? 'Aprobar con la corrección' : 'Aprobar'}
      </Boton>
      <button type="button" className={SECONDARY} disabled={ocupado !== null || !sinGuardar || vacio}
        onClick={() => void hacer('guardar')}>{ocupado === 'guardar' ? 'Guardando…' : 'Guardar sin aprobar'}</button>
      {sinGuardar && <button type="button" className={SECONDARY} disabled={ocupado !== null}
        onClick={() => setValor(actual.final_text || actual.generated_text)}>Deshacer cambios</button>}
      <div className="ml-auto flex items-center gap-2">
        {confirmarDescarte
          ? <>
            <span className="text-sm text-tinta-500">¿Descartarlo? El paciente no lo verá.</span>
            <button type="button" className={DANGER} disabled={ocupado !== null} onClick={() => void hacer('descartar')}>
              {ocupado === 'descartar' ? 'Descartando…' : 'Sí, descartar'}</button>
            <button type="button" className={SECONDARY} onClick={() => setConfirmarDescarte(false)}>No</button>
          </>
          : <button type="button" className={DANGER} disabled={ocupado !== null} onClick={() => setConfirmarDescarte(true)}>Descartar</button>}
      </div>
    </div>
  </article>
}

/**
 * US-39 — Qué pasó con el resumen para el paciente al firmar la atención.
 *
 * Si quedó generado, lleva a la bandeja; si la IA no estaba, lo dice (no hay
 * plantilla de reemplazo) y deja reintentar.
 */
export function AvisoResumenPaciente({ encuentroId, resultado, onCambio }: {
  encuentroId: string
  resultado: ResultadoResumen
  onCambio: (r: ResultadoResumen) => void
}) {
  const { token, puede } = useSesion()
  const [reintentando, setReintentando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const listo = resultado.status === 'generated' || resultado.status === 'exists'

  const reintentar = async () => {
    setReintentando(true); setError(null)
    try { onCambio(await reintentarResumen(encuentroId, { token })) }
    catch (e) { setError(mensajeError(e)) }
    finally { setReintentando(false) }
  }

  return <div role="status" className={`flex flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border px-4 py-3 text-sm ${listo
    ? 'border-marca-200 bg-marca-50 text-marca-800 dark:border-marca-800 dark:bg-marca-950 dark:text-marca-200'
    : 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200'}`}>
    <span className="mr-auto">{resultado.message}{error && ` ${error}`}</span>
    {listo && puede('ai.text.review') && <Link to="/textos-ia" className="font-semibold underline-offset-2 hover:underline">Revisarlo ahora →</Link>}
    {!listo && puede('ai.text.review') && <button type="button" className={SECONDARY} disabled={reintentando}
      onClick={() => void reintentar()}>{reintentando ? 'Generando…' : 'Reintentar'}</button>}
  </div>
}

/**
 * US-39 — En una atención ya firmada, sin aviso a la vista: pedir el resumen
 * para el paciente. Si ya hay uno, el backend lo dice y no genera otro.
 */
export function PedirResumenPaciente({ encuentroId, onResultado }: {
  encuentroId: string
  onResultado: (r: ResultadoResumen) => void
}) {
  const { token, puede } = useSesion()
  const [pidiendo, setPidiendo] = useState(false)
  const [error, setError] = useState<string | null>(null)
  if (!puede('ai.text.review')) return null
  const pedir = async () => {
    setPidiendo(true); setError(null)
    try { onResultado(await reintentarResumen(encuentroId, { token })) }
    catch (e) { setError(mensajeError(e)) }
    finally { setPidiendo(false) }
  }
  return <div className="flex flex-wrap items-center gap-3 text-sm text-tinta-500">
    <button type="button" className={SECONDARY} disabled={pidiendo} onClick={() => void pedir()}>
      {pidiendo ? 'Generando…' : 'Resumen para el paciente'}</button>
    <span>{error ?? 'La IA lo redacta desde esta atención; nadie lo ve hasta que lo apruebes.'}</span>
  </div>
}

/** Un texto ya decidido: qué se aprobó, quién y cuándo, y qué se corrigió. */
function Decidido({ texto }: { texto: TextoIa }) {
  const aprobado = texto.status === 'approved'
  return <article className={`${PANEL} space-y-3`}>
    <div className="flex flex-wrap items-start justify-between gap-2">
      <div>
        <h2 className="font-semibold text-tinta-900 dark:text-tinta-100">{texto.patient_name}</h2>
        <div className="mt-1"><Origen texto={texto} /></div>
      </div>
      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${aprobado
        ? 'bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-300'
        : 'bg-tinta-100 text-tinta-600 dark:bg-tinta-800 dark:text-tinta-300'}`}>
        {aprobado ? (texto.was_edited ? 'Aprobado con corrección' : 'Aprobado sin cambios') : 'Descartado'}
      </span>
    </div>
    {aprobado && texto.was_edited
      ? <Diferencia tramos={texto.diff} />
      : <p className={`whitespace-pre-wrap text-[0.9375rem] leading-7 ${aprobado ? 'text-tinta-800 dark:text-tinta-100' : 'text-tinta-500 line-through'}`}>
        {aprobado ? texto.final_text : texto.generated_text}</p>}
    {texto.reviewed_at && <p className="text-xs text-tinta-500">
      {aprobado ? 'Aprobado' : 'Descartado'} por {texto.reviewed_by_name} el {fechaHora(texto.reviewed_at)}.
    </p>}
  </article>
}

/**
 * US-42 — La bandeja del médico: lo que la IA escribió para sus pacientes.
 *
 * Nada de esto le llega al paciente hasta que el médico lo aprueba (regla 14
 * del Sprint 4). Se guarda lo que escribió el modelo y lo que quedó, para que
 * se vea qué se corrigió.
 */
export function TextosPorValidar() {
  const { token, puede } = useSesion()
  useTitulo('Textos por validar')
  const permitido = puede('ai.text.review')
  const [estado, setEstado] = useState<EstadoTexto>('draft')
  const [pagina, setPagina] = useState(1)
  const [textos, setTextos] = useState<TextoIa[]>([])
  const [total, setTotal] = useState(0)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)

  const recargar = useCallback(async (signal?: AbortSignal) => {
    setCargando(true)
    try {
      const datos = await verBandeja(estado, pagina, { token }, signal)
      setTextos(datos.results); setTotal(datos.count); setError(null)
    } catch (e) { if (!(e instanceof DOMException && e.name === 'AbortError')) setError(mensajeError(e)) }
    finally { if (!signal?.aborted) setCargando(false) }
  }, [estado, pagina, token])

  useEffect(() => {
    if (!permitido) return
    const c = new AbortController(); void recargar(c.signal); return () => c.abort()
  }, [permitido, recargar])

  const cambiarPestana = (e: EstadoTexto) => { setEstado(e); setPagina(1); setAviso(null) }

  const decidido = (t: TextoIa, mensaje: string) => {
    setAviso(mensaje)
    setTextos(lista => lista.filter(x => x.id !== t.id))
    setTotal(n => Math.max(0, n - 1))
  }

  if (!permitido) return <main className="mx-auto max-w-4xl px-5 py-10 text-tinta-500">Esta pantalla es del médico que valida los textos de sus pacientes.</main>

  return <main className="mx-auto max-w-4xl space-y-6 px-5 py-8 sm:py-10">
    <div className="surgir flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-marca-700 dark:text-marca-400">Historia clínica</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-tinta-900 dark:text-tinta-50">Textos por validar</h1>
        <p className="mt-1.5 max-w-2xl text-[0.9375rem] text-tinta-500">
          Lo que la IA redactó para tus pacientes a partir de tus atenciones. Ninguno les llega hasta que lo apruebes: corrígelo si hace falta, apruébalo o descártalo.
        </p>
      </div>
      <button type="button" className={SECONDARY} disabled={cargando} onClick={() => void recargar()}>
        <IconoCatalogo nombre="refresh" className="size-4" /> Actualizar</button>
    </div>

    <div role="tablist" aria-label="Estado de los textos" className="flex gap-1 border-b border-tinta-200 dark:border-tinta-800">
      {PESTANAS.map(p => <button key={p.estado} role="tab" type="button" aria-selected={estado === p.estado}
        onClick={() => cambiarPestana(p.estado)}
        className={`-mb-px border-b-2 px-4 py-2.5 text-sm font-medium transition ${estado === p.estado
          ? 'border-marca-600 text-marca-700 dark:text-marca-400'
          : 'border-transparent text-tinta-500 hover:text-tinta-800 dark:hover:text-tinta-200'}`}>
        {p.etiqueta}</button>)}
    </div>

    {aviso && <AvisoCatalogo mensaje={aviso} onCerrar={() => setAviso(null)} />}
    {error && <ErrorCatalogo mensaje={error} />}

    {cargando && textos.length === 0
      ? <p className="text-sm text-tinta-500">Cargando…</p>
      : textos.length === 0
        ? <div className={`${PANEL} text-center text-sm text-tinta-500`}>
          {estado === 'draft' ? 'No tienes textos pendientes. Cuando firmes una atención, su resumen aparecerá acá.'
            : estado === 'approved' ? 'Todavía no aprobaste ningún texto.' : 'No descartaste ningún texto.'}
        </div>
        : <div className="space-y-4">
          {textos.map(t => estado === 'draft'
            ? <Pendiente key={t.id} texto={t} onDecidido={decidido} />
            : <Decidido key={t.id} texto={t} />)}
        </div>}

    <Paginador pagina={pagina} total={total} cargando={cargando} onCambiar={setPagina} />
  </main>
}
