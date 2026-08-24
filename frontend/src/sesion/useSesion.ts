import { useContext } from 'react'

import { ContextoSesion, type EstadoSesion } from './contexto'

/**
 * Acceso a la sesión desde cualquier componente.
 *
 * Está en su propio archivo y no junto al contexto porque Vite recarga en
 * caliente sólo los módulos que exportan componentes; mezclar un hook con el
 * proveedor hace que cada cambio recargue la página entera y se pierda el
 * estado del formulario que estabas probando.
 */
export function useSesion(): EstadoSesion {
  const contexto = useContext(ContextoSesion)
  if (!contexto) {
    throw new Error('useSesion se usó fuera de <ProveedorSesion>.')
  }
  return contexto
}
