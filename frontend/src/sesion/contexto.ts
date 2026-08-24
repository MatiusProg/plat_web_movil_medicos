import { createContext } from 'react'

import type { Credenciales } from '@/api/autenticacion'
import type { UsuarioSesion } from '@/api/tipos'

/**
 * El contexto y su tipo, separados del proveedor.
 *
 * Vite recarga en caliente sólo los módulos que exportan **nada más que**
 * componentes. Con el `createContext` en el mismo archivo que
 * `<ProveedorSesion>`, cada cambio recarga la página entera y se pierde lo que
 * estabas escribiendo en el formulario que probabas.
 */
export interface EstadoSesion {
  usuario: UsuarioSesion | null
  entrar: (credenciales: Credenciales, senal?: AbortSignal) => Promise<UsuarioSesion>
  salir: () => Promise<void>
  /** Atajo de `permissions.includes(...)`, que es lo que se usa en el menú. */
  puede: (permiso: string) => boolean
}

export const ContextoSesion = createContext<EstadoSesion | null>(null)
