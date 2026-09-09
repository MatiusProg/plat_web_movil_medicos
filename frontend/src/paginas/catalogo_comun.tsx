import type { ReactNode } from 'react'
import { ErrorApi } from '@/api/tipos'

export const PANEL = 'rounded-2xl border border-tinta-200 bg-white p-5 dark:border-tinta-800 dark:bg-tinta-900/50'
export const INPUT = 'w-full rounded-xl border border-tinta-300 bg-white px-3.5 py-2.5 text-[0.9375rem] text-tinta-800 outline-none transition focus:border-marca-500 focus:ring-4 focus:ring-marca-500/20 dark:border-tinta-700 dark:bg-tinta-900 dark:text-tinta-100'
export const SECONDARY = 'inline-flex items-center justify-center gap-2 rounded-xl border border-tinta-300 px-4 py-2.5 text-sm font-semibold text-tinta-700 transition hover:bg-tinta-100 disabled:opacity-50 dark:border-tinta-700 dark:text-tinta-200 dark:hover:bg-tinta-800'
export const DANGER = 'rounded-xl px-3 py-2.5 text-sm font-medium text-alerta-600 hover:bg-alerta-50 disabled:opacity-50 dark:text-alerta-500 dark:hover:bg-alerta-500/10'

export function mensajeError(error: unknown): string {
  if (error instanceof ErrorApi) {
    if (error.porCampo) return Object.entries(error.porCampo)
      .map(([key, messages]) => `${key}: ${messages.join(', ')}`).join(' · ')
    return error.message
  }
  return error instanceof Error ? error.message : 'No se pudo completar la operación.'
}

export function IconoCatalogo({ nombre, className='size-5' }: { nombre:string; className?:string }) {
  const paths: Record<string, ReactNode> = {
    plus: <path d="M12 5v14M5 12h14"/>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
    edit: <><path d="m15 5 4 4M4 20l4.5-1 11-11a2.1 2.1 0 0 0-3-3l-11 11L4 20Z"/></>,
    close: <path d="M5 5l14 14M19 5 5 19"/>,
    check: <path d="m5 12 4 4L19 6"/>,
    refresh: <><path d="M20 7v5h-5M4 17v-5h5"/><path d="M5.5 9A7 7 0 0 1 18 7l2 5M4 12l2 5a7 7 0 0 0 12.5-2"/></>,
    heart: <><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/><path d="M4 12h4l2-3 4 6 2-3h4"/></>,
    user: <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
    building: <><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M9 21v-5h6v5M8 7h2m4 0h2M8 11h2m4 0h2"/></>,
  }
  return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[nombre]}</svg>
}

export function CabeceraCatalogo({titulo,descripcion,children}:{
  titulo:string;descripcion:string;children?:ReactNode
}) {
  return <div className="surgir flex flex-wrap items-end justify-between gap-4">
    <div>
      <p className="text-marca-700 dark:text-marca-400 text-sm font-medium">Catálogo del centro médico · US-12</p>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight text-tinta-900 dark:text-tinta-50">{titulo}</h1>
      <p className="mt-1.5 max-w-2xl text-[0.9375rem] text-tinta-500">{descripcion}</p>
    </div>{children}
  </div>
}
export function EstadoCatalogo({activo}: {activo:boolean}) {
  return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${activo?'bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-300':'bg-tinta-100 text-tinta-500 dark:bg-tinta-800'}`}>{activo?'Activa':'Inactiva'}</span>
}
export function AvisoCatalogo({mensaje,onCerrar}: {mensaje:string;onCerrar:()=>void}) {
  return <div role="status" className="flex items-center gap-2 rounded-xl border border-marca-200 bg-marca-50 px-4 py-3 text-sm text-marca-800 dark:border-marca-800 dark:bg-marca-950 dark:text-marca-200"><IconoCatalogo nombre="check" className="size-4"/>{mensaje}<button type="button" className="ml-auto" onClick={onCerrar} aria-label="Cerrar aviso"><IconoCatalogo nombre="close" className="size-4"/></button></div>
}
export function ErrorCatalogo({mensaje}: {mensaje:string}) {
  return <div role="alert" className="rounded-xl border border-alerta-200 bg-alerta-50 px-4 py-3 text-sm text-alerta-700 dark:border-alerta-500/40 dark:bg-alerta-500/10 dark:text-alerta-200">{mensaje}</div>
}
export function BuscadorCatalogo({valor,onCambio,estado,onEstado}:{
  valor:string;onCambio:(v:string)=>void;estado:string;onEstado:(v:string)=>void
}) {
  return <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_180px]">
    <label className="relative block"><span className="sr-only">Buscar</span><IconoCatalogo nombre="search" className="pointer-events-none absolute left-3.5 top-3 size-5 text-tinta-400"/><input className={`${INPUT} pl-11`} value={valor} onChange={e=>onCambio(e.target.value)} placeholder="Buscar en el catálogo…"/></label>
    <label><span className="sr-only">Estado</span><select className={INPUT} value={estado} onChange={e=>onEstado(e.target.value)}><option value="active">Activos</option><option value="all">Todos</option><option value="inactive">Inactivos</option></select></label>
  </div>
}
export function CampoSeleccion({etiqueta,children}: {etiqueta:string;children:ReactNode}) {
  return <label className="space-y-1.5 text-sm"><span className="block font-medium text-tinta-700 dark:text-tinta-300">{etiqueta}</span>{children}</label>
}
export function ConfirmacionCatalogo({titulo,descripcion,trabajando,onCancelar,onConfirmar}:{
  titulo:string;descripcion:string;trabajando:boolean;onCancelar:()=>void;onConfirmar:()=>void
}) {
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget&&!trabajando)onCancelar()}}>
    <div role="alertdialog" aria-modal="true" aria-labelledby="catalog-confirm-title" aria-describedby="catalog-confirm-desc" className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-tinta-900">
      <h2 id="catalog-confirm-title" className="text-lg font-semibold">{titulo}</h2><p id="catalog-confirm-desc" className="mt-2 text-sm leading-6 text-tinta-500">{descripcion}</p>
      <div className="mt-6 flex justify-end gap-3"><button type="button" disabled={trabajando} onClick={onCancelar} className={SECONDARY}>Cancelar</button><button type="button" disabled={trabajando} onClick={onConfirmar} className="rounded-xl bg-alerta-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{trabajando?'Procesando…':'Desactivar'}</button></div>
    </div>
  </div>
}
export function Etiqueta({children}: {children:ReactNode}) {
  return <span className="rounded-md border border-tinta-200 bg-tinta-50 px-2 py-1 text-xs font-medium text-tinta-600 dark:border-tinta-700 dark:bg-tinta-800 dark:text-tinta-300">{children}</span>
}
