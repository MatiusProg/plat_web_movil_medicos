import { pedir } from './cliente'
import { leerSesion } from '@/sesion/almacenamiento'

export interface PlanSuscripcion {
    id: string
    code: string
    name: string
    description: string
    monthly_price: string
    currency: string
    max_branches: number | null
    max_users: number | null
    max_practitioners: number | null
    max_appointments_month: number | null
    max_ai_queries_month: number | null
    storage_mb: number | null
    features: Record<string, unknown>
    is_active: boolean
    created_at: string
    updated_at: string
}

export interface Suscripcion {
    id: string
    organization: string
    organization_name: string
    organization_slug: string
    plan: string
    plan_code: string
    plan_name: string
    starts_at: string
    ends_at: string | null
    status: string
    change_reason: string
    assigned_by: string | null
    assigned_by_email: string | null
    created_at: string
}

export interface RespuestaPaginada<T> {
    count: number
    next: string | null
    previous: string | null
    results: T[]
}

export interface DatosPlan {
    code: string
    name: string
    description?: string
    monthly_price: string
    currency: string
    max_branches: number | null
    max_users: number | null
    max_practitioners?: number | null
    max_appointments_month?: number | null
    max_ai_queries_month?: number | null
    storage_mb?: number | null
    features?: Record<string, unknown>
    is_active: boolean
}

export interface DatosAsignacionPlan {
    organization_id: string
    plan_id: string
    starts_at?: string
    change_reason?: string
}

function obtenerToken(): string {
    const sesion = leerSesion()

    if (!sesion?.access) {
        throw new Error('No hay una sesión activa.')
    }

    return sesion.access
}

export function listarPlanes(): Promise<RespuestaPaginada<PlanSuscripcion>> {
    return pedir<RespuestaPaginada<PlanSuscripcion>>('/platform/plans/', {
        token: obtenerToken(),
    })
}

export function crearPlan(datos: DatosPlan): Promise<PlanSuscripcion> {
    return pedir<PlanSuscripcion>('/platform/plans/', {
        metodo: 'POST',
        cuerpo: datos,
        token: obtenerToken(),
    })
}

export function actualizarPlan(
    id: string,
    datos: Partial<DatosPlan>,
): Promise<PlanSuscripcion> {
    return pedir<PlanSuscripcion>(`/platform/plans/${id}/`, {
        metodo: 'PATCH',
        cuerpo: datos,
        token: obtenerToken(),
    })
}

export function listarSuscripciones(
    soloVigentes = false,
): Promise<RespuestaPaginada<Suscripcion>> {
    const sufijo = soloVigentes ? '?current=true' : ''

    return pedir<RespuestaPaginada<Suscripcion>>(
        `/platform/subscriptions/${sufijo}`,
        {
            token: obtenerToken(),
        },
    )
}

export function asignarPlan(
    datos: DatosAsignacionPlan,
): Promise<Suscripcion> {
    return pedir<Suscripcion>('/platform/subscriptions/assign/', {
        metodo: 'POST',
        cuerpo: datos,
        token: obtenerToken(),
    })
}

export function listarHistorialOrganizacion(
    organizationId: string,
): Promise<RespuestaPaginada<Suscripcion>> {
    return pedir<RespuestaPaginada<Suscripcion>>(
        `/platform/organizations/${organizationId}/subscriptions/`,
        {
            token: obtenerToken(),
        },
    )
}