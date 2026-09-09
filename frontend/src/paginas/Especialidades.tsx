import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { listarEspecialidades, type Especialidad } from '@/api/catalogo'
import { crearEspecialidad, editarEspecialidad, desactivarEspecialidad } from '@/api/catalogo_admin'
import { Boton } from '@/componentes/Boton'
import { Campo } from '@/componentes/Campo'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'
import {
  PANEL, INPUT, SECONDARY, DANGER, mensajeError, IconoCatalogo, CabeceraCatalogo,
  EstadoCatalogo, AvisoCatalogo, ErrorCatalogo, BuscadorCatalogo, ConfirmacionCatalogo,
} from './catalogo_comun'

type Draft = {name:string;description:string}
export function Especialidades() {
  const {token,puede}=useSesion()
  useTitulo('Especialidades')
  const leer=puede('catalog.specialty.read')
  const crear=puede('catalog.specialty.create')
  const editar=puede('catalog.specialty.update')
  const [items,setItems]=useState<Especialidad[]>([])
  const [loading,setLoading]=useState(true)
  const [saving,setSaving]=useState(false)
  const [error,setError]=useState<string|null>(null)
  const [success,setSuccess]=useState<string|null>(null)
  const [query,setQuery]=useState('')
  const [filter,setFilter]=useState('active')
  const [form,setForm]=useState<{id:string|null;value:Draft}|null>(null)
  const [confirm,setConfirm]=useState<Especialidad|null>(null)
  const contexto={token}
  const recargar=useCallback(async(signal?:AbortSignal)=>{
    setLoading(true)
    try {setItems(await listarEspecialidades({token},signal));setError(null)}
    catch(e){if(!(e instanceof DOMException&&e.name==='AbortError'))setError(mensajeError(e))}
    finally{if(!signal?.aborted)setLoading(false)}
  },[token])
  useEffect(()=>{
    if(!leer)return
    const c=new AbortController();void recargar(c.signal);return()=>c.abort()
  },[leer,recargar])
  const guardar=async(e:FormEvent)=>{
    e.preventDefault();if(!form||saving)return
    const value={name:form.value.name.trim(),description:form.value.description.trim()}
    if(!value.name){setError('Ingresá el nombre de la especialidad.');return}
    setSaving(true);setError(null)
    try{
      if(form.id)await editarEspecialidad(form.id,value,contexto)
      else await crearEspecialidad(value,contexto)
      setForm(null);setSuccess(form.id?'Especialidad actualizada correctamente.':'Especialidad registrada correctamente.')
      await recargar()
    }catch(e){setError(mensajeError(e))}
    finally{setSaving(false)}
  }
  const desactivar=async()=>{
    if(!confirm||saving)return
    setSaving(true);setError(null)
    try{
      await desactivarEspecialidad(confirm.id,contexto)
      setConfirm(null);setSuccess('Especialidad desactivada. Sus datos se conservaron.')
      await recargar()
    }catch(e){setConfirm(null);setError(mensajeError(e))}
    finally{setSaving(false)}
  }
  const filtered=items.filter(s=>(filter==='all'||(s.is_active)===(filter==='active'))&&
    `${s.name} ${s.description}`.toLowerCase().includes(query.toLowerCase().trim()))
  if(!leer)return <main className="mx-auto max-w-4xl px-5 py-10 text-tinta-500">No tenés permiso para consultar especialidades.</main>
  return <main className="mx-auto max-w-6xl space-y-6 px-5 py-8 sm:py-10">
    <CabeceraCatalogo titulo="Especialidades médicas" descripcion="Organizá las áreas de atención del centro médico y su descripción. Estas especialidades se utilizan para buscar y asignar profesionales.">
      {crear&&<Boton type="button" onClick={()=>{setError(null);setForm({id:null,value:{name:'',description:''}})}} className="w-auto"><IconoCatalogo nombre="plus" className="size-4"/> Nueva especialidad</Boton>}
    </CabeceraCatalogo>
    {success&&<AvisoCatalogo mensaje={success} onCerrar={()=>setSuccess(null)}/>}
    {error&&!form&&<ErrorCatalogo mensaje={error}/>}
    <div className="flex flex-wrap gap-2"><Link to="/especialidades" className="rounded-xl bg-marca-600 px-4 py-2 text-sm font-semibold text-white">Especialidades</Link><Link to="/profesionales" className={SECONDARY}>Profesionales</Link><Link to="/sucursales" className={SECONDARY}>Sucursales</Link></div>
    <section className={PANEL}>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3"><span className="grid size-11 place-items-center rounded-xl bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-300"><IconoCatalogo nombre="heart"/></span><div><h2 className="font-semibold text-tinta-900 dark:text-tinta-100">Catálogo de especialidades</h2><p className="text-sm text-tinta-500">{items.filter(s=>s.is_active).length} activas · {items.length} registradas</p></div></div>
        <button type="button" disabled={loading} onClick={()=>void recargar()} className={SECONDARY}><IconoCatalogo nombre="refresh" className="size-4"/> Actualizar</button>
      </div>
      <div className="mt-5"><BuscadorCatalogo valor={query} onCambio={setQuery} estado={filter} onEstado={setFilter}/></div>
      {loading?<p role="status" className="py-12 text-center text-sm text-tinta-500">Cargando especialidades…</p>:filtered.length===0?
        <div className="py-12 text-center"><span className="mx-auto grid size-14 place-items-center rounded-2xl bg-tinta-100 text-tinta-400 dark:bg-tinta-800"><IconoCatalogo nombre="heart" className="size-7"/></span><h3 className="mt-4 font-semibold">No se encontraron especialidades</h3><p className="mt-1 text-sm text-tinta-500">Registrá una especialidad o probá con otro filtro.</p></div>:
        <div className="mt-5 grid gap-3 md:grid-cols-2">{filtered.map(s=><article key={s.id} className="flex min-w-0 flex-col rounded-xl border border-tinta-200 p-4 transition hover:border-tinta-300 dark:border-tinta-800 dark:hover:border-tinta-700">
          <div className="flex items-start gap-3"><span className="grid size-10 shrink-0 place-items-center rounded-xl bg-tinta-100 text-tinta-600 dark:bg-tinta-800 dark:text-tinta-300"><IconoCatalogo nombre="heart"/></span><div className="min-w-0 flex-1"><h3 className="break-words font-semibold text-tinta-900 dark:text-tinta-100">{s.name}</h3><div className="mt-1"><EstadoCatalogo activo={s.is_active}/></div></div></div>
          <p className="mt-4 min-h-12 flex-1 whitespace-pre-wrap break-words text-sm leading-6 text-tinta-500">{s.description||'Sin descripción registrada.'}</p>
          <div className="mt-4 flex flex-wrap gap-2 border-t border-tinta-200 pt-3 dark:border-tinta-800">{editar&&<button type="button" className={SECONDARY} onClick={()=>{setError(null);setForm({id:s.id,value:{name:s.name,description:s.description}})}}><IconoCatalogo nombre="edit" className="size-4"/> Editar</button>}{editar&&s.is_active&&<button type="button" className={DANGER} onClick={()=>setConfirm(s)}>Desactivar</button>}</div>
        </article>)}</div>}
    </section>
    {form&&<div className="fixed inset-0 z-40 overflow-y-auto bg-black/60 p-3 sm:p-6" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget&&!saving){setForm(null);setError(null)}}}>
      <div role="dialog" aria-modal="true" aria-labelledby="especialidad-titulo" className="mx-auto my-4 w-full max-w-xl rounded-2xl bg-white shadow-2xl dark:bg-tinta-950">
        <div className="flex items-start justify-between gap-4 border-b border-tinta-200 p-5 sm:p-6 dark:border-tinta-800"><div><p className="text-xs font-semibold uppercase tracking-wider text-marca-700 dark:text-marca-400">Catálogo · US-12</p><h2 id="especialidad-titulo" className="mt-1 text-xl font-semibold">{form.id?'Editar especialidad':'Nueva especialidad'}</h2></div><button type="button" disabled={saving} onClick={()=>{setForm(null);setError(null)}} aria-label="Cerrar" className="rounded-lg p-2 text-tinta-500 hover:bg-tinta-100 dark:hover:bg-tinta-800"><IconoCatalogo nombre="close"/></button></div>
        <form onSubmit={e=>void guardar(e)}><div className="space-y-5 p-5 sm:p-6">{error&&<ErrorCatalogo mensaje={error}/>}<Campo etiqueta="Nombre de la especialidad" required maxLength={120} value={form.value.name} onChange={e=>setForm({...form,value:{...form.value,name:e.target.value}})} placeholder="Ej. Cardiología"/><label className="block space-y-1.5 text-sm"><span className="font-medium text-tinta-700 dark:text-tinta-300">Descripción</span><textarea className={`${INPUT} min-h-28 resize-y`} value={form.value.description} onChange={e=>setForm({...form,value:{...form.value,description:e.target.value}})} placeholder="Describe el área de atención…" maxLength={2000}/><span className="block text-xs text-tinta-500">Una descripción clara ayuda a identificar la especialidad.</span></label></div>
          <div className="flex justify-end gap-3 border-t border-tinta-200 bg-tinta-50 px-5 py-4 dark:border-tinta-800 dark:bg-tinta-900"><button type="button" disabled={saving} onClick={()=>{setForm(null);setError(null)}} className={SECONDARY}>Cancelar</button><Boton type="submit" cargando={saving} className="w-auto">{form.id?'Guardar cambios':'Registrar especialidad'}</Boton></div>
        </form>
      </div>
    </div>}
    {confirm&&<ConfirmacionCatalogo titulo="Desactivar especialidad" descripcion={`¿Querés desactivar ${confirm.name}? Los datos se conservarán. Si tiene profesionales activos asociados, el sistema rechazará la operación para proteger esas relaciones.`} trabajando={saving} onCancelar={()=>setConfirm(null)} onConfirmar={()=>void desactivar()}/>}
  </main>
}
