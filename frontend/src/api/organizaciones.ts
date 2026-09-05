/**
 * US-43 — Alta y consulta de organizaciones (RF-W-01).
 *
 * Los tipos viven acá y no en `api/tipos.ts` a propósito: ese archivo es el
 * contrato de `accounts` y lo comparten todas las historias. Cada historia que
 * agregue endpoints trae su propio módulo, y así dos personas no editan el
 * mismo archivo el mismo sprint — la misma regla que el backend aplica en
 * `views/` y `serializers/`.
 *
 * Los nombres de los campos van en inglés porque son los que devuelve el
 * backend. Traducirlos acá obligaría a mantener dos vocabularios.
 */

import { pedir, type Contexto } from './cliente'

export interface PlanVigente {
  code: string
  name: string
  starts_at: string
}

export interface Organizacion {
  id: string
  slug: string
  name: string
  legal_name: string
  tax_id: string
  contact_email: string
  contact_phone: string
  address: string
  city: string
  country: string
  logo_url: string
  primary_color: string
  secondary_color: string
  timezone: string
  status: 'active' | 'suspended' | 'inactive'
  onboarded_at: string
  /** `null` mientras no tenga una suscripción sin fecha de fin. */
  current_plan: PlanVigente | null
  created_at: string
}

/** El primer usuario de la organización. No lleva contraseña: la genera el backend. */
export interface AdministradorNuevo {
  email: string
  first_name: string
  last_name: string
  document_number: string
  document_type?: string
  phone?: string
}

export interface AltaOrganizacion {
  slug: string
  name: string
  legal_name: string
  tax_id: string
  contact_email: string
  contact_phone?: string
  address?: string
  city?: string
  plan_code: string
  admin: AdministradorNuevo
}

/**
 * Lo que devuelve el alta: la organización creada más los datos del
 * administrador, con su contraseña temporal.
 *
 * **`temporary_password` se ve una sola vez.** No se guarda en ningún lado ni
 * se puede volver a consultar: en la base queda sólo su hash. Si se pierde, se
 * resuelve por el flujo de recuperación, no preguntándole al backend.
 */
export interface OrganizacionCreada extends Organizacion {
  admin: {
    id: string
    email: string
    role: string
    temporary_password: string
  }
}

interface Pagina<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export function listarOrganizaciones(
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Pagina<Organizacion>> {
  return pedir<Pagina<Organizacion>>('/platform/organizations/', {
    ...contexto,
    senal,
  })
}

export function crearOrganizacion(
  datos: AltaOrganizacion,
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<OrganizacionCreada> {
  return pedir<OrganizacionCreada>('/platform/organizations/', {
    ...contexto,
    metodo: 'POST',
    cuerpo: datos,
    senal,
  })
}

/** Los planes del catálogo, para el desplegable del alta. */
export interface Plan {
  id: string
  code: string
  name: string
  monthly_price: string
  currency: string
  is_active: boolean
}

export function listarPlanes(
  contexto: Contexto,
  senal?: AbortSignal,
): Promise<Pagina<Plan>> {
  return pedir<Pagina<Plan>>('/platform/plans/?is_active=true', {
    ...contexto,
    senal,
  })
}
