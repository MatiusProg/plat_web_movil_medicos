/**
 * Dónde vive la sesión entre recargas de la página.
 *
 * **Decisión y su costo.** Los tokens se guardan en `localStorage`. Es lo que
 * permite que recargar la pestaña no te eche, y es lo habitual en una SPA que
 * habla con una API por JWT. El costo es real y hay que decirlo: `localStorage`
 * es legible por cualquier JavaScript de la página, así que un XSS se lleva la
 * sesión. La alternativa —cookie `HttpOnly` + `SameSite`— es más segura pero
 * exige que el backend emita y lea cookies, que hoy no hace: `config/settings.py`
 * declara la API como pura, sin `SessionMiddleware`.
 *
 * Mitigación mientras tanto: el acceso dura 30 minutos y el refresco rota en
 * cada uso, así que una fuga tiene ventana corta. Queda anotado para revisar
 * antes de producción, en `docs/frontend/decisiones.md`.
 *
 * Todos los accesos van envueltos: en modo incógnito, con las cookies
 * bloqueadas o si la cuota está llena, `localStorage` lanza en vez de devolver
 * null, y una excepción acá dejaría la aplicación en blanco.
 */

import type { UsuarioSesion } from '@/api/tipos'

export const CLAVE_SESION = 'centro-medico.sesion'
/** El último centro médico usado, para no hacerlo tipear en cada visita. */
const CLAVE_ORGANIZACION = 'centro-medico.organizacion'

export interface SesionGuardada {
  access: string
  refresh: string
  usuario: UsuarioSesion
}

export function leerSesion(): SesionGuardada | null {
  try {
    const crudo = localStorage.getItem(CLAVE_SESION)
    if (!crudo) return null
    const dato = JSON.parse(crudo) as Partial<SesionGuardada>
    if (!dato.access || !dato.refresh || !dato.usuario) return null
    return dato as SesionGuardada
  } catch {
    return null
  }
}

export function guardarSesion(sesion: SesionGuardada): void {
  try {
    localStorage.setItem(CLAVE_SESION, JSON.stringify(sesion))
  } catch {
    // Sin persistencia la sesión sigue viva en memoria hasta que se recargue.
  }
}

export function borrarSesion(): void {
  try {
    localStorage.removeItem(CLAVE_SESION)
  } catch {
    /* nada que hacer */
  }
}

export function leerOrganizacion(): string {
  try {
    return localStorage.getItem(CLAVE_ORGANIZACION) ?? ''
  } catch {
    return ''
  }
}

export function guardarOrganizacion(slug: string): void {
  try {
    if (slug) localStorage.setItem(CLAVE_ORGANIZACION, slug)
    else localStorage.removeItem(CLAVE_ORGANIZACION)
  } catch {
    /* nada que hacer */
  }
}
