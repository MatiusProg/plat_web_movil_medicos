/** US-12: escritura administrativa, separada de la búsqueda de US-16. */
import { pedir, type Contexto } from './cliente'
import type { Especialidad, Referencia } from './catalogo'

export interface ProfesionalAdmin {
  id: string
  first_name: string
  last_name: string
  full_name: string
  license_number: string
  is_active: boolean
  specialties: Referencia[]
  branches: Referencia[]
}

export interface ProfesionalEscritura {
  first_name: string
  last_name: string
  license_number: string
  specialties: string[]
  branches: string[]
}
export type EspecialidadEscritura = Pick<Especialidad, 'name' | 'description'>

const specialties = '/catalog/specialties/'
const professionals = '/catalog/professionals/'

export const crearEspecialidad = (data: EspecialidadEscritura, contexto: Contexto) =>
  pedir<Especialidad>(specialties, { ...contexto, metodo: 'POST', cuerpo: data })

export const editarEspecialidad = (id: string, data: EspecialidadEscritura, contexto: Contexto) =>
  pedir<Especialidad>(`${specialties}${encodeURIComponent(id)}/`, {
    ...contexto, metodo: 'PATCH', cuerpo: data,
  })

export const desactivarEspecialidad = (id: string, contexto: Contexto) =>
  pedir<Especialidad>(`${specialties}${encodeURIComponent(id)}/deactivate/`, {
    ...contexto, metodo: 'POST',
  })

export const listarProfesionalesAdmin = (contexto: Contexto, senal?: AbortSignal) =>
  pedir<ProfesionalAdmin[]>(`${professionals}manage/`, { ...contexto, senal })

export const crearProfesional = (data: ProfesionalEscritura, contexto: Contexto) =>
  pedir<ProfesionalAdmin>(`${professionals}manage/`, {
    ...contexto, metodo: 'POST', cuerpo: data,
  })

export const editarProfesional = (id: string, data: ProfesionalEscritura, contexto: Contexto) =>
  pedir<ProfesionalAdmin>(`${professionals}${encodeURIComponent(id)}/`, {
    ...contexto, metodo: 'PATCH', cuerpo: data,
  })

export const desactivarProfesional = (id: string, contexto: Contexto) =>
  pedir<ProfesionalAdmin>(`${professionals}${encodeURIComponent(id)}/deactivate/`, {
    ...contexto, metodo: 'POST',
  })
