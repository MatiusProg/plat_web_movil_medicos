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
  /**
   * El token de acceso vigente, para que una pantalla pueda llamar a la API.
   *
   * Se renueva solo cada 25 minutos, así que hay que leerlo del contexto en
   * cada petición y no guardarlo en un estado local: una copia vieja produce
   * un 401 justo después de la renovación.
   */
  token: string | null
  entrar: (credenciales: Credenciales, senal?: AbortSignal) => Promise<UsuarioSesion>
  salir: () => Promise<void>
  /**
   * Atajo de `permissions.includes(...)` para decidir qué se muestra.
   *
   * **No sirve para el Superadministrador de Plataforma:** sus permisos llegan
   * vacíos. `user_roles` está protegida por RLS con
   * `organization_id = app_current_tenant()`, y las filas del superadmin irían
   * con `organization_id` NULL, que nunca compara verdadero — así que no puede
   * tener roles asignados. Para las pantallas de plataforma hay que mirar
   * `usuario.is_platform_admin`, igual que el backend, que usa la clase
   * `IsPlatformAdmin` y no `has_permission`.
   */
  puede: (permiso: string) => boolean
  /**
   * US-05 — Refleja en la sesión lo que cambió en el perfil, sin volver a
   * entrar: el nombre y el correo que muestra la barra, o el par de tokens
   * nuevo que devuelve el cambio de contraseña. Guardar el par es obligatorio:
   * el backend manda a la lista negra todos los refrescos anteriores.
   */
  actualizar: (cambios: CambiosSesion) => void
}

export interface CambiosSesion {
  usuario?: Partial<Pick<UsuarioSesion, 'full_name' | 'email'>>
  access?: string
  refresh?: string
}

export const ContextoSesion = createContext<EstadoSesion | null>(null)
