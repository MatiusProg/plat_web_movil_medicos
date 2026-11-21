/**
 * US-25 — "Mi historia clínica": lo que escribieron los médicos, visto por el
 * propio paciente.
 *
 * Es el mismo endpoint que usa el médico (`/encounters/history/<paciente>/`):
 * el backend da alcance "propio" al paciente y a quien tiene a su cargo a un
 * dependiente (US-07), y 404 a cualquier otro. Arriba va el selector de
 * "¿de quién?", igual que en la reserva y en el móvil.
 *
 * No confundir con los antecedentes (US-08), que el paciente declara. Esto lo
 * registró y firmó un médico, y acá sólo se lee.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { verHistorial, type Historial as DatosHistorial } from '@/api/atencion'
import { listarOpcionesDePaciente, type OpcionDePaciente } from '@/api/pacientes'
import { verResumenesAprobados, type ResumenAprobado } from '@/api/textos_ia'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'
import { CalificarAtencion } from './CalificarAtencion'
import { GraficoSigno } from './EvolucionSignos'
import { VerSignos } from './SignosVitales'
import { SERIES, puntosDe, ultimaMedicion } from './signos_vitales'
import { ErrorCatalogo, PANEL, mensajeError } from './catalogo_comun'
import { LineaDeTiempo, resumenHistorial } from './Historial'

export function MiHistoria() {
  const { token, puede } = useSesion()
  useTitulo('Mi historia clínica')
  const chat = puede('encounters.chat')
  const [opciones, setOpciones] = useState<OpcionDePaciente[] | null>(null)
  const [elegido, setElegido] = useState<string>('')
  const [datos, setDatos] = useState<DatosHistorial | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const c = new AbortController()
    listarOpcionesDePaciente({ token }, c.signal)
      .then(o => { setOpciones(o); setElegido(o[0]?.id ?? '') })
      .catch(e => { if (!(e instanceof DOMException)) setError(mensajeError(e)) })
    return () => c.abort()
  }, [token])

  useEffect(() => {
    if (!elegido) return
    const c = new AbortController()
    verHistorial(elegido, { token }, c.signal)
      .then(d => { setDatos(d); setError(null) })
      .catch(e => { if (!(e instanceof DOMException)) setError(mensajeError(e)) })
    return () => c.abort()
  }, [elegido, token])

  // US-39: los resúmenes que su médico aprobó, igual que en el móvil. Si no
  // se pueden traer, la historia se ve igual sin ellos: son una ayuda.
  const [resumenes, setResumenes] = useState<Map<string, ResumenAprobado>>(new Map())
  useEffect(() => {
    setResumenes(new Map())
    if (!elegido || !datos?.encounters.length) return
    const c = new AbortController()
    verResumenesAprobados(elegido, { token }, c.signal).then(setResumenes).catch(() => {})
    return () => c.abort()
  }, [elegido, token, datos])

  // La línea de tiempo se remonta al cambiar de persona (`key={elegido}`):
  // así el filtro no queda en una sucursal que la otra persona no tiene.
  const deQuien = opciones?.find(o => o.id === elegido)

  return <main className="mx-auto max-w-4xl space-y-6 px-5 py-8 sm:py-10">
    <div className="surgir flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-tinta-900 dark:text-tinta-50">Mi historia clínica</h1>
        <p className="mt-1.5 max-w-2xl text-[1.0625rem] text-tinta-500">
          Lo que registraron y firmaron los médicos que te atendieron, de todas las sucursales. Para cambiar algo, habla con tu médico.
        </p>
      </div>
      {opciones && opciones.length > 1 && <label className="text-sm text-tinta-600 dark:text-tinta-300">
        <span className="block font-medium">¿De quién es?</span>
        <select value={elegido} onChange={e => { setDatos(null); setElegido(e.target.value) }}
          className="mt-1 rounded-lg border border-tinta-200 bg-white px-3 py-2 text-tinta-900 dark:border-tinta-700 dark:bg-tinta-900 dark:text-tinta-50">
          {opciones.map(o => <option key={o.id} value={o.id}>{o.is_self ? o.full_name : `${o.full_name} · ${o.relationship_label}`}</option>)}
        </select>
      </label>}
    </div>

    {error && <ErrorCatalogo mensaje={error} />}
    {!error && !datos && <p role="status" className="text-sm text-tinta-500">Cargando tu historia…</p>}

    {datos && <>
      <p className="text-sm font-medium text-tinta-700 dark:text-tinta-200">
        {resumenHistorial(datos, deQuien && !deQuien.is_self
          ? `${deQuien.full_name} todavía no tiene atenciones firmadas.`
          : 'Todavía no tienes atenciones firmadas.')}
      </p>
      <MisSignosVitales key={elegido} datos={datos} />
      {datos.encounters.length === 0
        ? <div className={`${PANEL} text-center text-sm text-tinta-500`}>Cuando un médico atienda y firme la consulta, aparece acá.</div>
        : <LineaDeTiempo key={elegido} datos={datos}
          cabeza={e => { const r = resumenes.get(e.id); return r && <ResumenDeLaConsulta resumen={r} /> }}
          pie={e => <>
            {/* US-48: la calificación, remontada al cambiar de persona. */}
            <CalificarAtencion key={`${elegido}-${e.id}`} encuentroId={e.id} inicial={e.rating ?? null} />
            {chat && <Link to={`/consultas/${e.id}`}
              className="mt-3 inline-flex text-sm font-medium text-marca-700 hover:underline dark:text-marca-400">
              Escribir al médico sobre esta atención →</Link>}
          </>} />}
    </>}
  </main>
}

/**
 * US-53 — «Mis signos vitales»: la última medición y cómo vienen la presión y
 * el peso. Sin signos tomados, la sección no aparece.
 */
function MisSignosVitales({ datos }: { datos: DatosHistorial }) {
  const ultima = ultimaMedicion(datos.encounters)
  if (!ultima) return null
  const fecha = new Date(ultima.appointment_starts_at).toLocaleDateString('es-BO', { day: 'numeric', month: 'long', year: 'numeric' })
  const graficas = SERIES.filter(s => s.id === 'presion' || s.id === 'weight_kg')
    .map(s => ({ serie: s, puntos: puntosDe(s, datos.encounters) })).filter(g => g.puntos.length > 0)
  return <section className={`${PANEL} space-y-5`} aria-labelledby="mis-signos">
    <div>
      <h2 id="mis-signos" className="font-semibold text-tinta-900 dark:text-tinta-50">Mis signos vitales</h2>
      <p className="mt-1 text-sm text-tinta-500">Última medición: {fecha}, {ultima.practitioner_name}.</p>
    </div>
    <VerSignos signos={ultima.vital_signs} />
    {ultima.amendments.some(a => a.section === 'vital_signs') && <p className="text-sm text-tinta-500">Tu médico agregó una corrección: la ves en esa atención, más abajo.</p>}
    {graficas.map(g => <div key={g.serie.id} className="space-y-2">
      <h3 className="text-sm font-medium text-tinta-700 dark:text-tinta-300">{g.serie.etiqueta}{g.serie.unidad && ` (${g.serie.unidad})`}</h3>
      <GraficoSigno serie={g.serie} puntos={g.puntos} />
    </div>)}
  </section>
}

/** US-39: el resumen en palabras simples, arriba de lo firmado, que sigue completo debajo. */
function ResumenDeLaConsulta({ resumen }: { resumen: ResumenAprobado }) {
  const aprobado = resumen.approved_at
    ? new Date(resumen.approved_at).toLocaleString('es-BO', { dateStyle: 'medium', timeStyle: 'short', hourCycle: 'h23' })
    : null
  return <section className="mt-3 rounded-xl bg-marca-50 px-4 py-3 dark:bg-marca-950/40" aria-label="Resumen de tu consulta">
    <h3 className="text-sm font-semibold text-marca-800 dark:text-marca-200">Resumen de tu consulta</h3>
    <p className="mt-1.5 whitespace-pre-wrap text-sm text-tinta-800 dark:text-tinta-100">{resumen.text}</p>
    <p className="mt-2 text-xs text-tinta-500">
      Redactado con IA y revisado por {resumen.practitioner_name}{aprobado && ` · ${aprobado}`}
    </p>
  </section>
}
