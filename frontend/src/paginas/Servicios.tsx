import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { listarEspecialidades, type Especialidad } from '@/api/catalogo'
import {
  TIPOS_SERVICIO, crearServicio, desactivarServicio, editarServicio, listarServicios,
  reindexarAsistente, type Servicio, type ServicioEscritura, type TipoServicio,
} from '@/api/servicios'
import { Boton } from '@/componentes/Boton'
import { Campo } from '@/componentes/Campo'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'
import {
  PANEL, INPUT, SECONDARY, DANGER, mensajeError, IconoCatalogo, CabeceraCatalogo,
  EstadoCatalogo, AvisoCatalogo, ErrorCatalogo, BuscadorCatalogo, ConfirmacionCatalogo,
  CampoSeleccion, Etiqueta,
} from './catalogo_comun'

/** El formulario guarda el precio como texto: vacío es "a consultar". */
type Draft = {
  name: string; kind: TipoServicio; specialty: string
  description: string; preparation: string; price: string
}
const VACIO: Draft = { name: '', kind: 'study', specialty: '', description: '', preparation: '', price: '' }

const aDraft = (s: Servicio): Draft => ({
  name: s.name, kind: s.kind, specialty: s.specialty ?? '', description: s.description,
  preparation: s.preparation, price: s.price ?? '',
})

function precio(s: Servicio) {
  if (s.price === null) return 'A consultar'
  const valor = Number(s.price)
  const texto = Number.isInteger(valor) ? String(valor) : valor.toFixed(2).replace('.', ',')
  return `${s.currency === 'BOB' ? 'Bs' : s.currency} ${texto}`
}

export function Servicios() {
  const { token, puede } = useSesion()
  useTitulo('Servicios y estudios')
  const leer = puede('catalog.service.read')
  const crear = puede('catalog.service.create')
  const editar = puede('catalog.service.update')
  const reindexar = puede('assistant.catalog.reindex')
  const [items, setItems] = useState<Servicio[]>([])
  const [especialidades, setEspecialidades] = useState<Especialidad[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [indexando, setIndexando] = useState(false)
  // Hubo cambios desde la última reindexación: el asistente todavía no los sabe.
  const [pendiente, setPendiente] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('active')
  const [form, setForm] = useState<{ id: string | null; value: Draft } | null>(null)
  const [confirm, setConfirm] = useState<Servicio | null>(null)
  const contexto = { token }

  const recargar = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    try { setItems(await listarServicios({ token }, signal)); setError(null) }
    catch (e) { if (!(e instanceof DOMException && e.name === 'AbortError')) setError(mensajeError(e)) }
    finally { if (!signal?.aborted) setLoading(false) }
  }, [token])

  useEffect(() => {
    if (!leer) return
    const c = new AbortController()
    void recargar(c.signal)
    // La especialidad es opcional: si no se pueden leer, el selector queda vacío.
    listarEspecialidades({ token }, c.signal).then(setEspecialidades).catch(() => {})
    return () => c.abort()
  }, [leer, recargar, token])

  const guardar = async (e: FormEvent) => {
    e.preventDefault(); if (!form || saving) return
    const v = form.value
    const value: ServicioEscritura = {
      name: v.name.trim(), kind: v.kind, specialty: v.specialty || null,
      description: v.description.trim(), preparation: v.preparation.trim(),
      price: v.price.trim() === '' ? null : v.price.trim().replace(',', '.'),
    }
    if (!value.name) { setError('Ingresá el nombre del servicio.'); return }
    setSaving(true); setError(null)
    try {
      if (form.id) await editarServicio(form.id, value, contexto)
      else await crearServicio(value, contexto)
      setForm(null); setPendiente(true)
      setSuccess(form.id ? 'Servicio actualizado correctamente.' : 'Servicio registrado correctamente.')
      await recargar()
    } catch (e) { setError(mensajeError(e)) }
    finally { setSaving(false) }
  }

  const desactivar = async () => {
    if (!confirm || saving) return
    setSaving(true); setError(null)
    try {
      await desactivarServicio(confirm.id, contexto)
      setConfirm(null); setPendiente(true)
      setSuccess('Servicio desactivado. Sus datos se conservaron.')
      await recargar()
    } catch (e) { setConfirm(null); setError(mensajeError(e)) }
    finally { setSaving(false) }
  }

  const actualizarAsistente = async () => {
    if (indexando) return
    setIndexando(true); setError(null)
    try {
      const r = await reindexarAsistente(contexto)
      setPendiente(false)
      setSuccess(`Asistente actualizado: ${r.branches} sedes, ${r.services} servicios y ${r.specialties} especialidades (${r.fragments} fragmentos).`)
    } catch (e) { setError(mensajeError(e)) }
    finally { setIndexando(false) }
  }

  const filtered = items.filter(s => (filter === 'all' || s.is_active === (filter === 'active')) &&
    `${s.name} ${s.description} ${s.preparation} ${s.specialty_name ?? ''}`.toLowerCase().includes(query.toLowerCase().trim()))
  const cambiar = (campo: keyof Draft, valor: string) => form && setForm({ ...form, value: { ...form.value, [campo]: valor } })

  if (!leer) return <main className="mx-auto max-w-4xl px-5 py-10 text-tinta-500">No tenés permiso para consultar servicios.</main>
  return <main className="mx-auto max-w-6xl space-y-6 px-5 py-8 sm:py-10">
    <CabeceraCatalogo titulo="Servicios y estudios" descripcion="Precio y preparación de cada consulta, estudio o procedimiento. Es lo que el asistente le contesta al paciente cuando pregunta cuánto cuesta o cómo tiene que ir.">
      <div className="flex flex-wrap gap-2">
        {reindexar && <button type="button" disabled={indexando} onClick={() => void actualizarAsistente()} className={SECONDARY}><IconoCatalogo nombre="refresh" className="size-4" /> {indexando ? 'Actualizando…' : 'Actualizar asistente'}</button>}
        {crear && <Boton type="button" onClick={() => { setError(null); setForm({ id: null, value: VACIO }) }} className="w-auto"><IconoCatalogo nombre="plus" className="size-4" /> Nuevo servicio</Boton>}
      </div>
    </CabeceraCatalogo>
    {success && <AvisoCatalogo mensaje={success} onCerrar={() => setSuccess(null)} />}
    {pendiente && reindexar && <div role="status" className="rounded-xl border border-tinta-200 bg-tinta-50 px-4 py-3 text-sm text-tinta-700 dark:border-tinta-700 dark:bg-tinta-900 dark:text-tinta-200">Hay cambios que el asistente todavía no conoce. Tocá <strong>Actualizar asistente</strong> cuando termines de cargar.</div>}
    {error && !form && <ErrorCatalogo mensaje={error} />}
    <div className="flex flex-wrap gap-2"><Link to="/especialidades" className={SECONDARY}>Especialidades</Link><Link to="/profesionales" className={SECONDARY}>Profesionales</Link><Link to="/sucursales" className={SECONDARY}>Sucursales</Link><Link to="/servicios" className="rounded-xl bg-marca-600 px-4 py-2 text-sm font-semibold text-white">Servicios</Link></div>
    <section className={PANEL}>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3"><span className="grid size-11 place-items-center rounded-xl bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-300"><IconoCatalogo nombre="building" /></span><div><h2 className="font-semibold text-tinta-900 dark:text-tinta-100">Catálogo de servicios</h2><p className="text-sm text-tinta-500">{items.filter(s => s.is_active).length} activos · {items.length} registrados</p></div></div>
        <button type="button" disabled={loading} onClick={() => void recargar()} className={SECONDARY}><IconoCatalogo nombre="refresh" className="size-4" /> Recargar</button>
      </div>
      <div className="mt-5"><BuscadorCatalogo valor={query} onCambio={setQuery} estado={filter} onEstado={setFilter} /></div>
      {loading ? <p role="status" className="py-12 text-center text-sm text-tinta-500">Cargando servicios…</p> : filtered.length === 0 ?
        <div className="py-12 text-center"><span className="mx-auto grid size-14 place-items-center rounded-2xl bg-tinta-100 text-tinta-400 dark:bg-tinta-800"><IconoCatalogo nombre="building" className="size-7" /></span><h3 className="mt-4 font-semibold">No se encontraron servicios</h3><p className="mt-1 text-sm text-tinta-500">Registrá un servicio o probá con otro filtro.</p></div> :
        <div className="mt-5 grid gap-3 md:grid-cols-2">{filtered.map(s => <article key={s.id} className="flex min-w-0 flex-col rounded-xl border border-tinta-200 p-4 transition hover:border-tinta-300 dark:border-tinta-800 dark:hover:border-tinta-700">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0"><h3 className="break-words font-semibold text-tinta-900 dark:text-tinta-100">{s.name}</h3><div className="mt-1 flex flex-wrap items-center gap-2"><EstadoCatalogo activo={s.is_active} /><Etiqueta>{s.kind_display}</Etiqueta>{s.specialty_name && <Etiqueta>{s.specialty_name}</Etiqueta>}</div></div>
            <span className="shrink-0 text-lg font-semibold text-marca-700 dark:text-marca-300">{precio(s)}</span>
          </div>
          <dl className="mt-4 flex-1 space-y-2 text-sm leading-6">
            <div><dt className="font-medium text-tinta-700 dark:text-tinta-300">Preparación</dt><dd className="whitespace-pre-wrap break-words text-tinta-500">{s.preparation || 'No requiere preparación.'}</dd></div>
            {s.description && <div><dt className="font-medium text-tinta-700 dark:text-tinta-300">Descripción</dt><dd className="whitespace-pre-wrap break-words text-tinta-500">{s.description}</dd></div>}
          </dl>
          <div className="mt-4 flex flex-wrap gap-2 border-t border-tinta-200 pt-3 dark:border-tinta-800">{editar && <button type="button" className={SECONDARY} onClick={() => { setError(null); setForm({ id: s.id, value: aDraft(s) }) }}><IconoCatalogo nombre="edit" className="size-4" /> Editar</button>}{editar && s.is_active && <button type="button" className={DANGER} onClick={() => setConfirm(s)}>Desactivar</button>}</div>
        </article>)}</div>}
    </section>
    {form && <div className="fixed inset-0 z-40 overflow-y-auto bg-black/60 p-3 sm:p-6" role="presentation" onMouseDown={e => { if (e.target === e.currentTarget && !saving) { setForm(null); setError(null) } }}>
      <div role="dialog" aria-modal="true" aria-labelledby="servicio-titulo" className="mx-auto my-4 w-full max-w-xl rounded-2xl bg-white shadow-2xl dark:bg-tinta-950">
        <div className="flex items-start justify-between gap-4 border-b border-tinta-200 p-5 sm:p-6 dark:border-tinta-800"><div><p className="text-sm font-medium text-marca-700 dark:text-marca-400">Catálogo</p><h2 id="servicio-titulo" className="mt-1 text-xl font-semibold">{form.id ? 'Editar servicio' : 'Nuevo servicio'}</h2></div><button type="button" disabled={saving} onClick={() => { setForm(null); setError(null) }} aria-label="Cerrar" className="rounded-lg p-2 text-tinta-500 hover:bg-tinta-100 dark:hover:bg-tinta-800"><IconoCatalogo nombre="close" /></button></div>
        <form onSubmit={e => void guardar(e)}><div className="space-y-5 p-5 sm:p-6">
          {error && <ErrorCatalogo mensaje={error} />}
          <Campo etiqueta="Nombre del servicio" required maxLength={120} value={form.value.name} onChange={e => cambiar('name', e.target.value)} placeholder="Ej. Análisis de sangre" />
          <div className="grid gap-4 sm:grid-cols-2">
            <CampoSeleccion etiqueta="Tipo"><select className={INPUT} value={form.value.kind} onChange={e => cambiar('kind', e.target.value)}>{TIPOS_SERVICIO.map(t => <option key={t.valor} value={t.valor}>{t.etiqueta}</option>)}</select></CampoSeleccion>
            <CampoSeleccion etiqueta="Especialidad (opcional)"><select className={INPUT} value={form.value.specialty} onChange={e => cambiar('specialty', e.target.value)}><option value="">Ninguna</option>{especialidades.filter(s => s.is_active || s.id === form.value.specialty).map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></CampoSeleccion>
          </div>
          <label className="block space-y-1.5 text-sm"><span className="font-medium text-tinta-700 dark:text-tinta-300">Precio en Bs</span><input className={INPUT} inputMode="decimal" value={form.value.price} onChange={e => cambiar('price', e.target.value)} placeholder="Ej. 80" pattern="[0-9]+([.,][0-9]{1,2})?" /><span className="block text-xs text-tinta-500">Dejalo vacío si el precio se informa en la consulta: el asistente dirá «a consultar».</span></label>
          <label className="block space-y-1.5 text-sm"><span className="font-medium text-tinta-700 dark:text-tinta-300">Preparación previa</span><textarea className={`${INPUT} min-h-24 resize-y`} value={form.value.preparation} onChange={e => cambiar('preparation', e.target.value)} placeholder="Ej. Ayuno de 8 horas: sólo agua desde la noche anterior." maxLength={2000} /><span className="block text-xs text-tinta-500">Escribila como se la dirías al paciente: es la frase que el asistente le va a mostrar.</span></label>
          <label className="block space-y-1.5 text-sm"><span className="font-medium text-tinta-700 dark:text-tinta-300">Descripción</span><textarea className={`${INPUT} min-h-20 resize-y`} value={form.value.description} onChange={e => cambiar('description', e.target.value)} placeholder="Qué es y qué incluye…" maxLength={2000} /></label>
        </div>
          <div className="flex justify-end gap-3 border-t border-tinta-200 bg-tinta-50 px-5 py-4 dark:border-tinta-800 dark:bg-tinta-900"><button type="button" disabled={saving} onClick={() => { setForm(null); setError(null) }} className={SECONDARY}>Cancelar</button><Boton type="submit" cargando={saving} className="w-auto">{form.id ? 'Guardar cambios' : 'Registrar servicio'}</Boton></div>
        </form>
      </div>
    </div>}
    {confirm && <ConfirmacionCatalogo titulo="Desactivar servicio" descripcion={`¿Querés desactivar ${confirm.name}? Los datos se conservarán y el asistente dejará de ofrecerlo cuando lo actualices.`} trabajando={saving} onCancelar={() => setConfirm(null)} onConfirmar={() => void desactivar()} />}
  </main>
}
