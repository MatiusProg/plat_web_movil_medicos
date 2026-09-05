/**
 * US-04 — Roles, permisos y asignación de roles a los usuarios.
 *
 * Los tipos viven acá y no en `api/tipos.ts` por la misma razón que los de
 * US-43: ese archivo es el contrato compartido de `accounts`, y cada historia
 * que agrega endpoints trae su propio módulo. Es la regla del archivo
 * compartido de `docs/convenciones-de-codigo.md`, aplicada al frontend.
 *
 * Los nombres de los campos van en inglés porque son los que devuelve el
 * backend.
 */

import { pedir, type Contexto } from './cliente'

export interface Permiso {
  id: string
  /** `modulo.recurso.accion`. */
  code: string
  module: string
  description: string
}

export interface Rol {
  id: string
  code: string
  name: string
  description: string
  /** Siempre `false` en lo que devuelve el listado: las plantillas no se listan. */
  is_system: boolean
  is_active: boolean
  /** Códigos de permiso, ordenados. */
  permissions: string[]
  /** Cuántos usuarios lo tienen. Decide si se puede eliminar. */
  assigned_users: number
  created_at: string
  updated_at: string
}

export interface RolNuevo {
  code: string
  name: string
  description?: string
  permissions?: string[]
}

export interface RolEditado {
  name?: string
  description?: string
  is_active?: boolean
}

export interface RolDeUsuario {
  id: string
  code: string
  name: string
}

export interface UsuarioDeLaOrganizacion {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  document_type: string
  document_number: string
  is_active: boolean
  roles: RolDeUsuario[]
}

export interface Asignacion {
  id: number
  user: string
  user_email: string
  user_full_name: string
  role: string
  role_code: string
  role_name: string
  assigned_by: string | null
  assigned_by_email: string | null
  assigned_at: string
}

interface Pagina<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

/**
 * El catálogo de permisos concedibles.
 *
 * No viene paginado: son unas decenas de filas, las dibuja todas la misma
 * pantalla y paginarlas obligaría a la casilla de un permiso a estar en una
 * página distinta que la de otro del mismo módulo.
 */
export function listarPermisos(
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Permiso[]> {
  return pedir<Permiso[]>('/accounts/permissions/', { ...contexto, senal })
}

export function listarRoles(
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Pagina<Rol>> {
  return pedir<Pagina<Rol>>('/accounts/roles/', { ...contexto, senal })
}

export function crearRol(
  datos: RolNuevo,
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Rol> {
  return pedir<Rol>('/accounts/roles/', {
    ...contexto,
    metodo: 'POST',
    cuerpo: datos,
    senal,
  })
}

export function editarRol(
  id: string,
  datos: RolEditado,
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Rol> {
  return pedir<Rol>(`/accounts/roles/${id}/`, {
    ...contexto,
    metodo: 'PATCH',
    cuerpo: datos,
    senal,
  })
}

/**
 * Reemplaza el conjunto de permisos del rol.
 *
 * Es un PUT y manda **todos** los códigos marcados, no sólo los que
 * cambiaron: lo que no viaja se revoca. Con un PATCH nunca se podría quitar
 * un permiso.
 */
export function guardarPermisosDelRol(
  id: string,
  permisos: string[],
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Rol> {
  return pedir<Rol>(`/accounts/roles/${id}/permissions/`, {
    ...contexto,
    metodo: 'PUT',
    cuerpo: { permissions: permisos },
    senal,
  })
}

export function eliminarRol(
  id: string,
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<void> {
  return pedir<void>(`/accounts/roles/${id}/`, {
    ...contexto,
    metodo: 'DELETE',
    senal,
  })
}

export function listarUsuarios(
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Pagina<UsuarioDeLaOrganizacion>> {
  return pedir<Pagina<UsuarioDeLaOrganizacion>>('/accounts/users/', {
    ...contexto,
    senal,
  })
}

export function asignarRol(
  usuario: string,
  rol: string,
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Asignacion> {
  return pedir<Asignacion>('/accounts/user-roles/', {
    ...contexto,
    metodo: 'POST',
    cuerpo: { user: usuario, role: rol },
    senal,
  })
}

export function listarAsignacionesDe(
  usuario: string,
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Pagina<Asignacion>> {
  return pedir<Pagina<Asignacion>>(`/accounts/user-roles/?user=${usuario}`, {
    ...contexto,
    senal,
  })
}

export function revocarAsignacion(
  id: number,
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<void> {
  return pedir<void>(`/accounts/user-roles/${id}/`, {
    ...contexto,
    metodo: 'DELETE',
    senal,
  })
}
