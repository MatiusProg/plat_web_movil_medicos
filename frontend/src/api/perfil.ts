/**
 * US-05 — El perfil propio y el cambio de contraseña.
 *
 *   GET   /api/accounts/users/me/            el perfil de quien tiene la sesión
 *   PATCH /api/accounts/users/me/            sólo los campos que cambiaron
 *   POST  /api/accounts/users/me/password/   actual + nueva -> par de tokens nuevo
 *
 * La ruta no lleva identificador: el backend saca al usuario del token. No hay
 * forma de pedir, desde acá, el perfil de otra persona.
 */

import { pedir, type Contexto } from './cliente'
import type { Rol } from './tipos'

export interface Perfil {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  phone: string
  birth_date: string | null
  document_type: string
  document_number: string
  organization: { slug: string; name: string } | null
  roles: Rol[]
  is_platform_admin: boolean
  is_active: boolean
}

/** Lo único que el usuario puede cambiar de sí mismo. El resto, el backend lo rechaza. */
export type DatosEditables = Partial<
  Pick<Perfil, 'first_name' | 'last_name' | 'phone' | 'email'>
>

export function obtenerPerfil(contexto: Contexto, senal?: AbortSignal): Promise<Perfil> {
  return pedir<Perfil>('/accounts/users/me/', { ...contexto, senal })
}

/**
 * Guardado parcial (punto f): se manda sólo lo que cambió. Mandar el
 * formulario entero funcionaría igual, pero la bitácora registraría como
 * "editado" cada campo que sólo se reenvió.
 */
export function actualizarPerfil(
  datos: DatosEditables,
  contexto: Contexto,
): Promise<Perfil> {
  return pedir<Perfil>('/accounts/users/me/', {
    ...contexto,
    metodo: 'PATCH',
    cuerpo: datos,
  })
}

export interface ContrasenaCambiada {
  detail: string
  /** El par nuevo. Los refrescos anteriores quedaron en la lista negra. */
  access: string
  refresh: string
}

export function cambiarContrasena(
  datos: { actual: string; nueva: string; repetida: string },
  contexto: Contexto,
): Promise<ContrasenaCambiada> {
  return pedir<ContrasenaCambiada>('/accounts/users/me/password/', {
    ...contexto,
    metodo: 'POST',
    cuerpo: {
      current_password: datos.actual,
      password: datos.nueva,
      password_confirmation: datos.repetida,
    },
  })
}
