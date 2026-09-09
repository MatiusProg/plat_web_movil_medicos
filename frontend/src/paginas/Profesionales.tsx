import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { listarEspecialidades, listarSucursales, type Especialidad, type Sucursal } from '@/api/catalogo'
import {
  listarProfesionalesAdmin, crearProfesional, editarProfesional, desactivarProfesional,
  type ProfesionalAdmin, type ProfesionalEscritura,
} from '@/api/catalogo_admin'
import { Boton } from '@/componentes/Boton'
import { Campo } from '@/componentes/Campo'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'
import {
  PANEL, SECONDARY, DANGER, mensajeError, IconoCatalogo, CabeceraCatalogo,
  EstadoCatalogo, AvisoCatalogo, ErrorCatalogo, BuscadorCatalogo, ConfirmacionCatalogo,
  Etiqueta,
} from './catalogo_comun'

const vacio=():ProfesionalEscritura=>({
  first_name:'',last_name:'',license_number:'',specialties:[],branches:[],
})
export function Profesionales() {
  const {token,puede}=useSesion()
  useTitulo('Profesionales')
  const leer=puede('catalog.professional.read')
  const crear=puede('catalog.professional.create')
  const editar=puede('catalog.professional.update')
  const [items,setItems]=useState<ProfesionalAdmin[]>([])
  const [specialties,setSpecialties]=useState<Especialidad[]>([])
  const [branches,setBranches]=useState<Sucursal[]>([])
  const [loading,setLoading]=useState(true)
  const [saving,setSaving]=useState(false)
  const [error,setError]=useState<string|null>(null)
  const [success,setSuccess]=useState<string|null>(null)
  const [query,setQuery]=useState('')
  const [filter,setFilter]=useState('active')
  const [form,setForm]=useState<{id:string|null;value:ProfesionalEscritura}|null>(null)
  const [confirm,setConfirm]=useState<ProfesionalAdmin|null>(null)
  const contexto={token}
  const recargar=useCallback(async(signal?:AbortSignal)=>{
    setLoading(true)
    try{
      const [p,s,b]=await Promise.all([
        listarProfesionalesAdmin({token},signal),
        listarEspecialidades({token},signal),
        listarSucursales({token},signal),
      ])
      setItems(p);setSpecialties(s);setBranches(b);setError(null)
    }catch(e){if(!(e instanceof DOMException&&e.name==='AbortError'))setError(mensajeError(e))}
    finally{if(!signal?.aborted)setLoading(false)}
  },[token])
  useEffect(()=>{
    if(!leer)return
    const c=new AbortController();void recargar(c.signal);return()=>c.abort()
  },[leer,recargar])
  const abrir=(p?:ProfesionalAdmin)=>{
    setError(null)
    setForm({id:p?.id??null,value:p?{
      first_name:p.first_name,last_name:p.last_name,license_number:p.license_number,
      specialties:p.specialties.map(s=>s.id),branches:p.branches.map(b=>b.id),
    }:vacio()})
  }
  const guardar=async(e:FormEvent)=>{
    e.preventDefault();if(!form||saving)return
    const value={...form.value,first_name:form.value.first_name.trim(),
      last_name:form.value.last_name.trim(),license_number:form.value.license_number.trim()}
    if(!value.first_name||!value.last_name){setError('Ingresá el nombre y apellido.');return}
    setSaving(true);setError(null)
    try{
      if(form.id)await editarProfesional(form.id,value,contexto)
      else await crearProfesional(value,contexto)
      setForm(null);setSuccess(form.id?'Profesional actualizado correctamente.':'Profesional registrado correctamente.')
      await recargar()
    }catch(e){setError(mensajeError(e))}
    finally{setSaving(false)}
  }
  const desactivar=async()=>{
    if(!confirm||saving)return
    setSaving(true);setError(null)
    try{
      await desactivarProfesional(confirm.id,contexto)
      setConfirm(null);setSuccess('Profesional desactivado. Sus datos se conservaron.')
      await recargar()
    }catch(e){setConfirm(null);setError(mensajeError(e))}
    finally{setSaving(false)}
  }
  const filtered=items.filter(p=>(filter==='all'||p.is_active===(filter==='active'))&&
    `${p.full_name} ${p.license_number} ${p.specialties.map(s=>s.name).join(' ')} ${p.branches.map(b=>b.name).join(' ')}`.toLowerCase().includes(query.toLowerCase().trim()))
  if(!leer)return <main className="mx-auto max-w-4xl px-5 py-10 text-tinta-500">No tenés permiso para consultar profesionales.</main>
  return <main className="mx-auto max-w-6xl space-y-6 px-5 py-8 sm:py-10">
    <CabeceraCatalogo titulo="Profesionales" descripcion="Gestioná el directorio médico y asigná a cada profesional sus especialidades y las sucursales donde atiende.">
      {crear&&<Boton type="button" onClick={()=>abrir()} className="w-auto"><IconoCatalogo nombre="plus" className="size-4"/> Nuevo profesional</Boton>}
    </CabeceraCatalogo>
    {success&&<AvisoCatalogo mensaje={success} onCerrar={()=>setSuccess(null)}/>}
    {error&&!form&&<ErrorCatalogo mensaje={error}/>}
    <div className="flex flex-wrap gap-2"><Link to="/especialidades" className={SECONDARY}>Especialidades</Link><Link to="/profesionales" className="rounded-xl bg-marca-600 px-4 py-2 text-sm font-semibold text-white">Profesionales</Link><Link to="/sucursales" className={SECONDARY}>Sucursales</Link></div>
    <section className={PANEL}>
      <div className="flex flex-wrap items-center justify-between gap-4"><div className="flex items-center gap-3"><span className="grid size-11 place-items-center rounded-xl bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-300"><IconoCatalogo nombre="user"/></span><div><h2 className="font-semibold text-tinta-900 dark:text-tinta-100">Directorio de profesionales</h2><p className="text-sm text-tinta-500">{items.filter(p=>p.is_active).length} activos · {items.length} registrados</p></div></div><button type="button" disabled={loading} onClick={()=>void recargar()} className={SECONDARY}><IconoCatalogo nombre="refresh" className="size-4"/> Actualizar</button></div>
      <div className="mt-5"><BuscadorCatalogo valor={query} onCambio={setQuery} estado={filter} onEstado={setFilter}/></div>
      {loading?<p role="status" className="py-12 text-center text-sm text-tinta-500">Cargando profesionales…</p>:filtered.length===0?
        <div className="py-12 text-center"><span className="mx-auto grid size-14 place-items-center rounded-2xl bg-tinta-100 text-tinta-400 dark:bg-tinta-800"><IconoCatalogo nombre="user" className="size-7"/></span><h3 className="mt-4 font-semibold">No se encontraron profesionales</h3><p className="mt-1 text-sm text-tinta-500">Registrá un profesional o probá con otro filtro.</p></div>:
        <div className="mt-5 grid gap-3 md:grid-cols-2">{filtered.map(p=><article key={p.id} className="flex min-w-0 flex-col rounded-xl border border-tinta-200 p-4 transition hover:border-tinta-300 dark:border-tinta-800 dark:hover:border-tinta-700">
          <div className="flex items-start gap-3"><span className="grid size-10 shrink-0 place-items-center rounded-xl bg-tinta-100 text-tinta-600 dark:bg-tinta-800 dark:text-tinta-300"><IconoCatalogo nombre="user"/></span><div className="min-w-0 flex-1"><h3 className="break-words font-semibold text-tinta-900 dark:text-tinta-100">{p.full_name}</h3><p className="mt-0.5 text-xs text-tinta-500">Matrícula: {p.license_number||'Sin registrar'}</p><div className="mt-2"><EstadoCatalogo activo={p.is_active}/></div></div></div>
          <div className="mt-4 flex-1 space-y-3"><div><p className="mb-2 text-xs font-semibold uppercase tracking-wider text-tinta-500">Especialidades</p><div className="flex flex-wrap gap-1.5">{p.specialties.length?p.specialties.map(s=><Etiqueta key={s.id}>{s.name}</Etiqueta>):<span className="text-sm text-tinta-400">Sin asignar</span>}</div></div><div><p className="mb-2 text-xs font-semibold uppercase tracking-wider text-tinta-500">Sucursales</p><div className="flex flex-wrap gap-1.5">{p.branches.length?p.branches.map(b=><Etiqueta key={b.id}>{b.name}</Etiqueta>):<span className="text-sm text-tinta-400">Sin asignar</span>}</div></div></div>
          <div className="mt-4 flex flex-wrap gap-2 border-t border-tinta-200 pt-3 dark:border-tinta-800">{editar&&<button type="button" className={SECONDARY} onClick={()=>abrir(p)}><IconoCatalogo nombre="edit" className="size-4"/> Editar y asignar</button>}{editar&&p.is_active&&<button type="button" className={DANGER} onClick={()=>setConfirm(p)}>Desactivar</button>}</div>
        </article>)}</div>}
    </section>
    {form&&<FormularioProfesional key={form.id??'nuevo'} inicial={form.value} esEdicion={Boolean(form.id)} specialties={specialties} branches={branches} saving={saving} error={error} onChange={value=>setForm({...form,value})} onSubmit={guardar} onClose={()=>{setForm(null);setError(null)}}/>}
    {confirm&&<ConfirmacionCatalogo titulo="Desactivar profesional" descripcion={`¿Querés desactivar a ${confirm.full_name}? Sus datos y asociaciones se conservarán. El sistema rechazará la baja si tiene agendas activas.`} trabajando={saving} onCancelar={()=>setConfirm(null)} onConfirmar={()=>void desactivar()}/>}
  </main>
}

function FormularioProfesional({inicial,esEdicion,specialties,branches,saving,error,onChange,onSubmit,onClose}:{
  inicial:ProfesionalEscritura;esEdicion:boolean;specialties:Especialidad[];branches:Sucursal[]
  saving:boolean;error:string|null;onChange:(v:ProfesionalEscritura)=>void
  onSubmit:(e:FormEvent)=>void;onClose:()=>void
}) {
  const [value,setValue]=useState(inicial)
  const set=(next:ProfesionalEscritura)=>{setValue(next);onChange(next)}
  const campo=<K extends keyof ProfesionalEscritura>(key:K,v:ProfesionalEscritura[K])=>set({...value,[key]:v})
  const toggle=(key:'specialties'|'branches',id:string)=>{
    const current=value[key]
    campo(key,current.includes(id)?current.filter(v=>v!==id):[...current,id])
  }
  const selectedSpecialties=new Set(value.specialties)
  const selectedBranches=new Set(value.branches)
  return <div className="fixed inset-0 z-40 overflow-y-auto bg-black/60 p-3 sm:p-6" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget&&!saving)onClose()}}>
    <div role="dialog" aria-modal="true" aria-labelledby="profesional-titulo" className="mx-auto my-4 w-full max-w-3xl overflow-hidden rounded-2xl bg-white shadow-2xl dark:bg-tinta-950">
      <div className="flex items-start justify-between gap-4 border-b border-tinta-200 p-5 sm:p-6 dark:border-tinta-800"><div><p className="text-xs font-semibold uppercase tracking-wider text-marca-700 dark:text-marca-400">Catálogo · US-12</p><h2 id="profesional-titulo" className="mt-1 text-xl font-semibold">{esEdicion?'Editar profesional':'Nuevo profesional'}</h2><p className="mt-1 text-sm text-tinta-500">Datos profesionales y lugares de atención.</p></div><button type="button" disabled={saving} onClick={onClose} aria-label="Cerrar formulario" className="rounded-lg p-2 text-tinta-500 hover:bg-tinta-100 dark:hover:bg-tinta-800"><IconoCatalogo nombre="close"/></button></div>
      <form onSubmit={e=>void onSubmit(e)}>
        <div className="max-h-[65vh] space-y-6 overflow-y-auto p-5 sm:p-6">
          {error&&<ErrorCatalogo mensaje={error}/>}
          <section className="space-y-4"><div><h3 className="font-semibold">Información profesional</h3><p className="mt-1 text-sm text-tinta-500">El profesional puede registrarse antes de tener una cuenta de acceso.</p></div><div className="grid gap-4 sm:grid-cols-2"><Campo etiqueta="Nombres" required maxLength={80} value={value.first_name} onChange={e=>campo('first_name',e.target.value)} placeholder="Ej. Laura"/><Campo etiqueta="Apellidos" required maxLength={80} value={value.last_name} onChange={e=>campo('last_name',e.target.value)} placeholder="Ej. Gómez"/><div className="sm:col-span-2"><Campo etiqueta="Matrícula profesional (opcional)" maxLength={40} value={value.license_number} onChange={e=>campo('license_number',e.target.value)} placeholder="Ej. MP-1001" ayuda="Debe ser única dentro del centro médico cuando se registra."/></div></div></section>
          <section className="space-y-3 border-t border-tinta-200 pt-5 dark:border-tinta-800"><div><h3 className="font-semibold">Especialidades</h3><p className="mt-1 text-sm text-tinta-500">Seleccioná una o varias áreas de atención.</p></div><div className="grid gap-2 sm:grid-cols-2">{specialties.filter(s=>s.is_active||selectedSpecialties.has(s.id)).map(s=><label key={s.id} className="flex cursor-pointer items-start gap-3 rounded-xl border border-tinta-200 p-3 text-sm transition hover:border-marca-300 dark:border-tinta-800 dark:hover:border-marca-800"><input type="checkbox" className="mt-0.5 size-4 accent-marca-600" checked={selectedSpecialties.has(s.id)} onChange={()=>toggle('specialties',s.id)}/><span className="min-w-0"><span className="block font-medium">{s.name}</span>{!s.is_active&&<span className="text-xs text-tinta-500">Inactiva · asociación existente</span>}</span></label>)}</div>{specialties.length===0&&<p className="text-sm text-tinta-500">No hay especialidades registradas. <Link to="/especialidades" className="font-semibold text-marca-600 dark:text-marca-400">Crear especialidad →</Link></p>}</section>
          <section className="space-y-3 border-t border-tinta-200 pt-5 dark:border-tinta-800"><div><h3 className="font-semibold">Sucursales donde atiende</h3><p className="mt-1 text-sm text-tinta-500">Podés asignar varias sedes al mismo profesional. No se crean registros duplicados.</p></div><div className="grid gap-2 sm:grid-cols-2">{branches.filter(b=>b.is_active||selectedBranches.has(b.id)).map(b=><label key={b.id} className="flex cursor-pointer items-start gap-3 rounded-xl border border-tinta-200 p-3 text-sm transition hover:border-marca-300 dark:border-tinta-800 dark:hover:border-marca-800"><input type="checkbox" className="mt-0.5 size-4 accent-marca-600" checked={selectedBranches.has(b.id)} onChange={()=>toggle('branches',b.id)}/><span className="min-w-0"><span className="block font-medium">{b.name}</span><span className="mt-0.5 block text-xs text-tinta-500">{b.address||b.timezone}</span>{!b.is_active&&<span className="block text-xs text-tinta-500">Inactiva · asociación existente</span>}</span></label>)}</div>{branches.length===0&&<p className="text-sm text-tinta-500">No hay sucursales registradas. <Link to="/sucursales" className="font-semibold text-marca-600 dark:text-marca-400">Registrar sucursal →</Link></p>}<p className="text-xs leading-5 text-tinta-500">Si quitás una sede con agendas activas, el backend rechazará el cambio. Desactivá o reasigná esas agendas antes.</p></section>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-3 border-t border-tinta-200 bg-tinta-50 px-5 py-4 dark:border-tinta-800 dark:bg-tinta-900"><button type="button" disabled={saving} onClick={onClose} className={SECONDARY}>Cancelar</button><Boton type="submit" cargando={saving} className="w-auto">{esEdicion?'Guardar cambios':'Registrar profesional'}</Boton></div>
      </form>
    </div>
  </div>
}
