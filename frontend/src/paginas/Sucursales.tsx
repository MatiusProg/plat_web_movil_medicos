import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { listarSucursales, type Sucursal } from '@/api/catalogo'
import {
  crearSucursal, desactivarSucursal, editarSucursal, obtenerSucursal,
  type FranjaSucursal, type SucursalDetalle, type SucursalEscritura,
} from '@/api/sucursales'
import { ErrorApi } from '@/api/tipos'
import { Boton } from '@/componentes/Boton'
import { Campo } from '@/componentes/Campo'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
const INPUT = 'w-full rounded-xl border border-tinta-300 bg-white px-3.5 py-2.5 text-[0.9375rem] text-tinta-800 outline-none transition focus:border-marca-500 focus:ring-4 focus:ring-marca-500/20 dark:border-tinta-700 dark:bg-tinta-900 dark:text-tinta-100'
const PANEL = 'rounded-2xl border border-tinta-200 bg-white p-5 dark:border-tinta-800 dark:bg-tinta-900/50'
const SECUNDARIO = 'inline-flex items-center justify-center gap-2 rounded-xl border border-tinta-300 px-4 py-2.5 text-sm font-semibold text-tinta-700 transition hover:bg-tinta-100 disabled:opacity-50 dark:border-tinta-700 dark:text-tinta-200 dark:hover:bg-tinta-800'
const HORA = /^\d{2}:\d{2}(:\d{2})?$/

type Borrador = {
  name: string; address: string; phone: string; timezone: string
  latitude: string; longitude: string; hours: FranjaSucursal[]
}
const vacio = (): Borrador => ({
  name: '', address: '', phone: '', timezone: 'America/La_Paz',
  latitude: '', longitude: '', hours: [],
})
const hora = (value: string) => value.slice(0, 5)
const convertir = (s: SucursalDetalle): Borrador => ({
  name: s.name, address: s.address, phone: s.phone, timezone: s.timezone,
  latitude: s.latitude ?? '', longitude: s.longitude ?? '',
  hours: s.hours.map(h => ({ ...h, opens_at: hora(h.opens_at), closes_at: hora(h.closes_at) })),
})
function validar(f: Borrador): string | null {
  if (!f.name.trim()) return 'Ingresá el nombre de la sucursal.'
  if (f.name.length > 120) return 'El nombre no puede superar 120 caracteres.'
  if (f.address.length > 200 || f.phone.length > 30) return 'Revisá la longitud de la dirección o el teléfono.'
  for (const [clave, min, max] of [['latitude', -90, 90], ['longitude', -180, 180]] as const) {
    const raw = f[clave]
    if (raw && (!Number.isFinite(Number(raw)) || Number(raw) < min || Number(raw) > max))
      return `${clave === 'latitude' ? 'La latitud' : 'La longitud'} debe estar entre ${min} y ${max}.`
  }
  const franjas = [...f.hours].sort((a,b) => a.weekday-b.weekday || a.opens_at.localeCompare(b.opens_at))
  for (let i=0; i<franjas.length; i++) {
    const h=franjas[i]
    if (!Number.isInteger(h.weekday) || h.weekday<0 || h.weekday>6 || !HORA.test(h.opens_at) || !HORA.test(h.closes_at) || h.opens_at>=h.closes_at)
      return 'Revisá el día y las horas de apertura y cierre.'
    if (i>0 && franjas[i-1].weekday===h.weekday && h.opens_at<franjas[i-1].closes_at)
      return `Hay franjas superpuestas el ${DIAS[h.weekday]}.`
  }
  return null
}
function cuerpo(f: Borrador): SucursalEscritura {
  return {
    name: f.name.trim(), address: f.address.trim(), phone: f.phone.trim(),
    timezone: f.timezone.trim(), latitude: f.latitude || null,
    longitude: f.longitude || null,
    hours: f.hours.map(h => ({ ...h, opens_at: hora(h.opens_at), closes_at: hora(h.closes_at) })),
  }
}
function mensaje(error: unknown): string {
  if (error instanceof ErrorApi) {
    const campos = error.porCampo
    if (campos) return Object.entries(campos).map(([k,v]) => `${k}: ${v.join(', ')}`).join(' · ')
    return error.message
  }
  return error instanceof Error ? error.message : 'No se pudo completar la operación.'
}
function Icono({ name, className='size-5' }: { name: string; className?: string }) {
  const paths: Record<string, ReactNode> = {
    edificio: <><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M9 21v-5h6v5M8 7h2m4 0h2M8 11h2m4 0h2"/></>,
    plus: <path d="M12 5v14M5 12h14"/>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
    pencil: <><path d="m15 5 4 4M4 20l4.5-1 11-11a2.1 2.1 0 0 0-3-3l-11 11L4 20Z"/></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 10h18"/></>,
    location: <><path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></>,
    phone: <path d="M6 3h3l2 5-2 2a15 15 0 0 0 5 5l2-2 5 2v3a3 3 0 0 1-3 3A15 15 0 0 1 3 6a3 3 0 0 1 3-3Z"/>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    close: <path d="M5 5l14 14M19 5 5 19"/>,
    check: <path d="m5 12 4 4L19 6"/>,
    refresh: <><path d="M20 7v5h-5M4 17v-5h5"/><path d="M5.5 9A7 7 0 0 1 18 7l2 5M4 12l2 5a7 7 0 0 0 12.5-2"/></>,
  }
  return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
}
export function Sucursales() {
  const { token, puede } = useSesion()
  useTitulo('Sucursales')
  const leer = puede('catalog.branch.read')
  const crear = puede('catalog.branch.create')
  const editar = puede('catalog.branch.update')
  const baja = puede('catalog.branch.deactivate')
  const [items,setItems]=useState<Sucursal[]>([])
  const [cargando,setCargando]=useState(true)
  const [error,setError]=useState<string|null>(null)
  const [aviso,setAviso]=useState<string|null>(null)
  const [consulta,setConsulta]=useState('')
  const [estado,setEstado]=useState('active')
  const [formulario,setFormulario]=useState<{ id:string|null; valor:Borrador }|null>(null)
  const [cargandoDetalle,setCargandoDetalle]=useState(false)
  const [guardando,setGuardando]=useState(false)
  const [confirmar,setConfirmar]=useState<Sucursal|null>(null)
  const contexto={token}
  const recargar=useCallback(async (senal?:AbortSignal) => {
    setCargando(true)
    try {
      const datos=await listarSucursales({token},senal)
      setItems(datos); setError(null)
    } catch(e) {
      if (!(e instanceof DOMException && e.name==='AbortError')) setError(mensaje(e))
    } finally { if (!senal?.aborted) setCargando(false) }
  },[token])
  useEffect(() => {
    if (!leer) return
    const c=new AbortController()
    void recargar(c.signal)
    return () => c.abort()
  },[leer,recargar])
  const abrir=async (s?:Sucursal) => {
    setError(null); setAviso(null)
    if (!s) { setFormulario({id:null,valor:vacio()}); return }
    setCargandoDetalle(true)
    try {
      const detalle=await obtenerSucursal(s.id,contexto)
      setFormulario({id:s.id,valor:convertir(detalle)})
    } catch(e) { setError(mensaje(e)) }
    finally {setCargandoDetalle(false)}
  }
  const guardar=async (event:FormEvent) => {
    event.preventDefault()
    if (!formulario || guardando) return
    const fallo=validar(formulario.valor)
    if (fallo) {setError(fallo);return}
    setGuardando(true);setError(null)
    try {
      const payload=cuerpo(formulario.valor)
      if (formulario.id) await editarSucursal(formulario.id,payload,contexto)
      else await crearSucursal(payload,contexto)
      setFormulario(null);setAviso(formulario.id?'Sucursal actualizada correctamente.':'Sucursal registrada correctamente.')
      await recargar()
    } catch(e) {setError(mensaje(e))}
    finally {setGuardando(false)}
  }
  const desactivar=async () => {
    if (!confirmar || guardando) return
    setGuardando(true);setError(null)
    try {
      await desactivarSucursal(confirmar.id,contexto)
      setConfirmar(null);setAviso('Sucursal desactivada. Sus datos se conservaron.')
      await recargar()
    } catch(e) {setConfirmar(null);setError(mensaje(e))}
    finally {setGuardando(false)}
  }
  const filtradas=items.filter(s => {
    if (estado==='active' && !s.is_active) return false
    if (estado==='inactive' && s.is_active) return false
    return `${s.name} ${s.address} ${s.phone}`.toLowerCase().includes(consulta.toLowerCase().trim())
  })
  if (!leer) return <main className="mx-auto max-w-4xl px-5 py-10"><p className="text-tinta-500">No tenés permiso para consultar sucursales.</p></main>
  return <main className="mx-auto max-w-6xl space-y-6 px-5 py-8 sm:py-10">
    <div className="surgir flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-marca-700 dark:text-marca-400 text-sm font-medium">Catálogo del centro médico · US-11</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-tinta-900 dark:text-tinta-50">Sucursales</h1>
        <p className="mt-1.5 max-w-2xl text-[0.9375rem] text-tinta-500">Administrá las sedes y sus horarios de atención. Los profesionales y agendas utilizan este catálogo.</p>
      </div>
      {crear && <Boton type="button" onClick={()=>void abrir()} className="w-auto"><Icono name="plus" className="size-4"/> Nueva sucursal</Boton>}
    </div>
    {aviso && <div role="status" className="flex items-center gap-2 rounded-xl border border-marca-200 bg-marca-50 px-4 py-3 text-sm text-marca-800 dark:border-marca-800 dark:bg-marca-950 dark:text-marca-200"><Icono name="check" className="size-4"/>{aviso}<button type="button" className="ml-auto" aria-label="Cerrar aviso" onClick={()=>setAviso(null)}><Icono name="close" className="size-4"/></button></div>}
    {error && <div role="alert" className="rounded-xl border border-alerta-200 bg-alerta-50 px-4 py-3 text-sm text-alerta-700 dark:border-alerta-500/40 dark:bg-alerta-500/10 dark:text-alerta-200">{error}</div>}
    <section className={PANEL}>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3"><span className="grid size-11 place-items-center rounded-xl bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-300"><Icono name="edificio"/></span><div><h2 className="font-semibold text-tinta-900 dark:text-tinta-100">Directorio de sedes</h2><p className="text-sm text-tinta-500">{items.filter(s=>s.is_active).length} activas · {items.length} registradas</p></div></div>
        <button type="button" onClick={()=>void recargar()} disabled={cargando} className={SECUNDARIO}><Icono name="refresh" className="size-4"/> Actualizar</button>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-[minmax(0,1fr)_180px]">
        <label className="relative block"><span className="sr-only">Buscar sucursales</span><Icono name="search" className="pointer-events-none absolute left-3.5 top-3 size-5 text-tinta-400"/><input className={`${INPUT} pl-11`} value={consulta} onChange={e=>setConsulta(e.target.value)} placeholder="Buscar por nombre, dirección o teléfono…"/></label>
        <label><span className="sr-only">Estado</span><select className={INPUT} value={estado} onChange={e=>setEstado(e.target.value)}><option value="active">Activas</option><option value="all">Todas</option><option value="inactive">Inactivas</option></select></label>
      </div>
      {cargando ? <p role="status" className="py-12 text-center text-sm text-tinta-500">Cargando sucursales…</p> :
      filtradas.length===0 ? <div className="py-12 text-center"><span className="mx-auto grid size-14 place-items-center rounded-2xl bg-tinta-100 text-tinta-400 dark:bg-tinta-800"><Icono name="edificio" className="size-7"/></span><h3 className="mt-4 font-semibold">No se encontraron sucursales</h3><p className="mt-1 text-sm text-tinta-500">{items.length===0?'Registrá la primera sede del centro médico.':'Probá con otro filtro de búsqueda.'}</p>{items.length===0 && crear && <button type="button" onClick={()=>void abrir()} className="mt-4 text-sm font-semibold text-marca-600 dark:text-marca-400">Registrar sucursal →</button>}</div> :
      <div className="mt-5 grid gap-3 md:grid-cols-2">
        {filtradas.map(s=><article key={s.id} className="flex min-w-0 flex-col rounded-xl border border-tinta-200 p-4 transition hover:border-tinta-300 dark:border-tinta-800 dark:hover:border-tinta-700">
          <div className="flex items-start gap-3"><span className="grid size-10 shrink-0 place-items-center rounded-xl bg-tinta-100 text-tinta-600 dark:bg-tinta-800 dark:text-tinta-300"><Icono name="edificio" className="size-5"/></span><div className="min-w-0 flex-1"><h3 className="break-words font-semibold text-tinta-900 dark:text-tinta-100">{s.name}</h3><span className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${s.is_active?'bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-300':'bg-tinta-100 text-tinta-500 dark:bg-tinta-800'}`}>{s.is_active?'Activa':'Inactiva'}</span></div></div>
          <div className="mt-4 flex-1 space-y-2 text-sm text-tinta-500"><p className="flex items-start gap-2"><Icono name="location" className="mt-0.5 size-4 shrink-0"/><span className="break-words">{s.address || 'Dirección no registrada'}</span></p><p className="flex items-center gap-2"><Icono name="phone" className="size-4 shrink-0"/>{s.phone || 'Sin teléfono'}</p><p className="flex items-center gap-2"><Icono name="clock" className="size-4 shrink-0"/>{s.timezone}</p></div>
          <div className="mt-4 flex flex-wrap gap-2 border-t border-tinta-200 pt-3 dark:border-tinta-800">
            {editar && <button type="button" disabled={cargandoDetalle} onClick={()=>void abrir(s)} className={SECUNDARIO}><Icono name="pencil" className="size-4"/> Editar y horarios</button>}
            {baja && s.is_active && <button type="button" onClick={()=>setConfirmar(s)} className="rounded-xl px-3 py-2.5 text-sm font-medium text-alerta-600 hover:bg-alerta-50 dark:text-alerta-500 dark:hover:bg-alerta-500/10">Desactivar</button>}
            <Link to="/agendas" className="ml-auto inline-flex items-center text-sm font-medium text-marca-600 dark:text-marca-400">Agendas →</Link>
          </div>
        </article>)}
      </div>}
    </section>
    {cargandoDetalle && <p role="status" className="text-sm text-tinta-500">Cargando datos de la sucursal…</p>}
    {formulario && <Formulario key={formulario.id??'nueva'} id={formulario.id} inicial={formulario.valor} guardando={guardando} error={error} onGuardar={guardar} onCambio={valor=>setFormulario({...formulario,valor})} onCerrar={()=>{setFormulario(null);setError(null)}}/>}
    {confirmar && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget&&!guardando)setConfirmar(null)}}>
      <div role="alertdialog" aria-modal="true" aria-labelledby="confirmar-titulo" aria-describedby="confirmar-desc" className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-tinta-900">
        <h2 id="confirmar-titulo" className="text-lg font-semibold">Desactivar sucursal</h2><p id="confirmar-desc" className="mt-2 text-sm leading-6 text-tinta-500">¿Querés desactivar <strong className="text-tinta-800 dark:text-tinta-100">{confirmar.name}</strong>? Sus datos se conservarán. Si tiene agendas activas, el sistema rechazará la operación para protegerlas.</p>
        <div className="mt-6 flex justify-end gap-3"><button type="button" disabled={guardando} onClick={()=>setConfirmar(null)} className={SECUNDARIO}>Cancelar</button><button type="button" disabled={guardando} onClick={()=>void desactivar()} className="rounded-xl bg-alerta-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{guardando?'Procesando…':'Desactivar'}</button></div>
      </div>
    </div>}
  </main>
}
function Formulario({id,inicial,guardando,error,onGuardar,onCambio,onCerrar}:{
  id:string|null; inicial:Borrador; guardando:boolean; error:string|null
  onGuardar:(e:FormEvent)=>void; onCambio:(v:Borrador)=>void; onCerrar:()=>void
}) {
  const f=inicial
  const [horariosCambiados,setHorariosCambiados]=useState(false)
  const [confirmarHorarios,setConfirmarHorarios]=useState(false)
  const set=(next:Borrador)=>{onCambio(next);setConfirmarHorarios(false)}
  const campo=<K extends keyof Borrador>(k:K,v:Borrador[K])=>set({...f,[k]:v})
  const setHora=(i:number,k:keyof FranjaSucursal,v:string|number)=>{
    const hours=f.hours.map((h,j)=>j===i?{...h,[k]:v}:h)
    set({...f,hours});setHorariosCambiados(true)
  }
  const submit=(e:FormEvent)=>{
    e.preventDefault()
    const fallo=validar(f)
    if(fallo){onGuardar(e);return}
    if(id && horariosCambiados && !confirmarHorarios){setConfirmarHorarios(true);return}
    onGuardar(e)
  }
  useEffect(()=>{
    const key=(e:KeyboardEvent)=>{if(e.key==='Escape'&&!guardando)onCerrar()}
    window.addEventListener('keydown',key)
    return ()=>window.removeEventListener('keydown',key)
  },[guardando,onCerrar])
  return <div className="fixed inset-0 z-40 overflow-y-auto bg-black/60 p-3 sm:p-6" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget&&!guardando)onCerrar()}}>
    <div role="dialog" aria-modal="true" aria-labelledby="sucursal-form-titulo" className="mx-auto my-4 w-full max-w-3xl overflow-hidden rounded-2xl bg-white shadow-2xl dark:bg-tinta-950">
      <div className="flex items-start justify-between gap-4 border-b border-tinta-200 p-5 sm:p-6 dark:border-tinta-800"><div><p className="text-xs font-semibold uppercase tracking-wider text-marca-700 dark:text-marca-400">Catálogo · US-11</p><h2 id="sucursal-form-titulo" className="mt-1 text-xl font-semibold">{id?'Editar sucursal':'Nueva sucursal'}</h2><p className="mt-1 text-sm text-tinta-500">Datos generales y horarios de atención.</p></div><button type="button" disabled={guardando} onClick={onCerrar} aria-label="Cerrar formulario" className="rounded-lg p-2 text-tinta-500 hover:bg-tinta-100 dark:hover:bg-tinta-800"><Icono name="close"/></button></div>
      <form onSubmit={submit}>
        <div className="max-h-[65vh] space-y-6 overflow-y-auto p-5 sm:p-6">
          {error && <div role="alert" className="rounded-xl border border-alerta-200 bg-alerta-50 p-3 text-sm text-alerta-700 dark:border-alerta-500/40 dark:bg-alerta-500/10 dark:text-alerta-200">{error}</div>}
          <section className="space-y-4"><div><h3 className="font-semibold">Información general</h3><p className="mt-1 text-sm text-tinta-500">Identificación y contacto de la sede.</p></div>
            <div className="grid gap-4 sm:grid-cols-2"><div className="sm:col-span-2"><Campo etiqueta="Nombre de la sucursal" required maxLength={120} value={f.name} onChange={e=>campo('name',e.target.value)} placeholder="Ej. Sede Centro"/></div><div className="sm:col-span-2"><Campo etiqueta="Dirección" maxLength={200} value={f.address} onChange={e=>campo('address',e.target.value)} placeholder="Av. Principal, número y referencia"/></div><Campo etiqueta="Teléfono" type="tel" maxLength={30} value={f.phone} onChange={e=>campo('phone',e.target.value)} placeholder="Ej. 70000000"/><label className="space-y-1.5 text-sm"><span className="block font-medium text-tinta-700 dark:text-tinta-300">Zona horaria</span><select className={INPUT} value={f.timezone} onChange={e=>campo('timezone',e.target.value)}><option value="America/La_Paz">Bolivia · La Paz (UTC−4)</option><option value="America/Lima">Perú · Lima</option><option value="America/Asuncion">Paraguay · Asunción</option><option value="America/Santiago">Chile · Santiago</option><option value="America/Argentina/Buenos_Aires">Argentina · Buenos Aires</option></select></label><Campo etiqueta="Latitud (opcional)" type="number" step="any" min={-90} max={90} value={f.latitude} onChange={e=>campo('latitude',e.target.value)} placeholder="-17.7833"/><Campo etiqueta="Longitud (opcional)" type="number" step="any" min={-180} max={180} value={f.longitude} onChange={e=>campo('longitude',e.target.value)} placeholder="-63.1821"/></div>
          </section>
          <section className="space-y-4 border-t border-tinta-200 pt-5 dark:border-tinta-800"><div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-semibold">Horarios de atención</h3><p className="mt-1 text-sm text-tinta-500">Podés agregar varias franjas por día, por ejemplo mañana y tarde.</p></div><button type="button" className={SECUNDARIO} onClick={()=>{campo('hours',[...f.hours,{weekday:0,opens_at:'08:00',closes_at:'12:00'}]);setHorariosCambiados(true);setConfirmarHorarios(false)}}><Icono name="plus" className="size-4"/> Agregar franja</button></div>
            {f.hours.length===0?<div className="rounded-xl border border-dashed border-tinta-300 p-5 text-center text-sm text-tinta-500 dark:border-tinta-700">No hay horarios cargados. La sede se guardará sin restricciones horarias hasta que se configuren.</div>:<div className="space-y-3">{f.hours.map((h,i)=><div key={i} className="grid items-end gap-3 rounded-xl border border-tinta-200 p-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto] dark:border-tinta-800"><label className="space-y-1 text-sm"><span className="block text-tinta-500">Día</span><select className={INPUT} value={h.weekday} onChange={e=>setHora(i,'weekday',Number(e.target.value))}>{DIAS.map((d,j)=><option key={d} value={j}>{d}</option>)}</select></label><label className="space-y-1 text-sm"><span className="block text-tinta-500">Apertura</span><input className={INPUT} type="time" required value={hora(h.opens_at)} onChange={e=>setHora(i,'opens_at',e.target.value)}/></label><label className="space-y-1 text-sm"><span className="block text-tinta-500">Cierre</span><input className={INPUT} type="time" required value={hora(h.closes_at)} onChange={e=>setHora(i,'closes_at',e.target.value)}/></label><button type="button" className="grid size-11 place-items-center rounded-xl text-tinta-400 hover:bg-alerta-50 hover:text-alerta-600 dark:hover:bg-alerta-500/10" aria-label={`Quitar franja ${i+1}`} onClick={()=>{campo('hours',f.hours.filter((_,j)=>j!==i));setHorariosCambiados(true);setConfirmarHorarios(false)}}><Icono name="close" className="size-4"/></button></div>)}</div>}
            <p className="text-xs leading-5 text-tinta-500">Los días sin franjas mantienen la convención del sistema: no se consideran automáticamente cerrados. Las agendas activas deben permanecer dentro de las franjas configuradas.</p>
          </section>
        </div>
        {confirmarHorarios && <div className="border-t border-espera-200 bg-espera-50 px-5 py-3 text-sm text-espera-700 dark:border-espera-600/40 dark:bg-espera-600/10 dark:text-espera-200">Estás reemplazando los horarios de esta sede. El backend rechazará cualquier cambio que deje agendas activas fuera del nuevo horario. Presioná Guardar nuevamente para confirmar.</div>}
        <div className="flex flex-wrap items-center justify-end gap-3 border-t border-tinta-200 bg-tinta-50 px-5 py-4 dark:border-tinta-800 dark:bg-tinta-900"><button type="button" disabled={guardando} onClick={onCerrar} className={SECUNDARIO}>Cancelar</button><Boton type="submit" cargando={guardando} className="w-auto">{id?'Guardar cambios':'Registrar sucursal'}</Boton></div>
      </form>
    </div>
  </div>
}
