import { useState } from 'react'
import { Link } from 'react-router-dom'
import { verResumenHistorial, type ResumenHistorial } from '@/api/atencion'
import { useSesion } from '@/sesion/useSesion'
import { ErrorCatalogo, PANEL, SECONDARY, mensajeError } from './catalogo_comun'

const fecha = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString('es-BO', { dateStyle: 'medium' })

const ORIGEN: Record<ResumenHistorial['generated_by'], string> = {
  gemini: 'Redactado con IA a partir de las atenciones citadas. Verifícalo antes de decidir.',
  plantilla: 'Sin IA en este momento: son los diagnósticos copiados tal cual de cada atención.',
  sin_datos: '',
}

/**
 * US-41 — El resumen del historial, antes de la consulta.
 *
 * Se pide con un botón y no al abrir la página: cada resumen es una llamada al
 * modelo, y el médico que ya conoce al paciente no la necesita.
 */
export function PanelResumenHistorial({ pacienteId }: { pacienteId: string }) {
  const { token } = useSesion()
  const [datos, setDatos] = useState<ResumenHistorial | null>(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const pedir = async () => {
    setCargando(true); setError(null)
    try { setDatos(await verResumenHistorial(pacienteId, { token })) }
    catch (e) { setError(mensajeError(e)) }
    finally { setCargando(false) }
  }

  const fuente = (ref: string) => datos?.sources.find(f => f.ref === ref)
  const graves = datos?.alerts.allergies ?? []

  return <section className={PANEL} aria-labelledby="resumen-titulo">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 id="resumen-titulo" className="font-semibold text-tinta-900 dark:text-tinta-100">Resumen del historial</h2>
        <p className="mt-0.5 text-sm text-tinta-500">Las últimas atenciones firmadas, de todas las sucursales, en pocas líneas.</p>
      </div>
      <button type="button" className={SECONDARY} onClick={() => void pedir()} disabled={cargando}>
        {cargando ? 'Generando…' : datos ? 'Volver a generar' : 'Generar resumen'}
      </button>
    </div>

    {error && <div className="mt-3"><ErrorCatalogo mensaje={error} /></div>}

    {datos && <div className="mt-4 space-y-4">
      {graves.length > 0 && <p className="rounded-xl bg-alerta-50 px-3.5 py-2.5 text-sm text-alerta-800 dark:bg-alerta-500/10 dark:text-alerta-200">
        <span className="font-semibold">Alergias: </span>
        {graves.map(a => `${a.description}${a.severity_label ? ` (${a.severity_label.toLowerCase()})` : ''}`).join(', ')}
      </p>}

      {datos.generated_by === 'sin_datos'
        ? <p className="text-sm text-tinta-500">El paciente no tiene atenciones firmadas todavía.</p>
        : <>
          <ul className="space-y-2 text-[0.9375rem] leading-6 text-tinta-800 dark:text-tinta-100">
            {datos.sentences.map((o, i) => <li key={i}>
              {o.text}{' '}
              {o.refs.map(r => { const f = fuente(r); return <span key={r} title={f ? `${fecha(f.date)} · ${f.branch} · ${f.practitioner}` : r}
                className="ml-0.5 inline-block rounded-md bg-marca-50 px-1.5 text-xs font-medium text-marca-700 dark:bg-marca-950 dark:text-marca-300">{r}</span> })}
            </li>)}
          </ul>
          <p className="text-xs text-tinta-500">
            {ORIGEN[datos.generated_by]}
            {datos.discarded > 0 && ` Se descartaron ${datos.discarded} ${datos.discarded === 1 ? 'oración' : 'oraciones'} que no citaban una atención.`}
          </p>
          <details className="text-sm">
            <summary className="cursor-pointer font-medium text-tinta-700 dark:text-tinta-300">Atenciones citadas ({datos.sources.length})</summary>
            <ul className="mt-2 space-y-1 text-tinta-600 dark:text-tinta-300">
              {datos.sources.map(f => <li key={f.ref}><span className="font-medium">{f.ref}</span> · {fecha(f.date)} · {f.branch} · {f.practitioner}{f.diagnosis && ` — ${f.diagnosis}`}</li>)}
            </ul>
            <Link to={`/historial/${pacienteId}`} className="mt-2 inline-block font-medium text-marca-700 hover:underline dark:text-marca-400">Abrir el historial completo →</Link>
          </details>
        </>}
    </div>}
  </section>
}
