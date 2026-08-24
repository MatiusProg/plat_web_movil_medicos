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


function textoError(error: unknown): string {
    if (error instanceof Error && error.message) {
        return error.message
    }

    return 'Ocurrió un error inesperado.'
}


function fechaVisual(fecha: string | null): string {
    if (!fecha) return '—'

    const [anio, mes, dia] = fecha.split('-')

    if (!anio || !mes || !dia) {
        return fecha
    }

    return `${dia}/${mes}/${anio}`
}


function estiloPlan(codigo: string) {
    const normalizado = codigo.toLowerCase()

    if (
        normalizado.includes('basic') ||
        normalizado.includes('basico') ||
        normalizado.includes('básico')
    ) {
        return {
            badge:
                'border-blue-200 bg-blue-50 text-blue-700',
            dot:
                'bg-blue-500',
        }
    }

    if (normalizado.includes('premium')) {
        return {
            badge:
                'border-violet-200 bg-violet-50 text-violet-700',
            dot:
                'bg-violet-500',
        }
    }

    return {
        badge:
            'border-cyan-200 bg-cyan-50 text-cyan-700',
        dot:
            'bg-cyan-500',
    }
}


function planMasUsado(
    suscripciones: Suscripcion[],
): string {
    if (suscripciones.length === 0) {
        return '—'
    }

    const conteo = new Map<string, number>()

    for (const suscripcion of suscripciones) {
        const codigo = suscripcion.plan_code

        conteo.set(
            codigo,
            (conteo.get(codigo) ?? 0) + 1,
        )
    }

    let codigoGanador = ''
    let cantidadGanadora = 0

    for (const [codigo, cantidad] of conteo) {
        if (cantidad > cantidadGanadora) {
            codigoGanador = codigo
            cantidadGanadora = cantidad
        }
    }

    return (
        suscripciones.find(
            (suscripcion) =>
                suscripcion.plan_code === codigoGanador,
        )?.plan_name ?? codigoGanador
    )
}


export function Suscripciones() {
    useTitulo('Suscripciones')

    const navigate = useNavigate()

    const [
        suscripciones,
        setSuscripciones,
    ] = useState<Suscripcion[]>([])

    const [
        planes,
        setPlanes,
    ] = useState<PlanSuscripcion[]>([])

    const [
        seleccionada,
        setSeleccionada,
    ] = useState<Suscripcion | null>(null)

    const [
        modalAbierto,
        setModalAbierto,
    ] = useState(false)

    const [
        consulta,
        setConsulta,
    ] = useState('')

    const [
        cargando,
        setCargando,
    ] = useState(true)

    const [
        guardando,
        setGuardando,
    ] = useState(false)

    const [
        error,
        setError,
    ] = useState<string | null>(null)


    const cargarDatos = async () => {
        setCargando(true)
        setError(null)

        try {
            const [
                respuestaSuscripciones,
                respuestaPlanes,
            ] = await Promise.all([
                listarSuscripciones(true),
                listarPlanes(),
            ])

            setSuscripciones(
                respuestaSuscripciones.results,
            )

            setPlanes(
                respuestaPlanes.results,
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
                (suscripcion) => {
                    return (
                        suscripcion.organization_name
                            .toLowerCase()
                            .includes(texto)
                        ||
                        suscripcion.organization_slug
                            .toLowerCase()
                            .includes(texto)
                        ||
                        suscripcion.plan_name
                            .toLowerCase()
                            .includes(texto)
                    )
                },
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
                        suscripcion.status === 'active',
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
        setSeleccionada(suscripcion)
        setModalAbierto(true)
    }


    function cerrarCambio() {
        if (guardando) return

        setModalAbierto(false)
        setSeleccionada(null)
    }


    async function confirmarCambio(
        datos: DatosCambioPlan,
    ) {
        if (!seleccionada) return

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
                    suscripcion.organization_name,

                    slug:
                    suscripcion.organization_slug,
                },
            },
        )
    }


    return (
        <>
            <div className="mx-auto w-full max-w-[1500px] px-8 py-8 xl:px-10">

                <header className="mb-8">
                    <div className="mb-2">
            <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-600">
              Administración
            </span>
                    </div>

                    <h1 className="text-3xl font-bold tracking-tight text-slate-900">
                        Suscripciones
                    </h1>

                    <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                        Consulta el plan vigente de cada organización
                        y administra sus cambios de suscripción.
                    </p>
                </header>


                {error && (
                    <div className="mb-6 flex items-start justify-between gap-4 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
                        <div>
                            <p className="font-semibold">
                                No se pudo completar la operación
                            </p>

                            <p className="mt-1">
                                {error}
                            </p>
                        </div>

                        <button
                            type="button"
                            onClick={() =>
                                setError(null)
                            }
                            className="font-bold"
                            aria-label="Cerrar aviso"
                        >
                            ×
                        </button>
                    </div>
                )}


                <section className="mb-7 grid grid-cols-1 gap-4 sm:grid-cols-3">

                    <Resumen
                        titulo="Suscripciones activas"
                        valor={String(activas)}
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
                        valorClase="text-cyan-600"
                    />

                </section>


                <section className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">

                    <div className="flex flex-col gap-4 border-b border-slate-200 p-5 md:flex-row md:items-center md:justify-between">

                        <div>
                            <h2 className="text-lg font-bold text-slate-900">
                                Organizaciones suscritas
                            </h2>

                            <p className="mt-1 text-sm text-slate-500">
                                {filtradas.length} resultados
                            </p>
                        </div>


                        <div className="relative w-full md:w-80">

              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
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
                                className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 pl-10 pr-4 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-100"
                            />

                        </div>

                    </div>


                    {cargando ? (
                        <div className="space-y-3 p-6">
                            {[1, 2, 3, 4].map(
                                (item) => (
                                    <div
                                        key={item}
                                        className="h-16 animate-pulse rounded-xl bg-slate-100"
                                    />
                                ),
                            )}
                        </div>
                    ) : filtradas.length === 0 ? (
                        <div className="px-6 py-14 text-center">
                            <p className="font-semibold text-slate-700">
                                No se encontraron suscripciones.
                            </p>

                            <p className="mt-1 text-sm text-slate-500">
                                No hay organizaciones que coincidan con la búsqueda.
                            </p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">

                            <table className="w-full min-w-[900px]">

                                <thead>
                                <tr className="border-b border-slate-200 bg-slate-50/80 text-left">

                                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500">
                                        Organización
                                    </th>

                                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500">
                                        Plan actual
                                    </th>

                                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500">
                                        Estado
                                    </th>

                                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500">
                                        Inicio
                                    </th>

                                    <th className="px-6 py-4 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">
                                        Acciones
                                    </th>

                                </tr>
                                </thead>


                                <tbody>

                                {filtradas.map(
                                    (suscripcion) => {
                                        const estilos =
                                            estiloPlan(
                                                suscripcion.plan_code,
                                            )

                                        return (
                                            <tr
                                                key={suscripcion.id}
                                                className="border-b border-slate-100 last:border-0"
                                            >

                                                <td className="px-6 py-5">

                                                    <div className="flex items-center gap-3">

                                                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                                                            <IconoEdificio />
                                                        </div>

                                                        <div>
                                                            <p className="font-semibold text-slate-900">
                                                                {
                                                                    suscripcion.organization_name
                                                                }
                                                            </p>

                                                            <p className="mt-0.5 text-xs text-slate-400">
                                                                {
                                                                    suscripcion.organization_slug
                                                                }
                                                            </p>
                                                        </div>

                                                    </div>

                                                </td>


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
                                    suscripcion.plan_name
                                }
                            </span>

                                                </td>


                                                <td className="px-6 py-5">

                            <span
                                className={[
                                    'inline-flex items-center gap-2 text-sm font-medium',
                                    suscripcion.status === 'active'
                                        ? 'text-emerald-600'
                                        : 'text-slate-500',
                                ].join(' ')}
                            >
                              <span
                                  className={[
                                      'h-2 w-2 rounded-full',
                                      suscripcion.status === 'active'
                                          ? 'bg-emerald-500'
                                          : 'bg-slate-400',
                                  ].join(' ')}
                              />

                                {suscripcion.status === 'active'
                                    ? 'Activa'
                                    : 'Finalizada'}
                            </span>

                                                </td>


                                                <td className="px-6 py-5">

                                                    <div className="flex items-center gap-2 text-sm text-slate-600">

                                                        <IconoCalendario />

                                                        {
                                                            fechaVisual(
                                                                suscripcion.starts_at,
                                                            )
                                                        }

                                                    </div>

                                                </td>


                                                <td className="px-6 py-5">

                                                    <div className="flex items-center justify-end gap-2">

                                                        <button
                                                            type="button"
                                                            onClick={() =>
                                                                abrirHistorial(
                                                                    suscripcion,
                                                                )
                                                            }
                                                            className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-600"
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
                                                            className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
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

            </div>


            {seleccionada && (
                <ModalCambiarPlan
                    abierto={modalAbierto}

                    organizacion={
                        seleccionada.organization_name
                    }

                    planActualId={
                        seleccionada.plan
                    }

                    planes={planes}

                    guardando={guardando}

                    onCerrar={cerrarCambio}

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
                     valorClase = 'text-slate-900',
                 }: {
    titulo: string
    valor: string
    valorClase?: string
}) {
    return (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">
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
            <circle cx="11" cy="11" r="7" />
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