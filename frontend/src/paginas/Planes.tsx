import {
    useEffect,
    useMemo,
    useState,
} from 'react'

import {
    actualizarPlan,
    crearPlan,
    listarPlanes,
    type DatosPlan,
    type PlanSuscripcion,
} from '@/api/suscripciones'

import {
    ModalPlan,
    type DatosFormularioPlan,
} from '@/componentes/ModalPlan'

import { useTitulo } from '@/rutas/useTitulo'


type TipoVisualPlan =
    | 'basic'
    | 'pro'
    | 'premium'

type FiltroPlanes =
    | 'todos'
    | 'activos'
    | 'inactivos'


function tipoVisual(
    codigo: string,
): TipoVisualPlan {
    const normalizado =
        codigo.toLowerCase()

    if (
        normalizado.includes('basic')
        || normalizado.includes('basico')
        || normalizado.includes('básico')
    ) {
        return 'basic'
    }

    if (
        normalizado.includes('premium')
    ) {
        return 'premium'
    }

    return 'pro'
}


function temaPlan(
    tipo: TipoVisualPlan,
) {
    if (tipo === 'basic') {
        return {
            icono:
                'bg-blue-50 text-blue-600 ring-blue-100',

            precio:
                'text-blue-600',

            check:
                'border-blue-200 bg-blue-50 text-blue-600',

            boton:
                'border-blue-200 text-blue-600 hover:border-blue-300 hover:bg-blue-50',

            seleccionado:
                'border-blue-500 shadow-blue-200/70',

            insignia:
                'bg-blue-600',
        }
    }

    if (tipo === 'pro') {
        return {
            icono:
                'bg-cyan-50 text-cyan-600 ring-cyan-100',

            precio:
                'text-cyan-600',

            check:
                'border-cyan-200 bg-cyan-50 text-cyan-600',

            boton:
                'border-cyan-200 text-cyan-700 hover:border-cyan-300 hover:bg-cyan-50',

            seleccionado:
                'border-cyan-500 shadow-cyan-200/70',

            insignia:
                'bg-cyan-600',
        }
    }

    return {
        icono:
            'bg-violet-50 text-violet-600 ring-violet-100',

        precio:
            'text-violet-600',

        check:
            'border-violet-200 bg-violet-50 text-violet-600',

        boton:
            'border-violet-200 text-violet-600 hover:border-violet-300 hover:bg-violet-50',

        seleccionado:
            'border-violet-500 shadow-violet-200/70',

        insignia:
            'bg-violet-600',
    }
}


function numeroONull(
    valor: string,
): number | null {
    const limpio =
        valor.trim()

    if (!limpio) {
        return null
    }

    return Number(limpio)
}


function textoLimite(
    valor: number | null,
    limitado: (cantidad: number) => string,
    ilimitado: string,
): string {
    if (valor === null) {
        return ilimitado
    }

    return limitado(valor)
}


function funcionActiva(
    features: Record<string, unknown>,
    claves: string[],
): boolean {
    return claves.some(
        (clave) =>
            features[clave] === true,
    )
}


function obtenerCaracteristicas(
    plan: PlanSuscripcion,
): string[] {
    const resultado: string[] = [
        textoLimite(
            plan.max_users,
            (cantidad) =>
                `Hasta ${cantidad} usuarios`,
            'Usuarios ilimitados',
        ),

        textoLimite(
            plan.max_branches,
            (cantidad) =>
                `Hasta ${cantidad} sucursales`,
            'Sucursales ilimitadas',
        ),

        textoLimite(
            plan.max_practitioners,
            (cantidad) =>
                `Hasta ${cantidad} profesionales`,
            'Profesionales ilimitados',
        ),

        textoLimite(
            plan.max_appointments_month,
            (cantidad) =>
                `Hasta ${cantidad} citas al mes`,
            'Citas mensuales ilimitadas',
        ),

        textoLimite(
            plan.max_ai_queries_month,
            (cantidad) =>
                `Hasta ${cantidad} consultas IA al mes`,
            'Consultas IA ilimitadas',
        ),

        textoLimite(
            plan.storage_mb,
            (cantidad) =>
                `${cantidad} MB de almacenamiento`,
            'Almacenamiento ilimitado',
        ),
    ]

    const features =
        plan.features ?? {}

    if (
        funcionActiva(
            features,
            [
                'ai_chatbot',
                'chatbot',
            ],
        )
    ) {
        resultado.push('Chatbot')
    }

    if (
        funcionActiva(
            features,
            [
                'noshow_prediction',
                'no_show_prediction',
            ],
        )
    ) {
        resultado.push(
            'Predicción de inasistencia',
        )
    }

    if (
        funcionActiva(
            features,
            [
                'ai_summaries',
                'ai_summary',
            ],
        )
    ) {
        resultado.push(
            'Resúmenes por IA',
        )
    }

    if (
        funcionActiva(
            features,
            [
                'report_export',
                'reports_export',
            ],
        )
    ) {
        resultado.push(
            'Exportación de reportes',
        )
    }

    if (
        funcionActiva(
            features,
            [
                'online_payment',
                'online_payments',
            ],
        )
    ) {
        resultado.push(
            'Pago en línea',
        )
    }

    return resultado
}


function monedaVisual(
    moneda: string,
): string {
    if (moneda === 'BOB') {
        return 'Bs'
    }

    return moneda
}


function descripcionError(
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


export function Planes() {
    useTitulo(
        'Planes de suscripción',
    )

    const [
        planes,
        setPlanes,
    ] =
        useState<PlanSuscripcion[]>([])

    const [
        seleccionado,
        setSeleccionado,
    ] =
        useState<string | null>(null)

    const [
        filtro,
        setFiltro,
    ] =
        useState<FiltroPlanes>(
            'todos',
        )

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

    const [
        modalAbierto,
        setModalAbierto,
    ] =
        useState(false)

    const [
        modoModal,
        setModoModal,
    ] =
        useState<
            'crear' | 'editar'
        >('crear')

    const [
        planEditando,
        setPlanEditando,
    ] =
        useState<PlanSuscripcion | null>(
            null,
        )


    const cargarPlanes =
        async () => {
            setCargando(true)
            setError(null)

            try {
                const respuesta =
                    await listarPlanes()

                setPlanes(
                    respuesta.results,
                )

                setSeleccionado(
                    (actual) => {
                        if (
                            actual
                            && respuesta.results.some(
                                (plan) =>
                                    plan.id === actual,
                            )
                        ) {
                            return actual
                        }

                        const pro =
                            respuesta.results.find(
                                (plan) =>
                                    tipoVisual(
                                        plan.code,
                                    ) === 'pro',
                            )

                        return (
                            pro?.id
                            ?? respuesta.results[0]
                                ?.id
                            ?? null
                        )
                    },
                )
            } catch (err) {
                setError(
                    descripcionError(err),
                )
            } finally {
                setCargando(false)
            }
        }


    useEffect(() => {
        void cargarPlanes()
    }, [])


    const planesActivos =
        useMemo(
            () =>
                planes.filter(
                    (plan) =>
                        plan.is_active,
                ).length,
            [planes],
        )


    const planesInactivos =
        useMemo(
            () =>
                planes.filter(
                    (plan) =>
                        !plan.is_active,
                ).length,
            [planes],
        )


    const planesVisibles =
        useMemo(() => {
            if (
                filtro === 'activos'
            ) {
                return planes.filter(
                    (plan) =>
                        plan.is_active,
                )
            }

            if (
                filtro === 'inactivos'
            ) {
                return planes.filter(
                    (plan) =>
                        !plan.is_active,
                )
            }

            return planes
        }, [
            filtro,
            planes,
        ])


    function abrirNuevoPlan() {
        setPlanEditando(null)
        setModoModal('crear')
        setModalAbierto(true)
    }


    function abrirEditarPlan(
        plan: PlanSuscripcion,
    ) {
        setPlanEditando(plan)
        setSeleccionado(plan.id)
        setModoModal('editar')
        setModalAbierto(true)
    }


    function cerrarModal() {
        if (guardando) {
            return
        }

        setModalAbierto(false)
        setPlanEditando(null)
    }


    async function guardarPlan(
        formulario:
        DatosFormularioPlan,
    ) {
        setGuardando(true)
        setError(null)

        const datos: DatosPlan = {
            code:
                formulario.code.trim(),

            name:
                formulario.name.trim(),

            description:
                formulario.description.trim(),

            monthly_price:
            formulario.price,

            currency:
            formulario.currency,

            max_users:
                numeroONull(
                    formulario.maxUsers,
                ),

            max_branches:
                numeroONull(
                    formulario.maxBranches,
                ),

            max_practitioners:
                numeroONull(
                    formulario.maxPractitioners,
                ),

            max_appointments_month:
                numeroONull(
                    formulario.maxAppointmentsMonth,
                ),

            max_ai_queries_month:
                numeroONull(
                    formulario.maxAiQueriesMonth,
                ),

            storage_mb:
                numeroONull(
                    formulario.storageMb,
                ),

            features: {
                ai_chatbot:
                formulario.chatbot,

                noshow_prediction:
                formulario.noShowPrediction,

                ai_summaries:
                formulario.aiSummaries,

                report_export:
                formulario.reportExport,

                online_payment:
                formulario.onlinePayment,
            },

            is_active:
            formulario.active,
        }

        try {
            if (
                modoModal === 'editar'
                && planEditando
            ) {
                const actualizado =
                    await actualizarPlan(
                        planEditando.id,
                        datos,
                    )

                setPlanes(
                    (actuales) =>
                        actuales.map(
                            (plan) =>
                                plan.id
                                === actualizado.id
                                    ? actualizado
                                    : plan,
                        ),
                )

                setSeleccionado(
                    actualizado.id,
                )
            } else {
                const nuevo =
                    await crearPlan(datos)

                setPlanes(
                    (actuales) => [
                        ...actuales,
                        nuevo,
                    ],
                )

                setSeleccionado(
                    nuevo.id,
                )
            }

            setModalAbierto(false)
            setPlanEditando(null)
        } catch (err) {
            setError(
                descripcionError(err),
            )
        } finally {
            setGuardando(false)
        }
    }


    const datosIniciales:
        DatosFormularioPlan | null =
        planEditando
            ? {
                id:
                planEditando.id,

                name:
                planEditando.name,

                code:
                planEditando.code,

                description:
                    planEditando.description
                    ?? '',

                price:
                planEditando
                    .monthly_price,

                currency:
                planEditando.currency,

                maxUsers:
                    planEditando
                        .max_users !== null
                        ? String(
                            planEditando
                                .max_users,
                        )
                        : '',

                maxBranches:
                    planEditando
                        .max_branches !== null
                        ? String(
                            planEditando
                                .max_branches,
                        )
                        : '',

                maxPractitioners:
                    planEditando
                        .max_practitioners
                    !== null
                        ? String(
                            planEditando
                                .max_practitioners,
                        )
                        : '',

                maxAppointmentsMonth:
                    planEditando
                        .max_appointments_month
                    !== null
                        ? String(
                            planEditando
                                .max_appointments_month,
                        )
                        : '',

                maxAiQueriesMonth:
                    planEditando
                        .max_ai_queries_month
                    !== null
                        ? String(
                            planEditando
                                .max_ai_queries_month,
                        )
                        : '',

                storageMb:
                    planEditando
                        .storage_mb !== null
                        ? String(
                            planEditando
                                .storage_mb,
                        )
                        : '',

                chatbot:
                    funcionActiva(
                        planEditando.features,
                        [
                            'ai_chatbot',
                            'chatbot',
                        ],
                    ),

                noShowPrediction:
                    funcionActiva(
                        planEditando.features,
                        [
                            'noshow_prediction',
                            'no_show_prediction',
                        ],
                    ),

                aiSummaries:
                    funcionActiva(
                        planEditando.features,
                        [
                            'ai_summaries',
                            'ai_summary',
                        ],
                    ),

                reportExport:
                    funcionActiva(
                        planEditando.features,
                        [
                            'report_export',
                            'reports_export',
                        ],
                    ),

                onlinePayment:
                    funcionActiva(
                        planEditando.features,
                        [
                            'online_payment',
                            'online_payments',
                        ],
                    ),

                active:
                planEditando
                    .is_active,
            }
            : null


    return (
        <>
            <div className="mx-auto w-full max-w-[1500px] px-8 py-8 xl:px-10">

                <header className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">

                    <div>

                        <div className="mb-2 flex items-center gap-2">
              <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-600">
                Administración
              </span>
                        </div>

                        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
                            Planes de suscripción
                        </h1>

                        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                            Configura los planes disponibles
                            para las organizaciones y controla
                            sus límites y funcionalidades.
                        </p>

                    </div>


                    <button
                        type="button"
                        onClick={
                            abrirNuevoPlan
                        }
                        className="flex h-11 items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 text-sm font-semibold text-white shadow-sm shadow-blue-200 transition hover:bg-blue-700"
                    >
                        <IconoMas />

                        Nuevo plan
                    </button>

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


                <div className="mb-7 grid grid-cols-1 gap-4 sm:grid-cols-3">

                    <TarjetaResumen
                        titulo="Planes disponibles"
                        valor={String(
                            planes.length,
                        )}
                    />

                    <TarjetaResumen
                        titulo="Planes activos"
                        valor={String(
                            planesActivos,
                        )}
                        valorClase="text-emerald-600"
                    />

                    <TarjetaResumen
                        titulo="Planes inactivos"
                        valor={String(
                            planesInactivos,
                        )}
                        valorClase="text-slate-500"
                    />

                </div>


                <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">

                    <div>
                        <p className="text-sm font-semibold text-slate-700">
                            Filtrar planes
                        </p>

                        <p className="mt-1 text-xs text-slate-400">
                            Consulta todos los planes o filtra por su estado.
                        </p>
                    </div>


                    <div className="inline-flex w-fit rounded-xl border border-slate-200 bg-white p-1 shadow-sm">

                        <BotonFiltro
                            activo={
                                filtro === 'todos'
                            }
                            onClick={() =>
                                setFiltro('todos')
                            }
                        >
                            Todos ({planes.length})
                        </BotonFiltro>

                        <BotonFiltro
                            activo={
                                filtro === 'activos'
                            }
                            onClick={() =>
                                setFiltro('activos')
                            }
                        >
                            Activos ({planesActivos})
                        </BotonFiltro>

                        <BotonFiltro
                            activo={
                                filtro === 'inactivos'
                            }
                            onClick={() =>
                                setFiltro('inactivos')
                            }
                        >
                            Inactivos ({planesInactivos})
                        </BotonFiltro>

                    </div>

                </div>


                {cargando ? (
                    <EstadoCargando />
                ) : planes.length === 0 ? (
                    <EstadoVacio
                        onCrear={
                            abrirNuevoPlan
                        }
                    />
                ) : planesVisibles.length === 0 ? (
                    <EstadoFiltroVacio
                        filtro={filtro}
                        onMostrarTodos={() =>
                            setFiltro('todos')
                        }
                    />
                ) : (
                    <section className="grid grid-cols-1 gap-7 xl:grid-cols-3">

                        {planesVisibles.map(
                            (plan) => {
                                const tipo =
                                    tipoVisual(
                                        plan.code,
                                    )

                                const tema =
                                    temaPlan(tipo)

                                const esSeleccionado =
                                    seleccionado
                                    === plan.id

                                const caracteristicas =
                                    obtenerCaracteristicas(
                                        plan,
                                    )

                                return (
                                    <article
                                        key={plan.id}
                                        onClick={() =>
                                            setSeleccionado(
                                                plan.id,
                                            )
                                        }
                                        className={[
                                            'relative flex min-h-[500px] cursor-pointer flex-col rounded-3xl bg-white p-6 transition-all duration-300 ease-out',

                                            esSeleccionado
                                                ? `z-10 -translate-y-3 scale-[1.025] border-2 shadow-2xl ${tema.seleccionado}`
                                                : 'border border-slate-200 shadow-sm hover:-translate-y-1.5 hover:shadow-lg',

                                            !plan.is_active
                                                ? 'opacity-90'
                                                : '',
                                        ].join(' ')}
                                    >

                                        {esSeleccionado ? (
                                            <div className="absolute -top-3 left-1/2 -translate-x-1/2">

                                                <div
                                                    className={[
                                                        'flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-semibold text-white shadow-lg',
                                                        tema.insignia,
                                                    ].join(' ')}
                                                >
                                                    <IconoCheck />

                                                    Seleccionado
                                                </div>

                                            </div>
                                        ) : (
                                            tipo === 'pro'
                                            && plan.is_active
                                            && (
                                                <div className="absolute -top-3 left-1/2 -translate-x-1/2">

                                                    <div className="rounded-full bg-cyan-600 px-3 py-1 text-xs font-semibold text-white shadow-sm">
                                                        Recomendado
                                                    </div>

                                                </div>
                                            )
                                        )}


                                        <div className="mb-6 flex items-start justify-between">

                                            <div
                                                className={[
                                                    'flex h-12 w-12 items-center justify-center rounded-2xl ring-1 transition-transform duration-300',
                                                    tema.icono,

                                                    esSeleccionado
                                                        ? 'scale-110'
                                                        : '',
                                                ].join(' ')}
                                            >
                                                <IconoPlan
                                                    tipo={tipo}
                                                />
                                            </div>


                                            {plan.is_active ? (
                                                <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-[11px] font-bold tracking-wide text-emerald-600">
                          ACTIVO
                        </span>
                                            ) : (
                                                <span className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-[11px] font-bold tracking-wide text-slate-500">
                          INACTIVO
                        </span>
                                            )}

                                        </div>


                                        <div className="mb-5">

                                            <h2 className="text-2xl font-bold text-slate-900">
                                                {plan.name}
                                            </h2>

                                            {plan.description && (
                                                <p className="mt-1 text-sm leading-6 text-slate-500">
                                                    {
                                                        plan.description
                                                    }
                                                </p>
                                            )}

                                            <div className="mt-3 flex items-end gap-1">

                        <span
                            className={`text-4xl font-bold ${tema.precio}`}
                        >
                          {monedaVisual(
                              plan.currency,
                          )}{' '}

                            {
                                plan.monthly_price
                            }
                        </span>

                                                <span className="pb-1 text-sm font-medium text-slate-400">
                          / mes
                        </span>

                                            </div>

                                        </div>


                                        <div className="mb-5 h-px bg-slate-100" />


                                        <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-400">
                                            Incluye
                                        </p>


                                        <div className="flex flex-1 flex-col gap-3">

                                            {caracteristicas.map(
                                                (
                                                    caracteristica,
                                                ) => (
                                                    <div
                                                        key={
                                                            caracteristica
                                                        }
                                                        className="flex items-start gap-3"
                                                    >

                                                        <div
                                                            className={[
                                                                'mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border',
                                                                tema.check,
                                                            ].join(' ')}
                                                        >
                                                            <IconoCheck />
                                                        </div>

                                                        <p className="text-sm leading-5 text-slate-600">
                                                            {
                                                                caracteristica
                                                            }
                                                        </p>

                                                    </div>
                                                ),
                                            )}

                                        </div>


                                        <button
                                            type="button"
                                            onClick={(
                                                evento,
                                            ) => {
                                                evento.stopPropagation()

                                                abrirEditarPlan(
                                                    plan,
                                                )
                                            }}
                                            className={[
                                                'mt-7 flex h-11 w-full items-center justify-center gap-2 rounded-xl border text-sm font-semibold transition-all duration-200',
                                                tema.boton,

                                                esSeleccionado
                                                    ? 'shadow-sm'
                                                    : '',
                                            ].join(' ')}
                                        >
                                            <IconoLapiz />

                                            Editar plan
                                        </button>

                                    </article>
                                )
                            },
                        )}

                    </section>
                )}

            </div>


            <ModalPlan
                abierto={
                    modalAbierto
                }

                modo={
                    modoModal
                }

                inicial={
                    datosIniciales
                }

                guardando={
                    guardando
                }

                onCerrar={
                    cerrarModal
                }

                onGuardar={
                    guardarPlan
                }
            />

        </>
    )
}


function BotonFiltro({
                         activo,
                         onClick,
                         children,
                     }: {
    activo: boolean
    onClick: () => void
    children: React.ReactNode
}) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={[
                'rounded-lg px-4 py-2 text-sm font-semibold transition',

                activo
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-500 hover:bg-slate-50 hover:text-slate-800',
            ].join(' ')}
        >
            {children}
        </button>
    )
}


function TarjetaResumen({
                            titulo,
                            valor,
                            valorClase = 'text-slate-900',
                        }: {
    titulo: string
    valor: string
    valorClase?: string
}) {
    return (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">

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


function EstadoCargando() {
    return (
        <div className="grid grid-cols-1 gap-7 xl:grid-cols-3">

            {[1, 2, 3].map(
                (item) => (
                    <div
                        key={item}
                        className="h-[500px] animate-pulse rounded-3xl border border-slate-200 bg-white p-6"
                    >
                        <div className="h-12 w-12 rounded-2xl bg-slate-100" />

                        <div className="mt-7 h-7 w-32 rounded-lg bg-slate-100" />

                        <div className="mt-4 h-10 w-44 rounded-lg bg-slate-100" />

                        <div className="mt-8 space-y-4">
                            <div className="h-5 rounded bg-slate-100" />
                            <div className="h-5 rounded bg-slate-100" />
                            <div className="h-5 rounded bg-slate-100" />
                        </div>
                    </div>
                ),
            )}

        </div>
    )
}


function EstadoVacio({
                         onCrear,
                     }: {
    onCrear: () => void
}) {
    return (
        <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center">

            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
                <IconoPlan
                    tipo="basic"
                />
            </div>

            <h2 className="mt-5 text-xl font-bold text-slate-900">
                No hay planes registrados
            </h2>

            <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
                Crea el primer plan de
                suscripción disponible para
                las organizaciones.
            </p>

            <button
                type="button"
                onClick={onCrear}
                className="mt-6 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
            >
                Crear plan
            </button>

        </div>
    )
}


function EstadoFiltroVacio({
                               filtro,
                               onMostrarTodos,
                           }: {
    filtro: FiltroPlanes
    onMostrarTodos: () => void
}) {
    return (
        <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">

            <h2 className="text-lg font-bold text-slate-900">
                No hay planes {
                filtro === 'activos'
                    ? 'activos'
                    : 'inactivos'
            }
            </h2>

            <p className="mt-2 text-sm text-slate-500">
                Cambia el filtro para consultar
                los demás planes registrados.
            </p>

            <button
                type="button"
                onClick={onMostrarTodos}
                className="mt-5 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
            >
                Mostrar todos
            </button>

        </div>
    )
}


function IconoMas() {
    return (
        <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="h-[18px] w-[18px]"
            aria-hidden="true"
        >
            <path d="M12 5v14M5 12h14" />
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
            className="h-3 w-3"
            aria-hidden="true"
        >
            <path d="m5 12 4 4L19 6" />
        </svg>
    )
}


function IconoLapiz() {
    return (
        <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="h-4 w-4"
            aria-hidden="true"
        >
            <path d="M12 20h9" />

            <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z" />
        </svg>
    )
}


function IconoPlan({
                       tipo,
                   }: {
    tipo: TipoVisualPlan
}) {
    if (tipo === 'basic') {
        return (
            <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.9"
                className="h-6 w-6"
                aria-hidden="true"
            >
                <path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9Z" />
            </svg>
        )
    }

    if (
        tipo === 'premium'
    ) {
        return (
            <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.9"
                className="h-6 w-6"
                aria-hidden="true"
            >
                <path d="m4 9 4-5 4 5 4-5 4 5-8 11Z" />

                <path d="M4 9h16" />
            </svg>
        )
    }

    return (
        <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.9"
            className="h-6 w-6"
            aria-hidden="true"
        >
            <path d="M4 7 8 4l4 5 4-5 4 3-2 11H6Z" />

            <path d="M7 18h10" />
        </svg>
    )
}