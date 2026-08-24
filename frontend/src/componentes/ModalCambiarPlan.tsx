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
    onConfirmar: (datos: DatosCambioPlan) => void | Promise<void>
}

function hoy(): string {
    const fecha = new Date()

    const anio = fecha.getFullYear()
    const mes = String(fecha.getMonth() + 1).padStart(2, '0')
    const dia = String(fecha.getDate()).padStart(2, '0')

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
    const [planId, setPlanId] = useState('')
    const [fechaInicio, setFechaInicio] = useState(hoy())
    const [motivo, setMotivo] = useState('')

    useEffect(() => {
        if (!abierto) return

        const alternativa = planes.find(
            (plan) =>
                plan.id !== planActualId
                && plan.is_active,
        )

        setPlanId(alternativa?.id ?? '')
        setFechaInicio(hoy())
        setMotivo('')
    }, [
        abierto,
        planActualId,
        planes,
    ])

    if (!abierto) return null

    const enviar = async (evento: FormEvent) => {
        evento.preventDefault()

        if (!planId || !fechaInicio) return

        await onConfirmar({
            planId,
            startsAt: fechaInicio,
            reason: motivo.trim(),
        })
    }

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4 backdrop-blur-[2px]"
            onMouseDown={onCerrar}
        >
            <div
                className="w-full max-w-xl overflow-hidden rounded-3xl bg-white shadow-2xl"
                onMouseDown={(evento) => evento.stopPropagation()}
            >
                <header className="flex items-start justify-between border-b border-slate-200 px-6 py-5">
                    <div>
                        <h2 className="text-xl font-bold text-slate-900">
                            Cambiar plan
                        </h2>

                        <p className="mt-1 text-sm text-slate-500">
                            Asigna un nuevo plan de suscripción a la organización.
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={onCerrar}
                        disabled={guardando}
                        className="flex h-10 w-10 items-center justify-center rounded-xl text-xl text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 disabled:opacity-50"
                        aria-label="Cerrar"
                    >
                        ×
                    </button>
                </header>

                <form
                    onSubmit={enviar}
                    className="space-y-6 p-6"
                >
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                            Organización
                        </p>

                        <p className="mt-1 text-base font-bold text-slate-900">
                            {organizacion}
                        </p>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-semibold text-slate-700">
                            Nuevo plan
                        </label>

                        <select
                            value={planId}
                            onChange={(evento) =>
                                setPlanId(evento.target.value)
                            }
                            className="h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                        >
                            <option value="">
                                Selecciona un plan
                            </option>

                            {planes
                                .filter(
                                    (plan) =>
                                        plan.is_active
                                        && plan.id !== planActualId,
                                )
                                .map((plan) => (
                                    <option
                                        key={plan.id}
                                        value={plan.id}
                                    >
                                        {plan.name}
                                    </option>
                                ))}
                        </select>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-semibold text-slate-700">
                            Fecha de inicio
                        </label>

                        <input
                            type="date"
                            value={fechaInicio}
                            onChange={(evento) =>
                                setFechaInicio(evento.target.value)
                            }
                            className="h-11 w-full rounded-xl border border-slate-200 px-4 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                        />
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-semibold text-slate-700">
                            Motivo del cambio
                        </label>

                        <textarea
                            value={motivo}
                            onChange={(evento) =>
                                setMotivo(evento.target.value)
                            }
                            placeholder="Ej. Actualización solicitada por la organización"
                            rows={4}
                            className="w-full resize-none rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                        />
                    </div>

                    <footer className="flex items-center justify-end gap-3 border-t border-slate-200 pt-5">
                        <button
                            type="button"
                            onClick={onCerrar}
                            disabled={guardando}
                            className="h-11 rounded-xl border border-slate-200 px-5 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
                        >
                            Cancelar
                        </button>

                        <button
                            type="submit"
                            disabled={
                                guardando
                                || !planId
                            }
                            className="h-11 rounded-xl bg-blue-600 px-5 text-sm font-semibold text-white shadow-sm shadow-blue-200 transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {guardando
                                ? 'Cambiando...'
                                : 'Confirmar cambio'}
                        </button>
                    </footer>
                </form>
            </div>
        </div>
    )
}