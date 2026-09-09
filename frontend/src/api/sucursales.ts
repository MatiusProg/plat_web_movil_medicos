import { pedir, type Contexto } from './cliente'
import type { Sucursal } from './catalogo'

export interface FranjaSucursal {
  weekday: number
  opens_at: string
  closes_at: string
}

export interface SucursalDetalle extends Sucursal {
  latitude: string | null
  longitude: string | null
  hours: FranjaSucursal[]
}

export interface SucursalEscritura {
  name: string
  address: string
  phone: string
  timezone: string
  latitude?: string | null
  longitude?: string | null
  hours?: FranjaSucursal[]
}

const base = '/catalog/branches/'

export const obtenerSucursal = (id: string, contexto: Contexto) =>
  pedir<SucursalDetalle>(`${base}${encodeURIComponent(id)}/`, contexto)

export const crearSucursal = (datos: SucursalEscritura, contexto: Contexto) =>
  pedir<SucursalDetalle>(base, { ...contexto, metodo: 'POST', cuerpo: datos })

export const editarSucursal = (id: string, datos: Partial<SucursalEscritura>, contexto: Contexto) =>
  pedir<SucursalDetalle>(`${base}${encodeURIComponent(id)}/`, {
    ...contexto, metodo: 'PATCH', cuerpo: datos,
  })

export const desactivarSucursal = (id: string, contexto: Contexto) =>
  pedir<SucursalDetalle>(`${base}${encodeURIComponent(id)}/deactivate/`, {
    ...contexto, metodo: 'POST',
  })
