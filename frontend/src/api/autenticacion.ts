/**
 * US-02 — Los tres endpoints de sesión, tal como los expone `accounts`.
 *
 *   POST /api/accounts/login/            credenciales -> par de tokens
 *   POST /api/accounts/token/refresh/    refresh      -> par nuevo
 *   POST /api/accounts/logout/           refresh      -> lista negra
 */

import { pedir } from './cliente'
import type { SesionIniciada } from './tipos'

export interface Credenciales {
  /** Slug del centro médico. Vacío = Superadministrador de Plataforma. */
  organizacion: string
  email: string
  password: string
}

export function iniciarSesion(
  credenciales: Credenciales,
  senal?: AbortSignal,
): Promise<SesionIniciada> {
  return pedir<SesionIniciada>('/accounts/login/', {
    metodo: 'POST',
    cuerpo: {
      organization: credenciales.organizacion,
      email: credenciales.email,
      password: credenciales.password,
    },
    senal,
  })
}

/**
 * RNF-06 — Cambia el token de refresco por un par nuevo.
 *
 * El backend rota: el token entregado queda invalidado y hay que guardar los
 * dos valores de la respuesta. Reusar el anterior devuelve 401.
 */
export function renovarSesion(refresh: string): Promise<{ access: string; refresh: string }> {
  return pedir<{ access: string; refresh: string }>('/accounts/token/refresh/', {
    metodo: 'POST',
    cuerpo: { refresh },
  })
}

/**
 * CU4 — Cierre de sesión.
 *
 * Manda el refresco a la lista negra. El token de acceso sigue siendo válido
 * hasta que expire (30 minutos): lo que esto garantiza es que la sesión no se
 * pueda renovar, no que el acceso muera al instante.
 */
export function cerrarSesion(refresh: string, token: string): Promise<void> {
  return pedir<void>('/accounts/logout/', {
    metodo: 'POST',
    cuerpo: { refresh },
    token,
  })
}
