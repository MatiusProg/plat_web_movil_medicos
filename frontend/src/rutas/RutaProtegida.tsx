/**
 * Puerta de las pantallas que exigen sesión.
 *
 * Esto es comodidad, **no** seguridad: quien quiera puede saltearlo desde la
 * consola del navegador. La autorización de verdad la hace el backend, que
 * verifica el token en cada petición y filtra por organización con RLS. Acá
 * sólo se evita mostrar una pantalla que igual llegaría vacía.
 *
 * Guarda de dónde venía la persona para devolverla ahí después de entrar, en
 * lugar de dejarla en el inicio.
 */

import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { useSesion } from '@/sesion/useSesion'

export function RutaProtegida({ children }: { children: ReactNode }) {
  const { usuario } = useSesion()
  const ubicacion = useLocation()

  // No hace falta un estado de carga: `ProveedorSesion` lee `localStorage` en
  // su primer render, así que acá la sesión ya se sabe.
  if (!usuario) {
    return <Navigate to="/ingresar" replace state={{ desde: ubicacion.pathname }} />
  }

  return <>{children}</>
}
