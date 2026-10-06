import { useCallback, useEffect, useState } from 'react'
import {
  descargarCopia, generarRespaldo, inspeccionarCopia, inspeccionarRespaldo, restaurarCopia,
  restaurarRespaldo, verHistorial, verPolitica,
  type Inspeccion, type PoliticaRespaldo, type RegistroRespaldo, type ResultadoRestauracion,
} from '@/api/respaldos'
import { Boton } from '@/componentes/Boton'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'
import { AvisoCatalogo, ErrorCatalogo, PANEL, SECONDARY, mensajeError } from './catalogo_comun'

const fechaHora = (iso: string) =>
  new Date(iso).toLocaleString('es-BO', { dateStyle: 'medium', timeStyle: 'short', hourCycle: 'h23' })

function tamano(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

/** De dónde sale lo que se va a restaurar: un archivo subido o una copia automática guardada. */
type Origen = { tipo: 'archivo'; archivo: File } | { tipo: 'copia'; registro: RegistroRespaldo }

/** Lo que la historia clínica o un pago no dejaron borrar, en una frase. */
function conservado(resultado: ResultadoRestauracion, inspeccion: Inspeccion) {
  const partes = Object.entries(resultado.kept ?? {}).filter(([, n]) => n > 0)
    .map(([t, n]) => `${n} ${(inspeccion.labels[t] ?? t).toLowerCase()}`)
  return partes.length
    ? ` Se conservaron ${partes.join(', ')} posteriores a la copia, porque no se pueden borrar: la historia clínica, los pagos o tu propio acceso dependen de ellos. Los que tienen baja lógica quedaron inactivos.`
    : ''
}

/** Característica general 6 — La copia de la organización, según su plan. */
export function Respaldos() {
  const { token, puede } = useSesion()
  useTitulo('Copias de seguridad')
  const respaldar = puede('backups.backup.create')
  const restaurar = puede('backups.backup.restore')
  const [politica, setPolitica] = useState<PoliticaRespaldo | null>(null)
  const [historial, setHistorial] = useState<RegistroRespaldo[]>([])
  const [trabajando, setTrabajando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)
  const [origen, setOrigen] = useState<Origen | null>(null)
  const [inspeccion, setInspeccion] = useState<Inspeccion | null>(null)
  const [confirmacion, setConfirmacion] = useState('')

  const cargar = useCallback(async (signal?: AbortSignal) => {
    try {
      const [p, h] = await Promise.all([verPolitica({ token }, signal), verHistorial({ token }, signal)])
      setPolitica(p); setHistorial(h); setError(null)
    } catch (e) { if (!(e instanceof DOMException && e.name === 'AbortError')) setError(mensajeError(e)) }
  }, [token])

  useEffect(() => {
    if (!respaldar) return
    const c = new AbortController(); void cargar(c.signal); return () => c.abort()
  }, [respaldar, cargar])

  const generar = async () => {
    setTrabajando(true); setError(null)
    try { const nombre = await generarRespaldo({ token }); setAviso(`Copia generada y descargada: ${nombre}. Guardala en un lugar seguro: trae todos los datos de la organización.`); await cargar() }
    catch (e) { setError(mensajeError(e)); await cargar() }
    finally { setTrabajando(false) }
  }

  const descargar = async (registro: RegistroRespaldo) => {
    setTrabajando(true); setError(null)
    try { const nombre = await descargarCopia(registro.id, { token }); setAviso(`Copia descargada: ${nombre}.`) }
    catch (e) { setError(mensajeError(e)); await cargar() }
    finally { setTrabajando(false) }
  }

  const elegir = async (nuevo: Origen | null) => {
    setOrigen(nuevo); setInspeccion(null); setConfirmacion(''); setError(null)
    if (!nuevo) return
    setTrabajando(true)
    try {
      setInspeccion(nuevo.tipo === 'archivo'
        ? await inspeccionarRespaldo(nuevo.archivo, { token })
        : await inspeccionarCopia(nuevo.registro.id, { token }))
    } catch (e) { setError(mensajeError(e)) }
    finally { setTrabajando(false) }
  }

  const confirmarRestauracion = async () => {
    if (!origen || !inspeccion) return
    setTrabajando(true); setError(null)
    try {
      const resultado = origen.tipo === 'archivo'
        ? await restaurarRespaldo(origen.archivo, { token })
        : await restaurarCopia(origen.registro.id, { token })
      setAviso(`Datos restaurados al ${inspeccion.generated_at ? fechaHora(inspeccion.generated_at) : 'momento de la copia'}.${conservado(resultado, inspeccion)}`)
      setOrigen(null); setInspeccion(null); setConfirmacion('')
      await cargar()
    } catch (e) { setError(mensajeError(e)) }
    finally { setTrabajando(false) }
  }

  if (!respaldar) return <main className="mx-auto max-w-4xl px-5 py-10 text-tinta-500">No tenés permiso para gestionar copias de seguridad.</main>
  const palabra = inspeccion?.organization.slug ?? ''
  const automatica = politica?.automatic
  const guardadas = historial.filter(r => r.downloadable)
  return <main className="mx-auto max-w-4xl space-y-6 px-5 py-8 sm:py-10">
    <div className="surgir">
      <p className="text-sm font-medium text-marca-700 dark:text-marca-400">Organización</p>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight text-tinta-900 dark:text-tinta-50">Copias de seguridad</h1>
      <p className="mt-1.5 max-w-2xl text-[0.9375rem] text-tinta-500">Una copia con todos los datos de tu organización, para guardarla fuera del sistema y poder restaurarla si algo sale mal.</p>
    </div>
    {aviso && <AvisoCatalogo mensaje={aviso} onCerrar={() => setAviso(null)} />}
    {error && <ErrorCatalogo mensaje={error} />}

    <section className={PANEL} aria-labelledby="generar-titulo">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-xl">
          <h2 id="generar-titulo" className="font-semibold text-tinta-900 dark:text-tinta-100">Generar una copia</h2>
          {politica && <>
            <p className="mt-1 text-sm text-tinta-600 dark:text-tinta-300">{politica.description}</p>
            {politica.last_backup_at && <p className="mt-1 text-sm text-tinta-500">Última copia manual: {fechaHora(politica.last_backup_at)}.</p>}
            {!politica.allowed_now && politica.next_available_at && <p className="mt-1 text-sm font-medium text-amber-700 dark:text-amber-300">La próxima se puede generar desde el {fechaHora(politica.next_available_at)}.</p>}
            {politica.plan_code && politica.plan_code !== 'premium' && <p className="mt-2 text-xs text-tinta-500">Con el plan Premium podés generar copias a voluntad.</p>}
          </>}
        </div>
        <Boton type="button" className="w-auto" cargando={trabajando} disabled={!politica?.allowed_now} onClick={() => void generar()}>Generar y descargar</Boton>
      </div>
    </section>

    <section className={PANEL} aria-labelledby="automaticas-titulo">
      <h2 id="automaticas-titulo" className="font-semibold text-tinta-900 dark:text-tinta-100">Copias automáticas</h2>
      {automatica && <>
        <p className="mt-1 text-sm text-tinta-600 dark:text-tinta-300">{automatica.description} Se guardan cifradas en la plataforma: no hace falta que hagas nada.</p>
        {automatica.enabled && <p className="mt-1 text-sm text-tinta-500">
          {automatica.last_at ? `Última: ${fechaHora(automatica.last_at)}.` : 'Todavía no se generó ninguna: la primera sale en menos de una hora.'}
          {automatica.next_at && ` Próxima: ${fechaHora(automatica.next_at)}.`}
        </p>}
      </>}
      {guardadas.length > 0 && <ul className="mt-4 divide-y divide-tinta-200 rounded-xl border border-tinta-200 dark:divide-tinta-800 dark:border-tinta-800">
        {guardadas.map(r => <li key={r.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm">
          <div>
            <p className="font-medium text-tinta-800 dark:text-tinta-100">{fechaHora(r.created_at)}</p>
            <p className="text-tinta-500 tabular-nums">{r.total_rows} filas · {tamano(r.size_bytes)}</p>
          </div>
          <div className="flex gap-2">
            <button type="button" className={SECONDARY} disabled={trabajando} onClick={() => void descargar(r)}>Descargar</button>
            {restaurar && <button type="button" className={SECONDARY} disabled={trabajando}
              onClick={() => { void elegir({ tipo: 'copia', registro: r }); document.getElementById('restaurar-titulo')?.scrollIntoView({ behavior: 'smooth' }) }}>Restaurar…</button>}
          </div>
        </li>)}
      </ul>}
    </section>

    {restaurar && <section className={PANEL} aria-labelledby="restaurar-titulo">
      <h2 id="restaurar-titulo" className="font-semibold text-tinta-900 dark:text-tinta-100">Restaurar desde una copia</h2>
      <p className="mt-1 text-sm text-tinta-500">Vuelve los datos de la organización al momento de la copia. No depende del plan. La bitácora no se toca, y la historia clínica y los pagos no se borran nunca: lo que falte se agrega.</p>
      <p className="mt-3 text-sm text-tinta-600 dark:text-tinta-300">Elegí una copia automática de arriba («Restaurar…») o subí un archivo descargado:</p>
      <input type="file" accept="application/json,.json" className="mt-2 block text-sm"
        onChange={e => { const f = e.target.files?.[0]; void elegir(f ? { tipo: 'archivo', archivo: f } : null) }} />
      {origen?.tipo === 'copia' && <p className="mt-3 text-sm font-medium text-tinta-700 dark:text-tinta-200">Copia automática del {fechaHora(origen.registro.created_at)}
        <button type="button" className="ml-2 text-xs font-normal text-marca-700 underline dark:text-marca-400" onClick={() => void elegir(null)}>Quitar</button></p>}
      {inspeccion && <div className="mt-4 space-y-3 rounded-xl border border-tinta-200 p-4 text-sm dark:border-tinta-800">
        <p><strong>{inspeccion.organization.name ?? 'Organización desconocida'}</strong>{inspeccion.generated_at && ` · copia del ${fechaHora(inspeccion.generated_at)}`}</p>
        {!inspeccion.belongs_to_my_organization
          ? <ErrorCatalogo mensaje="Este archivo es de otra organización: no se puede restaurar acá." />
          : <>
            <ul className="grid gap-1 sm:grid-cols-2">{Object.entries(inspeccion.counts).filter(([, n]) => n > 0).map(([t, n]) =>
              <li key={t} className="text-tinta-600 dark:text-tinta-300">{inspeccion.labels[t] ?? t}: {n}</li>)}</ul>
            <label className="block space-y-1.5"><span className="font-medium text-tinta-700 dark:text-tinta-300">Para confirmar, escribí <code>{palabra}</code></span>
              <input className="w-full rounded-xl border border-tinta-300 bg-white px-3.5 py-2.5 dark:border-tinta-700 dark:bg-tinta-900" value={confirmacion} onChange={e => setConfirmacion(e.target.value)} /></label>
            <button type="button" disabled={trabajando || confirmacion !== palabra} onClick={() => void confirmarRestauracion()}
              className="rounded-xl bg-alerta-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">Restaurar y reemplazar los datos</button>
          </>}
      </div>}
    </section>}

    <section className={PANEL} aria-labelledby="historial-titulo">
      <div className="flex items-center justify-between gap-4"><h2 id="historial-titulo" className="font-semibold text-tinta-900 dark:text-tinta-100">Historial</h2>
        <button type="button" className={SECONDARY} onClick={() => void cargar()}>Actualizar</button></div>
      {historial.length === 0 ? <p className="mt-3 text-sm text-tinta-500">Todavía no se generó ninguna copia.</p> :
        <div className="mt-3 overflow-x-auto"><table className="w-full text-left text-sm">
          <thead className="text-tinta-500"><tr><th className="py-2 pr-4 font-medium">Fecha</th><th className="py-2 pr-4 font-medium">Tipo</th><th className="py-2 pr-4 font-medium">Origen</th><th className="py-2 pr-4 font-medium">Quién</th><th className="py-2 pr-4 font-medium">Filas</th><th className="py-2 font-medium">Tamaño</th></tr></thead>
          <tbody className="divide-y divide-tinta-200 dark:divide-tinta-800">{historial.map(r => <tr key={r.id}>
            <td className="py-2 pr-4 whitespace-nowrap">{fechaHora(r.created_at)}</td><td className="py-2 pr-4">{r.kind_label}</td>
            <td className="py-2 pr-4">{r.kind === 'backup' ? r.trigger_label : '—'}{r.trigger === 'automatic' && !r.downloadable && <span className="ml-1 text-xs text-tinta-400">(ya no se conserva)</span>}</td>
            <td className="py-2 pr-4">{r.performed_by_email ?? (r.trigger === 'automatic' ? 'El sistema' : '—')}</td><td className="py-2 pr-4 tabular-nums">{r.total_rows}</td>
            <td className="py-2 tabular-nums">{r.kind === 'backup' ? tamano(r.size_bytes) : '—'}</td></tr>)}</tbody>
        </table></div>}
    </section>
  </main>
}
