import { useEffect, useState, type FormEvent } from 'react'

import type { PlanSuscripcion } from '@/api/suscripciones'


export type DatosCambioPlan = {
    planId: string
    startsAt: string
    reason: string
}


type Props = {
    abierto: boolean
    organizacion: string
    planActualId: string
    planes: PlanSuscripcion[]
    guardando?: boolean
    onCerrar: () => void
    onConfirmar:
        (datos: DatosCambioPlan) =>
            void | Promise<void>
}


function hoy(): string {
    const fecha =
        new Date()

    const anio =
        fecha.getFullYear()

    const mes =
        String(
            fecha.getMonth() + 1,
        ).padStart(
            2,
            '0',
        )

    const dia =
        String(
            fecha.getDate(),
        ).padStart(
            2,
            '0',
        )

    return `${anio}-${mes}-${dia}`
}


export function ModalCambiarPlan({
                                     abierto,
                                     organizacion,
                                     planActualId,
                                     planes,
                                     guardando = false,
                                     onCerrar,
                                     onConfirmar,
                                 }: Props) {
    const [
        planId,
        setPlanId,
    ] =
        useState('')

    const [
        fechaInicio,
        setFechaInicio,
    ] =
        useState(
            hoy(),
        )

    const [
        motivo,
        setMotivo,
    ] =
        useState('')


    useEffect(() => {
        if (!abierto) {
            return
        }

        const alternativa =
            planes.find(
                (plan) =>
                    plan.id
                    !== planActualId
                    && plan.is_active,
            )

        setPlanId(
            alternativa?.id
            ?? '',
        )

        setFechaInicio(
            hoy(),
        )

        setMotivo('')
    }, [
        abierto,
        planActualId,
        planes,
    ])


    if (!abierto) {
        return null
    }


    const enviar =
        async (
            evento: FormEvent,
        ) => {
            evento.preventDefault()

            if (
                !planId
                || !fechaInicio
            ) {
                return
            }

            await onConfirmar({
                planId,
                startsAt:
                fechaInicio,
                reason:
                    motivo.trim(),
            })
        }


    const planSeleccionado =
        planes.find(
            (plan) =>
                plan.id === planId,
        )


    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
            onMouseDown={
                onCerrar
            }
        >

            <div
                className="flex max-h-[calc(100dvh-2rem)] w-full max-w-xl flex-col overflow-hidden rounded-3xl border border-tinta-800 bg-tinta-900 shadow-2xl"
                onMouseDown={(
                    evento,
                ) =>
                    evento.stopPropagation()
                }
            >

                {/* Cabecera */}

                <header className="flex shrink-0 items-start justify-between border-b border-tinta-800 px-6 py-5">

                    <div>

                        <p className="text-xs font-semibold uppercase tracking-wider text-marca-400">
                            Suscripción
                        </p>

                        <h2 className="mt-1 text-xl font-bold text-tinta-50">
                            Cambiar plan
                        </h2>

                        <p className="mt-1 text-sm text-tinta-500">
                            Asigna un nuevo plan de suscripción
                            a la organización.
                        </p>

                    </div>


                    <button
                        type="button"
                        onClick={
                            onCerrar
                        }
                        disabled={
                            guardando
                        }
                        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-xl text-tinta-500 transition hover:bg-tinta-800 hover:text-tinta-100 disabled:opacity-50"
                        aria-label="Cerrar"
                    >
                        ×
                    </button>

                </header>


                <form
                    onSubmit={
                        enviar
                    }
                    className="flex min-h-0 flex-1 flex-col"
                >

                    {/* Contenido desplazable */}

                    <div className="min-h-0 flex-1 space-y-6 overflow-y-auto p-6">

                        {/* Organización */}

                        <div className="rounded-2xl border border-tinta-800 bg-tinta-950 p-4">

                            <div className="flex items-center gap-3">

                                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-marca-950 text-marca-400">

                                    <IconoEdificio />

                                </div>


                                <div>

                                    <p className="text-xs font-semibold uppercase tracking-wider text-tinta-500">
                                        Organización
                                    </p>

                                    <p className="mt-1 text-base font-bold text-tinta-50">
                                        {organizacion}
                                    </p>

                                </div>

                            </div>

                        </div>


                        {/* Nuevo plan */}

                        <div>

                            <label className="mb-2 block text-sm font-semibold text-tinta-300">
                                Nuevo plan
                            </label>

                            <select
                                value={
                                    planId
                                }
                                onChange={(
                                    evento,
                                ) =>
                                    setPlanId(
                                        evento.target.value,
                                    )
                                }
                                className="h-11 w-full rounded-xl border border-tinta-800 bg-tinta-950 px-4 text-sm text-tinta-100 outline-none transition focus:border-marca-600 focus:ring-2 focus:ring-marca-600/20"
                            >

                                <option value="">
                                    Selecciona un plan
                                </option>


                                {planes
                                    .filter(
                                        (plan) =>
                                            plan.is_active
                                            && plan.id
                                            !== planActualId,
                                    )
                                    .map(
                                        (plan) => (
                                            <option
                                                key={
                                                    plan.id
                                                }
                                                value={
                                                    plan.id
                                                }
                                            >
                                                {plan.name}
                                            </option>
                                        ),
                                    )}

                            </select>


                            {planSeleccionado && (
                                <div className="mt-3 rounded-xl border border-marca-900 bg-marca-950/40 px-4 py-3">

                                    <div className="flex flex-wrap items-center justify-between gap-3">

                                        <div>

                                            <p className="text-xs text-tinta-500">
                                                Plan seleccionado
                                            </p>

                                            <p className="mt-1 font-semibold text-marca-300">
                                                {
                                                    planSeleccionado.name
                                                }
                                            </p>

                                        </div>


                                        <div className="text-right">

                                            <p className="text-xs text-tinta-500">
                                                Precio mensual
                                            </p>

                                            <p className="mt-1 font-bold text-tinta-100">
                                                {planSeleccionado.currency === 'BOB'
                                                    ? 'Bs'
                                                    : planSeleccionado.currency}{' '}
                                                {
                                                    planSeleccionado.monthly_price
                                                }
                                            </p>

                                        </div>

                                    </div>

                                </div>
                            )}

                        </div>


                        {/* Fecha */}

                        <div>

                            <label className="mb-2 block text-sm font-semibold text-tinta-300">
                                Fecha de inicio
                            </label>

                            <input
                                type="date"
                                value={
                                    fechaInicio
                                }
                                onChange={(
                                    evento,
                                ) =>
                                    setFechaInicio(
                                        evento.target.value,
                                    )
                                }
                                className="h-11 w-full rounded-xl border border-tinta-800 bg-tinta-950 px-4 text-sm text-tinta-100 outline-none transition [color-scheme:dark] focus:border-marca-600 focus:ring-2 focus:ring-marca-600/20"
                            />

                            <p className="mt-1.5 text-xs text-tinta-500">
                                El backend verificará que la fecha
                                sea válida respecto a la suscripción actual.
                            </p>

                        </div>


                        {/* Motivo */}

                        <div>

                            <label className="mb-2 block text-sm font-semibold text-tinta-300">
                                Motivo del cambio
                            </label>

                            <textarea
                                value={
                                    motivo
                                }
                                onChange={(
                                    evento,
                                ) =>
                                    setMotivo(
                                        evento.target.value,
                                    )
                                }
                                placeholder="Ej. Actualización solicitada por la organización"
                                rows={4}
                                maxLength={200}
                                className="w-full resize-none rounded-xl border border-tinta-800 bg-tinta-950 px-4 py-3 text-sm text-tinta-100 placeholder:text-tinta-600 outline-none transition focus:border-marca-600 focus:ring-2 focus:ring-marca-600/20"
                            />


                            <div className="mt-1.5 flex justify-between gap-3">

                                <p className="text-xs text-tinta-500">
                                    Este motivo quedará registrado
                                    en el historial.
                                </p>

                                <p className="text-xs text-tinta-600">
                                    {motivo.length}/200
                                </p>

                            </div>

                        </div>


                        {/* Aviso */}

                        <div className="rounded-2xl border border-amber-900/70 bg-amber-950/30 px-4 py-3">

                            <div className="flex gap-3">

                                <div className="mt-0.5 text-amber-400">

                                    <IconoInformacion />

                                </div>

                                <p className="text-xs leading-5 text-amber-300/90">
                                    Al confirmar, la suscripción vigente
                                    se cerrará y se abrirá la nueva.
                                    La organización conservará su historial
                                    completo de cambios.
                                </p>

                            </div>

                        </div>

                    </div>


                    {/* Botones siempre visibles */}

                    <footer className="shrink-0 border-t border-tinta-800 bg-tinta-900 px-6 py-4">

                        <div className="flex items-center justify-end gap-3">

                            <button
                                type="button"
                                onClick={
                                    onCerrar
                                }
                                disabled={
                                    guardando
                                }
                                className="h-11 rounded-xl border border-tinta-700 px-5 text-sm font-semibold text-tinta-300 transition hover:bg-tinta-800 disabled:opacity-50"
                            >
                                Cancelar
                            </button>


                            <button
                                type="submit"
                                disabled={
                                    guardando
                                    || !planId
                                    || !fechaInicio
                                }
                                className="h-11 rounded-xl bg-marca-600 px-5 text-sm font-semibold text-white transition hover:bg-marca-700 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                                {guardando
                                    ? 'Cambiando...'
                                    : 'Confirmar cambio'}
                            </button>

                        </div>

                    </footer>

                </form>

            </div>

        </div>
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


function IconoInformacion() {
    return (
        <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="h-4 w-4"
            aria-hidden="true"
        >
            <circle
                cx="12"
                cy="12"
                r="9"
            />

            <path d="M12 11v5" />

            <path d="M12 8h.01" />
        </svg>
    )
}