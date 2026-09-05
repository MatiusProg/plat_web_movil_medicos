import {
    useEffect,
    useMemo,
    useState,
} from 'react'

import { useNavigate } from 'react-router-dom'

import {
    asignarPlan,
    listarPlanes,
    listarSuscripciones,
    type PlanSuscripcion,
    type Suscripcion,
} from '@/api/suscripciones'

import {
    ModalCambiarPlan,
    type DatosCambioPlan,
} from '@/componentes/ModalCambiarPlan'

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
        return '—'
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
        }
    }

    return {
        badge:
            'border-marca-900 bg-marca-950 text-marca-400',

        dot:
            'bg-marca-500',
    }
}


function planMasUsado(
    suscripciones: Suscripcion[],
): string {
    if (
        suscripciones.length === 0
    ) {
        return '—'
    }

    const conteo =
        new Map<string, number>()

    for (
        const suscripcion
        of suscripciones
        ) {
        const codigo =
            suscripcion.plan_code

        conteo.set(
            codigo,
            (
                conteo.get(codigo)
                ?? 0
            ) + 1,
        )
    }

    let codigoGanador = ''
    let cantidadGanadora = 0

    for (
        const [
            codigo,
            cantidad,
        ]
        of conteo
        ) {
        if (
            cantidad
            > cantidadGanadora
        ) {
            codigoGanador =
                codigo

            cantidadGanadora =
                cantidad
        }
    }

    return (
        suscripciones.find(
            (suscripcion) =>
                suscripcion.plan_code
                === codigoGanador,
        )?.plan_name
        ?? codigoGanador
    )
}


export function Suscripciones() {
    useTitulo(
        'Suscripciones',
    )

    const navigate =
        useNavigate()

    const [
        suscripciones,
        setSuscripciones,
    ] =
        useState<Suscripcion[]>([])

    const [
        planes,
        setPlanes,
    ] =
        useState<PlanSuscripcion[]>([])

    const [
        seleccionada,
        setSeleccionada,
    ] =
        useState<Suscripcion | null>(
            null,
        )

    const [
        modalAbierto,
        setModalAbierto,
    ] =
        useState(false)

    const [
        consulta,
        setConsulta,
    ] =
        useState('')

    const [
        cargando,
        setCargando,
    ] =
        useState(true)

    const [
        guardando,
        setGuardando,
    ] =
        useState(false)

    const [
        error,
        setError,
    ] =
        useState<string | null>(
            null,
        )


    const cargarDatos =
        async () => {
            setCargando(true)
            setError(null)

            try {
                const [
                    respuestaSuscripciones,
                    respuestaPlanes,
                ] =
                    await Promise.all([
                        listarSuscripciones(
                            true,
                        ),

                        listarPlanes(),
                    ])

                setSuscripciones(
                    respuestaSuscripciones
                        .results,
                )

                setPlanes(
                    respuestaPlanes
                        .results,
                )
            } catch (err) {
                setError(
                    textoError(err),
                )
            } finally {
                setCargando(false)
            }
        }


    useEffect(() => {
        void cargarDatos()
    }, [])


    const filtradas =
        useMemo(() => {
            const texto =
                consulta
                    .trim()
                    .toLowerCase()

            if (!texto) {
                return suscripciones
            }

            return suscripciones.filter(
                (suscripcion) =>
                    (
                        suscripcion
                            .organization_name
                            .toLowerCase()
                            .includes(texto)
                    )
                    ||
                    (
                        suscripcion
                            .organization_slug
                            .toLowerCase()
                            .includes(texto)
                    )
                    ||
                    (
                        suscripcion
                            .plan_name
                            .toLowerCase()
                            .includes(texto)
                    ),
            )
        }, [
            consulta,
            suscripciones,
        ])


    const activas =
        useMemo(
            () =>
                suscripciones.filter(
                    (suscripcion) =>
                        suscripcion.status
                        === 'active',
                ).length,
            [suscripciones],
        )


    const masUsado =
        useMemo(
            () =>
                planMasUsado(
                    suscripciones,
                ),
            [suscripciones],
        )


    function abrirCambio(
        suscripcion: Suscripcion,
    ) {
        setSeleccionada(
            suscripcion,
        )

        setModalAbierto(true)
    }


    function cerrarCambio() {
        if (guardando) {
            return
        }

        setModalAbierto(false)

        setSeleccionada(null)
    }


    async function confirmarCambio(
        datos: DatosCambioPlan,
    ) {
        if (!seleccionada) {
            return
        }

        setGuardando(true)
        setError(null)

        try {
            const nueva =
                await asignarPlan({
                    organization_id:
                    seleccionada.organization,

                    plan_id:
                    datos.planId,

                    starts_at:
                    datos.startsAt,

                    change_reason:
                    datos.reason,
                })

            setSuscripciones(
                (actuales) =>
                    actuales.map(
                        (suscripcion) =>
                            suscripcion.organization
                            === nueva.organization
                                ? nueva
                                : suscripcion,
                    ),
            )

            setModalAbierto(false)

            setSeleccionada(null)
        } catch (err) {
            setError(
                textoError(err),
            )
        } finally {
            setGuardando(false)
        }
    }


    function abrirHistorial(
        suscripcion: Suscripcion,
    ) {
        navigate(
            `/suscripciones/${suscripcion.organization}/historial`,
            {
                state: {
                    organization:
                    suscripcion
                        .organization_name,

                    slug:
                    suscripcion
                        .organization_slug,
                },
            },
        )
    }


    return (
        <>
            <main className="mx-auto w-full max-w-6xl px-8 py-10">

                {/* Encabezado */}

                <header className="mb-8">

                    <p className="text-sm font-medium text-marca-400">
                        Plataforma
                    </p>

                    <h1 className="mt-1 text-2xl font-semibold tracking-tight text-tinta-50">
                        Suscripciones
                    </h1>

                    <p className="mt-1.5 max-w-2xl text-[0.9375rem] leading-6 text-tinta-500">
                        Consulta el plan vigente de cada
                        organización y administra sus
                        cambios de suscripción.
                    </p>

                </header>


                {/* Error */}

                {error && (
                    <div className="mb-6 flex items-start justify-between gap-4 rounded-2xl border border-red-900 bg-red-950/40 px-5 py-4 text-sm text-red-300">

                        <div>

                            <p className="font-semibold">
                                No se pudo completar la operación
                            </p>

                            <p className="mt-1 text-red-400">
                                {error}
                            </p>

                        </div>


                        <button
                            type="button"
                            onClick={() =>
                                setError(null)
                            }
                            className="font-bold text-red-400 transition hover:text-red-300"
                            aria-label="Cerrar aviso"
                        >
                            ×
                        </button>

                    </div>
                )}


                {/* Resumen */}

                <section className="mb-7 grid grid-cols-1 gap-4 sm:grid-cols-3">

                    <Resumen
                        titulo="Suscripciones activas"
                        valor={String(
                            activas,
                        )}
                        valorClase="text-emerald-400"
                    />

                    <Resumen
                        titulo="Organizaciones"
                        valor={String(
                            suscripciones.length,
                        )}
                    />

                    <Resumen
                        titulo="Plan más utilizado"
                        valor={masUsado}
                        valorClase="text-marca-400"
                    />

                </section>


                {/* Tabla */}

                <section className="overflow-hidden rounded-2xl border border-tinta-800 bg-tinta-900/60">

                    <div className="flex flex-col gap-4 border-b border-tinta-800 p-5 md:flex-row md:items-center md:justify-between">

                        <div>

                            <h2 className="text-lg font-semibold text-tinta-50">
                                Organizaciones suscritas
                            </h2>

                            <p className="mt-1 text-sm text-tinta-500">
                                {filtradas.length}{' '}
                                {filtradas.length === 1
                                    ? 'resultado'
                                    : 'resultados'}
                            </p>

                        </div>


                        <div className="relative w-full md:w-80">

              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-tinta-500">
                <IconoBuscar />
              </span>

                            <input
                                value={consulta}
                                onChange={(evento) =>
                                    setConsulta(
                                        evento.target.value,
                                    )
                                }
                                placeholder="Buscar organización..."
                                className="h-11 w-full rounded-xl border border-tinta-800 bg-tinta-950 pl-10 pr-4 text-sm text-tinta-100 placeholder:text-tinta-500 outline-none transition focus:border-marca-600 focus:ring-2 focus:ring-marca-600/20"
                            />

                        </div>

                    </div>


                    {cargando ? (

                        <EstadoCargando />

                    ) : filtradas.length === 0 ? (

                        <EstadoVacio />

                    ) : (

                        <div className="overflow-x-auto">

                            <table className="w-full min-w-[900px]">

                                <thead>

                                <tr className="border-b border-tinta-800 bg-tinta-950/50 text-left">

                                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-tinta-500">
                                        Organización
                                    </th>

                                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-tinta-500">
                                        Plan actual
                                    </th>

                                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-tinta-500">
                                        Estado
                                    </th>

                                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-tinta-500">
                                        Inicio
                                    </th>

                                    <th className="px-6 py-4 text-right text-xs font-semibold uppercase tracking-wider text-tinta-500">
                                        Acciones
                                    </th>

                                </tr>

                                </thead>


                                <tbody>

                                {filtradas.map(
                                    (suscripcion) => {
                                        const estilos =
                                            estiloPlan(
                                                suscripcion
                                                    .plan_code,
                                            )

                                        return (
                                            <tr
                                                key={
                                                    suscripcion.id
                                                }
                                                className="border-b border-tinta-800 transition last:border-0 hover:bg-tinta-800/30"
                                            >

                                                {/* Organización */}

                                                <td className="px-6 py-5">

                                                    <div className="flex items-center gap-3">

                                                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-marca-950 text-marca-400">

                                                            <IconoEdificio />

                                                        </div>


                                                        <div className="min-w-0">

                                                            <p className="truncate font-semibold text-tinta-50">
                                                                {
                                                                    suscripcion
                                                                        .organization_name
                                                                }
                                                            </p>

                                                            <p className="mt-0.5 truncate text-xs text-tinta-500">
                                                                {
                                                                    suscripcion
                                                                        .organization_slug
                                                                }
                                                            </p>

                                                        </div>

                                                    </div>

                                                </td>


                                                {/* Plan */}

                                                <td className="px-6 py-5">

                            <span
                                className={[
                                    'inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold',
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

                                                </td>


                                                {/* Estado */}

                                                <td className="px-6 py-5">

                            <span
                                className={[
                                    'inline-flex items-center gap-2 text-sm font-medium',

                                    suscripcion.status
                                    === 'active'
                                        ? 'text-emerald-400'
                                        : 'text-tinta-500',
                                ].join(' ')}
                            >

                              <span
                                  className={[
                                      'h-2 w-2 rounded-full',

                                      suscripcion.status
                                      === 'active'
                                          ? 'bg-emerald-500'
                                          : 'bg-tinta-500',
                                  ].join(' ')}
                              />

                                {
                                    suscripcion.status
                                    === 'active'
                                        ? 'Activa'
                                        : 'Finalizada'
                                }

                            </span>

                                                </td>


                                                {/* Fecha */}

                                                <td className="px-6 py-5">

                                                    <div className="flex items-center gap-2 text-sm text-tinta-300">

                                                        <IconoCalendario />

                                                        {
                                                            fechaVisual(
                                                                suscripcion
                                                                    .starts_at,
                                                            )
                                                        }

                                                    </div>

                                                </td>


                                                {/* Acciones */}

                                                <td className="px-6 py-5">

                                                    <div className="flex items-center justify-end gap-2">

                                                        <button
                                                            type="button"
                                                            onClick={() =>
                                                                abrirHistorial(
                                                                    suscripcion,
                                                                )
                                                            }
                                                            className="rounded-xl border border-tinta-700 px-4 py-2 text-sm font-semibold text-tinta-300 transition hover:border-marca-800 hover:bg-marca-950 hover:text-marca-400"
                                                        >
                                                            Historial
                                                        </button>


                                                        <button
                                                            type="button"
                                                            onClick={() =>
                                                                abrirCambio(
                                                                    suscripcion,
                                                                )
                                                            }
                                                            className="flex items-center gap-2 rounded-xl bg-marca-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-marca-700"
                                                        >
                                                            Cambiar plan

                                                            <IconoFlecha />
                                                        </button>

                                                    </div>

                                                </td>

                                            </tr>
                                        )
                                    },
                                )}

                                </tbody>

                            </table>

                        </div>
                    )}

                </section>

            </main>


            {seleccionada && (
                <ModalCambiarPlan
                    abierto={
                        modalAbierto
                    }

                    organizacion={
                        seleccionada
                            .organization_name
                    }

                    planActualId={
                        seleccionada.plan
                    }

                    planes={planes}

                    guardando={
                        guardando
                    }

                    onCerrar={
                        cerrarCambio
                    }

                    onConfirmar={
                        confirmarCambio
                    }
                />
            )}

        </>
    )
}


function Resumen({
                     titulo,
                     valor,
                     valorClase =
                     'text-tinta-50',
                 }: {
    titulo: string
    valor: string
    valorClase?: string
}) {
    return (
        <div className="rounded-2xl border border-tinta-800 bg-tinta-900/60 p-5">

            <p className="text-sm text-tinta-500">
                {titulo}
            </p>

            <p
                className={`mt-1 text-2xl font-bold ${valorClase}`}
            >
                {valor}
            </p>

        </div>
    )
}


function EstadoCargando() {
    return (
        <div className="space-y-3 p-6">

            {[1, 2, 3, 4].map(
                (item) => (
                    <div
                        key={item}
                        className="h-16 animate-pulse rounded-xl bg-tinta-800"
                    />
                ),
            )}

        </div>
    )
}


function EstadoVacio() {
    return (
        <div className="px-6 py-14 text-center">

            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-tinta-800 text-tinta-400">

                <IconoEdificio />

            </div>

            <p className="mt-4 font-semibold text-tinta-300">
                No se encontraron suscripciones.
            </p>

            <p className="mt-1 text-sm text-tinta-500">
                No hay organizaciones que coincidan
                con la búsqueda.
            </p>

        </div>
    )
}


function IconoBuscar() {
    return (
        <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="h-[18px] w-[18px]"
            aria-hidden="true"
        >
            <circle
                cx="11"
                cy="11"
                r="7"
            />

            <path d="m20 20-4-4" />
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
            className="h-5 w-5"
            aria-hidden="true"
        >
            <path d="M4 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16" />

            <path d="M8 7h2M14 7h2M8 11h2M14 11h2M9 21v-5h4v5" />
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
            className="h-4 w-4 text-tinta-500"
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


function IconoFlecha() {
    return (
        <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="h-4 w-4"
            aria-hidden="true"
        >
            <path d="M5 12h14" />

            <path d="m13 6 6 6-6 6" />
        </svg>
    )
}