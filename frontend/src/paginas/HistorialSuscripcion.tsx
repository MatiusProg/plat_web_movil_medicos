import {
    useEffect,
    useMemo,
    useState,
} from 'react'

import {
    useLocation,
    useNavigate,
    useParams,
} from 'react-router-dom'

import {
    listarHistorialOrganizacion,
    type Suscripcion,
} from '@/api/suscripciones'

import { useTitulo } from '@/rutas/useTitulo'


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
        return 'Vigente'
    }

    const [
        anio,
        mes,
        dia,
    ] =
        fecha.split('-')

    if (
        !anio
        || !mes
        || !dia
    ) {
        return fecha
    }

    return `${dia}/${mes}/${anio}`
}


function fechaHoraVisual(
    fecha: string | null,
): string {
    if (!fecha) {
        return '—'
    }

    const valor =
        new Date(fecha)

    if (
        Number.isNaN(
            valor.getTime(),
        )
    ) {
        return fecha
    }

    return valor.toLocaleString(
        'es-BO',
        {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        },
    )
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
            badge:
                'border-blue-900 bg-blue-950 text-blue-400',

            dot:
                'bg-blue-500',

            linea:
                'bg-blue-700',
        }
    }

    if (
        normalizado.includes('premium')
    ) {
        return {
            badge:
                'border-violet-900 bg-violet-950 text-violet-400',

            dot:
                'bg-violet-500',

            linea:
                'bg-violet-700',
        }
    }

    return {
        badge:
            'border-marca-900 bg-marca-950 text-marca-400',

        dot:
            'bg-marca-500',

        linea:
            'bg-marca-700',
    }
}


type EstadoNavegacion = {
    organization?: string
    slug?: string
}


export function HistorialSuscripcion() {
    const {
        organizationId,
    } =
        useParams<{
            organizationId: string
        }>()

    const navigate =
        useNavigate()

    const location =
        useLocation()

    const estado = location.state as EstadoNavegacion | null

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

    useTitulo(
        'Historial de suscripción',
    )


    useEffect(() => {
        if (!organizationId) {
            setError(
                'No se recibió una organización válida.',
            )

            setCargando(false)

            return
        }

        const cargar =
            async () => {
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
    }, [
        organizationId,
    ])


    const ordenado =
        useMemo(
            () =>
                [...historial].sort(
                    (a, b) =>
                        new Date(
                            b.starts_at,
                        ).getTime()
                        -
                        new Date(
                            a.starts_at,
                        ).getTime(),
                ),
            [historial],
        )


    const organizacion =
        estado?.organization
        ?? ordenado[0]
            ?.organization_name
        ?? 'Organización'


    const slug =
        estado?.slug
        ?? ordenado[0]
            ?.organization_slug
        ?? ''


    return (
        <main className="mx-auto w-full max-w-5xl px-8 py-10">

            {/* Volver */}

            <button
                type="button"
                onClick={() =>
                    navigate(
                        '/suscripciones',
                    )
                }
                className="mb-6 inline-flex items-center gap-2 text-sm font-medium text-tinta-400 transition hover:text-marca-400"
            >
                <IconoVolver />

                Volver a suscripciones
            </button>


            {/* Encabezado */}

            <header className="mb-8">

                <p className="text-sm font-medium text-marca-400">
                    Plataforma
                </p>

                <h1 className="mt-1 text-2xl font-semibold tracking-tight text-tinta-50">
                    Historial de suscripción
                </h1>

                <p className="mt-1.5 max-w-2xl text-[0.9375rem] leading-6 text-tinta-500">
                    Consulta todos los cambios de plan realizados
                    para esta organización.
                </p>

            </header>


            {/* Organización */}

            <section className="mb-7 rounded-2xl border border-tinta-800 bg-tinta-900/60 p-5">

                <div className="flex flex-wrap items-center justify-between gap-4">

                    <div className="flex items-center gap-4">

                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-marca-950 text-marca-400">

                            <IconoEdificio />

                        </div>


                        <div>

                            <p className="text-xs font-semibold uppercase tracking-wider text-tinta-500">
                                Organización
                            </p>

                            <h2 className="mt-1 text-lg font-semibold text-tinta-50">
                                {organizacion}
                            </h2>

                            {slug && (
                                <p className="mt-0.5 text-sm text-tinta-500">
                                    {slug}
                                </p>
                            )}

                        </div>

                    </div>


                    <div className="rounded-xl border border-tinta-800 bg-tinta-950 px-4 py-3 text-right">

                        <p className="text-xs text-tinta-500">
                            Cambios registrados
                        </p>

                        <p className="mt-1 text-xl font-bold text-tinta-100">
                            {historial.length}
                        </p>

                    </div>

                </div>

            </section>


            {/* Error */}

            {error && (
                <div className="mb-6 rounded-2xl border border-red-900 bg-red-950/40 px-5 py-4">

                    <p className="font-semibold text-red-300">
                        No se pudo cargar el historial
                    </p>

                    <p className="mt-1 text-sm text-red-400">
                        {error}
                    </p>

                </div>
            )}


            {/* Contenido */}

            {cargando ? (

                <EstadoCargando />

            ) : ordenado.length === 0
            && !error ? (

                <EstadoVacio />

            ) : (

                <section className="rounded-2xl border border-tinta-800 bg-tinta-900/60">

                    <div className="border-b border-tinta-800 px-6 py-5">

                        <h2 className="font-semibold text-tinta-50">
                            Línea de tiempo
                        </h2>

                        <p className="mt-1 text-sm text-tinta-500">
                            Los cambios más recientes aparecen primero.
                        </p>

                    </div>


                    <div className="p-6">

                        <div className="relative">

                            {ordenado.map(
                                (
                                    suscripcion,
                                    indice,
                                ) => {
                                    const estilos =
                                        estiloPlan(
                                            suscripcion.plan_code,
                                        )

                                    const vigente =
                                        suscripcion.status
                                        === 'active'
                                        && !suscripcion.ends_at

                                    const ultimo =
                                        indice
                                        === ordenado.length
                                        - 1

                                    return (
                                        <div
                                            key={
                                                suscripcion.id
                                            }
                                            className="relative flex gap-5 pb-8 last:pb-0"
                                        >

                                            {/* Línea */}

                                            {!ultimo && (
                                                <div className="absolute left-[17px] top-9 h-[calc(100%-18px)] w-px bg-tinta-700" />
                                            )}


                                            {/* Punto */}

                                            <div
                                                className={[
                                                    'relative z-10 mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border',
                                                    vigente
                                                        ? 'border-emerald-700 bg-emerald-950'
                                                        : 'border-tinta-700 bg-tinta-900',
                                                ].join(' ')}
                                            >

                        <span
                            className={[
                                'h-2.5 w-2.5 rounded-full',
                                vigente
                                    ? 'bg-emerald-500'
                                    : estilos.dot,
                            ].join(' ')}
                        />

                                            </div>


                                            {/* Tarjeta */}

                                            <article className="min-w-0 flex-1 rounded-2xl border border-tinta-800 bg-tinta-950/40 p-5">

                                                <div className="flex flex-wrap items-start justify-between gap-4">

                                                    <div>

                                                        <div className="flex flex-wrap items-center gap-2">

                              <span
                                  className={[
                                      'inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold',
                                      estilos.badge,
                                  ].join(' ')}
                              >

                                <span
                                    className={[
                                        'h-2 w-2 rounded-full',
                                        estilos.dot,
                                    ].join(' ')}
                                />

                                  {
                                      suscripcion
                                          .plan_name
                                  }

                              </span>


                                                            {vigente && (
                                                                <span className="rounded-full border border-emerald-900 bg-emerald-950 px-3 py-1 text-xs font-semibold text-emerald-400">
                                  PLAN VIGENTE
                                </span>
                                                            )}

                                                        </div>


                                                        <p className="mt-3 text-sm text-tinta-400">
                                                            Vigencia
                                                        </p>

                                                        <p className="mt-1 font-medium text-tinta-200">
                                                            {
                                                                fechaVisual(
                                                                    suscripcion
                                                                        .starts_at,
                                                                )
                                                            }
                                                            {' → '}
                                                            {
                                                                fechaVisual(
                                                                    suscripcion
                                                                        .ends_at,
                                                                )
                                                            }
                                                        </p>

                                                    </div>


                                                    <div className="text-right">

                                                        <p className="text-xs text-tinta-500">
                                                            Estado
                                                        </p>

                                                        <p
                                                            className={[
                                                                'mt-1 text-sm font-semibold',
                                                                vigente
                                                                    ? 'text-emerald-400'
                                                                    : 'text-tinta-400',
                                                            ].join(' ')}
                                                        >
                                                            {vigente
                                                                ? 'Activa'
                                                                : 'Finalizada'}
                                                        </p>

                                                    </div>

                                                </div>


                                                <div className="my-5 h-px bg-tinta-800" />


                                                <dl className="grid gap-5 sm:grid-cols-2">

                                                    <Dato
                                                        titulo="Asignado por"
                                                        valor={
                                                            suscripcion
                                                                .assigned_by_email
                                                            ?? '—'
                                                        }
                                                    />

                                                    <Dato
                                                        titulo="Fecha del registro"
                                                        valor={
                                                            fechaHoraVisual(
                                                                suscripcion
                                                                    .created_at,
                                                            )
                                                        }
                                                    />

                                                    <Dato
                                                        titulo="Motivo del cambio"
                                                        valor={
                                                            suscripcion
                                                                .change_reason
                                                            || 'Sin motivo registrado'
                                                        }
                                                        ancho
                                                    />

                                                </dl>

                                            </article>

                                        </div>
                                    )
                                },
                            )}

                        </div>

                    </div>

                </section>
            )}

        </main>
    )
}


function Dato({
                  titulo,
                  valor,
                  ancho = false,
              }: {
    titulo: string
    valor: string
    ancho?: boolean
}) {
    return (
        <div
            className={
                ancho
                    ? 'sm:col-span-2'
                    : ''
            }
        >
            <dt className="text-xs font-medium uppercase tracking-wider text-tinta-500">
                {titulo}
            </dt>

            <dd className="mt-1.5 text-sm leading-6 text-tinta-200">
                {valor}
            </dd>
        </div>
    )
}


function EstadoCargando() {
    return (
        <div className="space-y-4">

            {[1, 2, 3].map(
                (item) => (
                    <div
                        key={item}
                        className="h-40 animate-pulse rounded-2xl border border-tinta-800 bg-tinta-900/60"
                    />
                ),
            )}

        </div>
    )
}


function EstadoVacio() {
    return (
        <div className="rounded-2xl border border-dashed border-tinta-700 bg-tinta-900/50 px-6 py-14 text-center">

            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-tinta-800 text-tinta-400">

                <IconoHistorial />

            </div>

            <h2 className="mt-4 font-semibold text-tinta-200">
                Sin historial disponible
            </h2>

            <p className="mt-1 text-sm text-tinta-500">
                Esta organización todavía no tiene
                cambios de suscripción registrados.
            </p>

        </div>
    )
}


function IconoVolver() {
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


function IconoEdificio() {
    return (
        <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            className="h-6 w-6"
            aria-hidden="true"
        >
            <path d="M4 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16" />

            <path d="M8 7h2M14 7h2M8 11h2M14 11h2M9 21v-5h4v5" />
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
            className="h-5 w-5"
            aria-hidden="true"
        >
            <path d="M3 12a9 9 0 1 0 3-6.7" />

            <path d="M3 4v5h5" />

            <path d="M12 7v5l3 2" />
        </svg>
    )
}