import { useCallback, useEffect, useState } from 'react'
import {
  generarRespaldo, inspeccionarRespaldo, restaurarRespaldo, verHistorial, verPolitica,
  type Inspeccion, type PoliticaRespaldo, type RegistroRespaldo,
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
  const [archivo, setArchivo] = useState<File | null>(null)
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

  const elegir = async (f: File | null) => {
    setArchivo(f); setInspeccion(null); setConfirmacion(''); setError(null)
    if (!f) return
    setTrabajando(true)
    try { setInspeccion(await inspeccionarRespaldo(f, { token })) }
    catch (e) { setError(mensajeError(e)) }
    finally { setTrabajando(false) }
  }

  const confirmarRestauracion = async () => {
    if (!archivo || !inspeccion) return
    setTrabajando(true); setError(null)
    try {
      await restaurarRespaldo(archivo, { token })
      setAviso(`Datos restaurados al ${inspeccion.generated_at ? fechaHora(inspeccion.generated_at) : 'momento de la copia'}.`)
      setArchivo(null); setInspeccion(null); setConfirmacion('')
      await cargar()
    } catch (e) { setError(mensajeError(e)) }
    finally { setTrabajando(false) }
  }

  if (!respaldar) return <main className="mx-auto max-w-4xl px-5 py-10 text-tinta-500">No tenés permiso para gestionar copias de seguridad.</main>
  const palabra = inspeccion?.organization.slug ?? ''
  return <main className="mx-auto max-w-4xl space-y-6 px-5 py-8 sm:py-10">
    <div className="surgir">
      <p className="text-sm font-medium text-marca-700 dark:text-marca-400">Característica general 6</p>
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
            {politica.last_backup_at && <p className="mt-1 text-sm text-tinta-500">Última copia: {fechaHora(politica.last_backup_at)}.</p>}
            {!politica.allowed_now && politica.next_available_at && <p className="mt-1 text-sm font-medium text-amber-700 dark:text-amber-300">La próxima se puede generar desde el {fechaHora(politica.next_available_at)}.</p>}
            {politica.plan_code && politica.plan_code !== 'premium' && <p className="mt-2 text-xs text-tinta-500">Con el plan Premium podés generar copias a voluntad.</p>}
          </>}
        </div>
        <Boton type="button" className="w-auto" cargando={trabajando} disabled={!politica?.allowed_now} onClick={() => void generar()}>Generar y descargar</Boton>
      </div>
    </section>

    {restaurar && <section className={PANEL} aria-labelledby="restaurar-titulo">
      <h2 id="restaurar-titulo" className="font-semibold text-tinta-900 dark:text-tinta-100">Restaurar desde una copia</h2>
      <p className="mt-1 text-sm text-tinta-500">Reemplaza <strong>todos</strong> los datos de la organización por los del archivo. No depende del plan. La bitácora no se toca.</p>
      <input type="file" accept="application/json,.json" className="mt-4 block text-sm" onChange={e => void elegir(e.target.files?.[0] ?? null)} />
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
          <thead className="text-tinta-500"><tr><th className="py-2 pr-4 font-medium">Fecha</th><th className="py-2 pr-4 font-medium">Tipo</th><th className="py-2 pr-4 font-medium">Quién</th><th className="py-2 pr-4 font-medium">Filas</th><th className="py-2 font-medium">Tamaño</th></tr></thead>
          <tbody className="divide-y divide-tinta-200 dark:divide-tinta-800">{historial.map(r => <tr key={r.id}>
            <td className="py-2 pr-4 whitespace-nowrap">{fechaHora(r.created_at)}</td><td className="py-2 pr-4">{r.kind_label}</td>
            <td className="py-2 pr-4">{r.performed_by_email ?? '—'}</td><td className="py-2 pr-4 tabular-nums">{r.total_rows}</td>
            <td className="py-2 tabular-nums">{r.kind === 'backup' ? tamano(r.size_bytes) : '—'}</td></tr>)}</tbody>
        </table></div>}
    </section>
  </main>
}
