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
import { verHistorial, type Historial as DatosHistorial } from '@/api/atencion'
import { listarOpcionesDePaciente, type OpcionDePaciente } from '@/api/pacientes'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'
import { ErrorCatalogo, PANEL, mensajeError } from './catalogo_comun'
import { LineaDeTiempo, resumenHistorial } from './Historial'

export function MiHistoria() {
  const { token } = useSesion()
  useTitulo('Mi historia clínica')
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

  // La línea de tiempo se remonta al cambiar de persona (`key={elegido}`):
  // así el filtro no queda en una sucursal que la otra persona no tiene.
  const deQuien = opciones?.find(o => o.id === elegido)

  return <main className="mx-auto max-w-4xl space-y-6 px-5 py-8 sm:py-10">
    <div className="surgir flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-tinta-900 dark:text-tinta-50">Mi historia clínica</h1>
        <p className="mt-1.5 max-w-2xl text-[0.9375rem] text-tinta-500">
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
      {datos.encounters.length === 0
        ? <div className={`${PANEL} text-center text-sm text-tinta-500`}>Cuando un médico atienda y firme la consulta, aparece acá.</div>
        : <LineaDeTiempo key={elegido} datos={datos} />}
    </>}
  </main>
}
