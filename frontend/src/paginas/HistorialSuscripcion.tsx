import {
    useEffect,
    useMemo,
    useState,
} from 'react'
import {
    Link,
    useLocation,
    useParams,
} from 'react-router-dom'

import {
    listarHistorialOrganizacion,
    type Suscripcion,
} from '@/api/suscripciones'

import { useTitulo } from '@/rutas/useTitulo'


type EstadoUbicacion = {
    organization?: string
    slug?: string
}


function textoError(
    error: unknown,
): string {
    if (
        error instanceof Error
        && error.message
    ) {
        return error.message
    }

    return 'Ocurrió un error inesperado.'
}


function fechaVisual(
    fecha: string | null,
): string {
    if (!fecha) {
        return 'Actualidad'
    }

    const [
        anio,
        mes,
        dia,
    ] = fecha.split('-')

    if (
        !anio
        || !mes
        || !dia
    ) {
        return fecha
    }

    return `${dia}/${mes}/${anio}`
}


function estiloPlan(
    codigo: string,
) {
    const normalizado =
        codigo.toLowerCase()

    if (
        normalizado.includes('basic')
        || normalizado.includes('basico')
        || normalizado.includes('básico')
    ) {
        return {
            borde:
                'border-blue-200',
            fondo:
                'bg-blue-50',
            texto:
                'text-blue-700',
            punto:
                'bg-blue-500',
        }
    }

    if (
        normalizado.includes('premium')
    ) {
        return {
            borde:
                'border-violet-200',
            fondo:
                'bg-violet-50',
            texto:
                'text-violet-700',
            punto:
                'bg-violet-500',
        }
    }

    return {
        borde:
            'border-cyan-200',
        fondo:
            'bg-cyan-50',
        texto:
            'text-cyan-700',
        punto:
            'bg-cyan-500',
    }
}


export function HistorialSuscripcion() {
    useTitulo(
        'Historial de suscripción',
    )

    const {
        organizationId,
    } =
        useParams<{
            organizationId: string
        }>()

    const location =
        useLocation()

    const estado =
        location.state as
            | EstadoUbicacion
            | null

    const [
        historial,
        setHistorial,
    ] =
        useState<Suscripcion[]>([])

    const [
        cargando,
        setCargando,
    ] =
        useState(true)

    const [
        error,
        setError,
    ] =
        useState<string | null>(
            null,
        )


    useEffect(() => {
        const cargar =
            async () => {
                if (!organizationId) {
                    setError(
                        'No se encontró la organización.',
                    )
                    setCargando(false)
                    return
                }

                setCargando(true)
                setError(null)

                try {
                    const respuesta =
                        await listarHistorialOrganizacion(
                            organizationId,
                        )

                    setHistorial(
                        respuesta.results,
                    )
                } catch (err) {
                    setError(
                        textoError(err),
                    )
                } finally {
                    setCargando(false)
                }
            }

        void cargar()
    }, [organizationId])


    const historialOrdenado =
        useMemo(
            () =>
                [...historial].sort(
                    (
                        primero,
                        segundo,
                    ) =>
                        segundo.starts_at.localeCompare(
                            primero.starts_at,
                        ),
                ),
            [historial],
        )


    const vigente =
        historialOrdenado.find(
            (suscripcion) =>
                suscripcion.ends_at
                === null,
        )
        ?? historialOrdenado[0]
        ?? null


    const nombreOrganizacion =
        estado?.organization
        ?? vigente?.organization_name
        ?? 'Organización'


    const slugOrganizacion =
        estado?.slug
        ?? vigente?.organization_slug
        ?? ''


    return (
        <div className="mx-auto w-full max-w-[1200px] px-8 py-8 xl:px-10">

            <div className="mb-8">

                <Link
                    to="/suscripciones"
                    className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 transition hover:text-blue-600"
                >
                    <IconoAtras />

                    Volver a suscripciones
                </Link>


                <div className="mt-6 flex flex-col gap-5 md:flex-row md:items-end md:justify-between">

                    <div>

                        <div className="mb-2">
              <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-600">
                Administración
              </span>
                        </div>

                        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
                            Historial de suscripción
                        </h1>

                        <p className="mt-2 text-sm text-slate-500">
                            Consulta todos los cambios
                            de plan realizados para
                            esta organización.
                        </p>

                    </div>


                    <div className="rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">

                        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                            Organización
                        </p>

                        <p className="mt-1 font-bold text-slate-900">
                            {nombreOrganizacion}
                        </p>

                        {slugOrganizacion && (
                            <p className="mt-1 text-xs text-slate-400">
                                {slugOrganizacion}
                            </p>
                        )}

                    </div>

                </div>

            </div>


            {error && (
                <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-5 py-4">

                    <p className="font-semibold text-red-700">
                        No se pudo cargar el historial
                    </p>

                    <p className="mt-1 text-sm text-red-600">
                        {error}
                    </p>

                </div>
            )}


            {cargando ? (
                <EstadoCargando />
            ) : historialOrdenado.length === 0 ? (
                <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center">

                    <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">
                        <IconoHistorial />
                    </div>

                    <h2 className="mt-5 text-xl font-bold text-slate-900">
                        Sin historial
                    </h2>

                    <p className="mt-2 text-sm text-slate-500">
                        Esta organización todavía no
                        tiene registros de suscripción.
                    </p>

                </div>
            ) : (
                <>
                    {vigente && (
                        <section className="mb-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">

                            <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">

                                <div>

                                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                                        Plan vigente
                                    </p>

                                    <h2 className="mt-2 text-2xl font-bold text-slate-900">
                                        {vigente.plan_name}
                                    </h2>

                                    <div className="mt-3 flex items-center gap-2 text-sm text-slate-500">

                                        <IconoCalendario />

                                        Desde{' '}
                                        {fechaVisual(
                                            vigente.starts_at,
                                        )}

                                    </div>

                                </div>


                                <span className="inline-flex w-fit items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-700">

                  <span className="h-2 w-2 rounded-full bg-emerald-500" />

                  Suscripción activa

                </span>

                            </div>

                        </section>
                    )}


                    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">

                        <div className="mb-7">

                            <h2 className="text-lg font-bold text-slate-900">
                                Línea de tiempo
                            </h2>

                            <p className="mt-1 text-sm text-slate-500">
                                {historialOrdenado.length}{' '}
                                {historialOrdenado.length === 1
                                    ? 'registro'
                                    : 'registros'}
                            </p>

                        </div>


                        <div className="relative">

                            <div className="absolute bottom-3 left-[19px] top-3 w-px bg-slate-200" />


                            <div className="space-y-8">

                                {historialOrdenado.map(
                                    (
                                        suscripcion,
                                        indice,
                                    ) => {
                                        const estilos =
                                            estiloPlan(
                                                suscripcion.plan_code,
                                            )

                                        const activa =
                                            suscripcion.ends_at
                                            === null

                                        return (
                                            <article
                                                key={
                                                    suscripcion.id
                                                }
                                                className="relative flex gap-5"
                                            >

                                                <div
                                                    className={[
                                                        'relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-4 border-white shadow-sm',
                                                        activa
                                                            ? 'bg-emerald-500 text-white'
                                                            : 'bg-slate-200 text-slate-500',
                                                    ].join(' ')}
                                                >
                                                    {activa
                                                        ? <IconoCheck />
                                                        : indice + 1}
                                                </div>


                                                <div className="min-w-0 flex-1 rounded-2xl border border-slate-200 bg-slate-50/60 p-5">

                                                    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">

                                                        <div>

                                                            <div className="flex flex-wrap items-center gap-2">

                                <span
                                    className={[
                                        'inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold',
                                        estilos.borde,
                                        estilos.fondo,
                                        estilos.texto,
                                    ].join(' ')}
                                >
                                  <span
                                      className={[
                                          'h-2 w-2 rounded-full',
                                          estilos.punto,
                                      ].join(' ')}
                                  />

                                    {
                                        suscripcion.plan_name
                                    }
                                </span>


                                                                {activa ? (
                                                                    <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
                                    Activa
                                  </span>
                                                                ) : (
                                                                    <span className="rounded-full bg-slate-200 px-3 py-1 text-xs font-semibold text-slate-600">
                                    Finalizada
                                  </span>
                                                                )}

                                                            </div>


                                                            <div className="mt-4 grid gap-3 text-sm text-slate-500 sm:grid-cols-2">

                                                                <DatoFecha
                                                                    titulo="Inicio"
                                                                    valor={
                                                                        fechaVisual(
                                                                            suscripcion.starts_at,
                                                                        )
                                                                    }
                                                                />

                                                                <DatoFecha
                                                                    titulo="Fin"
                                                                    valor={
                                                                        fechaVisual(
                                                                            suscripcion.ends_at,
                                                                        )
                                                                    }
                                                                />

                                                            </div>

                                                        </div>


                                                        {suscripcion.assigned_by_email && (
                                                            <div className="text-left sm:text-right">

                                                                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                                                                    Asignado por
                                                                </p>

                                                                <p className="mt-1 text-sm font-medium text-slate-600">
                                                                    {
                                                                        suscripcion.assigned_by_email
                                                                    }
                                                                </p>

                                                            </div>
                                                        )}

                                                    </div>


                                                    {suscripcion.change_reason && (
                                                        <div className="mt-5 rounded-xl border border-slate-200 bg-white p-4">

                                                            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                                                                Motivo del cambio
                                                            </p>

                                                            <p className="mt-1 text-sm leading-6 text-slate-600">
                                                                {
                                                                    suscripcion.change_reason
                                                                }
                                                            </p>

                                                        </div>
                                                    )}

                                                </div>

                                            </article>
                                        )
                                    },
                                )}

                            </div>

                        </div>

                    </section>
                </>
            )}

        </div>
    )
}


function DatoFecha({
                       titulo,
                       valor,
                   }: {
    titulo: string
    valor: string
}) {
    return (
        <div className="flex items-center gap-2">

            <IconoCalendario />

            <div>
                <p className="text-xs text-slate-400">
                    {titulo}
                </p>

                <p className="font-medium text-slate-600">
                    {valor}
                </p>
            </div>

        </div>
    )
}


function EstadoCargando() {
    return (
        <div className="space-y-5">

            <div className="h-32 animate-pulse rounded-3xl bg-slate-100" />

            <div className="rounded-3xl border border-slate-200 bg-white p-6">

                {[1, 2, 3].map(
                    (item) => (
                        <div
                            key={item}
                            className="mb-5 h-28 animate-pulse rounded-2xl bg-slate-100 last:mb-0"
                        />
                    ),
                )}

            </div>

        </div>
    )
}


function IconoAtras() {
    return (
        <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="h-4 w-4"
            aria-hidden="true"
        >
            <path d="m15 18-6-6 6-6" />
        </svg>
    )
}


function IconoCalendario() {
    return (
        <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            className="h-4 w-4 text-slate-400"
            aria-hidden="true"
        >
            <rect
                x="3"
                y="5"
                width="18"
                height="16"
                rx="2"
            />
            <path d="M8 3v4M16 3v4M3 10h18" />
        </svg>
    )
}


function IconoHistorial() {
    return (
        <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            className="h-6 w-6"
            aria-hidden="true"
        >
            <circle
                cx="12"
                cy="12"
                r="9"
            />
            <path d="M12 7v5l3 2" />
            <path d="M3 12H1" />
        </svg>
    )
}


function IconoCheck() {
    return (
        <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            className="h-4 w-4"
            aria-hidden="true"
        >
            <path d="m5 12 4 4L19 6" />
        </svg>
    )
}