import { useEffect, useState, type FormEvent } from 'react'

export type DatosFormularioPlan = {
    id?: string
    name: string
    code: string
    description: string
    price: string
    currency: string

    maxUsers: string
    maxBranches: string
    maxPractitioners: string
    maxAppointmentsMonth: string
    maxAiQueriesMonth: string
    storageMb: string

    chatbot: boolean
    noShowPrediction: boolean
    aiSummaries: boolean
    reportExport: boolean
    onlinePayment: boolean

    active: boolean
}

type Props = {
    abierto: boolean
    modo: 'crear' | 'editar'
    inicial?: DatosFormularioPlan | null
    guardando?: boolean
    onCerrar: () => void
    onGuardar: (
        datos: DatosFormularioPlan,
    ) => void | Promise<void>
}

const vacio: DatosFormularioPlan = {
    name: '',
    code: '',
    description: '',
    price: '',
    currency: 'BOB',

    maxUsers: '',
    maxBranches: '',
    maxPractitioners: '',
    maxAppointmentsMonth: '',
    maxAiQueriesMonth: '',
    storageMb: '',

    chatbot: false,
    noShowPrediction: false,
    aiSummaries: false,
    reportExport: false,
    onlinePayment: false,

    active: true,
}

export function ModalPlan({
                              abierto,
                              modo,
                              inicial,
                              guardando = false,
                              onCerrar,
                              onGuardar,
                          }: Props) {
    const [formulario, setFormulario] =
        useState<DatosFormularioPlan>(vacio)

    useEffect(() => {
        if (!abierto) {
            return
        }

        if (
            modo === 'editar'
            && inicial
        ) {
            setFormulario(inicial)
            return
        }

        setFormulario(vacio)
    }, [
        abierto,
        modo,
        inicial,
    ])

    if (!abierto) {
        return null
    }

    const cambiar = (
        campo: keyof DatosFormularioPlan,
        valor: string | boolean,
    ) => {
        setFormulario((actual) => ({
            ...actual,
            [campo]: valor,
        }))
    }

    const enviar = async (
        evento: FormEvent,
    ) => {
        evento.preventDefault()

        if (
            !formulario.name.trim()
            || !formulario.code.trim()
            || !formulario.price.trim()
        ) {
            return
        }

        await onGuardar(formulario)
    }

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-950/40 px-4 py-8 backdrop-blur-[2px]"
            onMouseDown={onCerrar}
        >
            <div
                className="my-auto w-full max-w-4xl overflow-hidden rounded-3xl bg-white shadow-2xl"
                onMouseDown={(evento) =>
                    evento.stopPropagation()
                }
            >
                <header className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
                    <div>
                        <h2 className="text-xl font-bold text-slate-900">
                            {modo === 'crear'
                                ? 'Nuevo plan'
                                : 'Editar plan'}
                        </h2>

                        <p className="mt-1 text-sm text-slate-500">
                            {modo === 'crear'
                                ? 'Configura un nuevo plan de suscripción.'
                                : 'Actualiza los límites y funcionalidades del plan.'}
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
                    className="max-h-[calc(100vh-150px)] overflow-y-auto"
                >
                    <div className="space-y-7 p-6">

                        {/* Información general */}

                        <Seccion
                            titulo="Información general"
                            descripcion="Datos principales del plan de suscripción."
                        >
                            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
                                <Campo
                                    etiqueta="Nombre"
                                    valor={formulario.name}
                                    placeholder="Ej. Pro"
                                    requerido
                                    onChange={(valor) =>
                                        cambiar('name', valor)
                                    }
                                />

                                <Campo
                                    etiqueta="Código"
                                    valor={formulario.code}
                                    placeholder="Ej. pro"
                                    requerido
                                    onChange={(valor) =>
                                        cambiar(
                                            'code',
                                            valor.toLowerCase(),
                                        )
                                    }
                                />
                            </div>

                            <div>
                                <label className="mb-2 block text-sm font-semibold text-slate-700">
                                    Descripción
                                </label>

                                <textarea
                                    value={formulario.description}
                                    onChange={(evento) =>
                                        cambiar(
                                            'description',
                                            evento.target.value,
                                        )
                                    }
                                    rows={3}
                                    placeholder="Describe brevemente qué ofrece este plan."
                                    className="w-full resize-none rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-300 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                                />
                            </div>

                            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">

                                <div>
                                    <label className="mb-2 block text-sm font-semibold text-slate-700">
                                        Precio mensual
                                    </label>

                                    <div className="flex">
                                        <input
                                            type="number"
                                            min="0"
                                            step="0.01"
                                            required
                                            value={formulario.price}
                                            onChange={(evento) =>
                                                cambiar(
                                                    'price',
                                                    evento.target.value,
                                                )
                                            }
                                            placeholder="890"
                                            className="h-11 min-w-0 flex-1 rounded-l-xl border border-r-0 border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-300 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                                        />

                                        <div className="flex h-11 items-center rounded-r-xl border border-slate-200 bg-slate-50 px-4 text-sm font-semibold text-slate-600">
                                            {formulario.currency}
                                        </div>
                                    </div>
                                </div>

                                <div>
                                    <label className="mb-2 block text-sm font-semibold text-slate-700">
                                        Estado
                                    </label>

                                    <Interruptor
                                        activo={formulario.active}
                                        titulo={
                                            formulario.active
                                                ? 'Plan activo'
                                                : 'Plan inactivo'
                                        }
                                        descripcion={
                                            formulario.active
                                                ? 'Disponible para nuevas asignaciones.'
                                                : 'No puede asignarse a nuevas organizaciones.'
                                        }
                                        onCambiar={() =>
                                            cambiar(
                                                'active',
                                                !formulario.active,
                                            )
                                        }
                                    />
                                </div>

                            </div>
                        </Seccion>


                        {/* Límites */}

                        <Seccion
                            titulo="Límites del plan"
                            descripcion="Deja un campo vacío para indicar que el recurso es ilimitado."
                        >
                            <div className="rounded-2xl border border-blue-100 bg-blue-50/70 px-4 py-3 text-sm text-blue-700">
                                Los campos sin valor se interpretan como
                                <strong> ilimitados</strong>.
                            </div>

                            <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">

                                <CampoLimite
                                    etiqueta="Máximo de sucursales"
                                    valor={formulario.maxBranches}
                                    placeholder="Ej. 5"
                                    onChange={(valor) =>
                                        cambiar(
                                            'maxBranches',
                                            valor,
                                        )
                                    }
                                />

                                <CampoLimite
                                    etiqueta="Máximo de usuarios"
                                    valor={formulario.maxUsers}
                                    placeholder="Ej. 60"
                                    onChange={(valor) =>
                                        cambiar(
                                            'maxUsers',
                                            valor,
                                        )
                                    }
                                />

                                <CampoLimite
                                    etiqueta="Máximo de profesionales"
                                    valor={formulario.maxPractitioners}
                                    placeholder="Ej. 40"
                                    onChange={(valor) =>
                                        cambiar(
                                            'maxPractitioners',
                                            valor,
                                        )
                                    }
                                />

                                <CampoLimite
                                    etiqueta="Citas mensuales"
                                    valor={formulario.maxAppointmentsMonth}
                                    placeholder="Ej. 4000"
                                    onChange={(valor) =>
                                        cambiar(
                                            'maxAppointmentsMonth',
                                            valor,
                                        )
                                    }
                                />

                                <CampoLimite
                                    etiqueta="Consultas IA mensuales"
                                    valor={formulario.maxAiQueriesMonth}
                                    placeholder="Ej. 3000"
                                    onChange={(valor) =>
                                        cambiar(
                                            'maxAiQueriesMonth',
                                            valor,
                                        )
                                    }
                                />

                                <CampoLimite
                                    etiqueta="Almacenamiento (MB)"
                                    valor={formulario.storageMb}
                                    placeholder="Ej. 10240"
                                    onChange={(valor) =>
                                        cambiar(
                                            'storageMb',
                                            valor,
                                        )
                                    }
                                />

                            </div>
                        </Seccion>


                        {/* Funcionalidades */}

                        <Seccion
                            titulo="Funcionalidades"
                            descripcion="Activa las características disponibles para las organizaciones que utilicen este plan."
                        >
                            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">

                                <OpcionFuncionalidad
                                    titulo="Chatbot"
                                    descripcion="Asistencia mediante chatbot."
                                    activo={formulario.chatbot}
                                    onCambiar={() =>
                                        cambiar(
                                            'chatbot',
                                            !formulario.chatbot,
                                        )
                                    }
                                />

                                <OpcionFuncionalidad
                                    titulo="Predicción de inasistencia"
                                    descripcion="Predicción de pacientes con riesgo de no asistir."
                                    activo={formulario.noShowPrediction}
                                    onCambiar={() =>
                                        cambiar(
                                            'noShowPrediction',
                                            !formulario.noShowPrediction,
                                        )
                                    }
                                />

                                <OpcionFuncionalidad
                                    titulo="Resúmenes por IA"
                                    descripcion="Generación de resúmenes asistidos por inteligencia artificial."
                                    activo={formulario.aiSummaries}
                                    onCambiar={() =>
                                        cambiar(
                                            'aiSummaries',
                                            !formulario.aiSummaries,
                                        )
                                    }
                                />

                                <OpcionFuncionalidad
                                    titulo="Exportación de reportes"
                                    descripcion="Permite generar y exportar reportes."
                                    activo={formulario.reportExport}
                                    onCambiar={() =>
                                        cambiar(
                                            'reportExport',
                                            !formulario.reportExport,
                                        )
                                    }
                                />

                                <OpcionFuncionalidad
                                    titulo="Pago en línea"
                                    descripcion="Habilita funcionalidades relacionadas con pagos en línea."
                                    activo={formulario.onlinePayment}
                                    onCambiar={() =>
                                        cambiar(
                                            'onlinePayment',
                                            !formulario.onlinePayment,
                                        )
                                    }
                                />

                            </div>
                        </Seccion>

                    </div>


                    <footer className="sticky bottom-0 flex items-center justify-between gap-3 border-t border-slate-200 bg-white px-6 py-4">

                        <p className="hidden text-xs text-slate-400 sm:block">
                            Los cambios se aplicarán al guardar.
                        </p>

                        <div className="ml-auto flex gap-3">

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
                                disabled={guardando}
                                className="h-11 rounded-xl bg-blue-600 px-5 text-sm font-semibold text-white shadow-sm shadow-blue-200 transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                                {guardando
                                    ? 'Guardando...'
                                    : modo === 'crear'
                                        ? 'Crear plan'
                                        : 'Guardar cambios'}
                            </button>

                        </div>

                    </footer>
                </form>
            </div>
        </div>
    )
}


function Seccion({
                     titulo,
                     descripcion,
                     children,
                 }: {
    titulo: string
    descripcion: string
    children: React.ReactNode
}) {
    return (
        <section>
            <div className="mb-4">
                <h3 className="text-base font-bold text-slate-900">
                    {titulo}
                </h3>

                <p className="mt-1 text-sm text-slate-500">
                    {descripcion}
                </p>
            </div>

            <div className="space-y-5">
                {children}
            </div>
        </section>
    )
}


type CampoProps = {
    etiqueta: string
    valor: string
    placeholder?: string
    requerido?: boolean
    onChange: (valor: string) => void
}

function Campo({
                   etiqueta,
                   valor,
                   placeholder,
                   requerido = false,
                   onChange,
               }: CampoProps) {
    return (
        <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700">
                {etiqueta}

                {requerido && (
                    <span className="ml-1 text-red-500">
            *
          </span>
                )}
            </label>

            <input
                type="text"
                required={requerido}
                value={valor}
                onChange={(evento) =>
                    onChange(
                        evento.target.value,
                    )
                }
                placeholder={placeholder}
                className="h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-300 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />
        </div>
    )
}


function CampoLimite({
                         etiqueta,
                         valor,
                         placeholder,
                         onChange,
                     }: {
    etiqueta: string
    valor: string
    placeholder: string
    onChange: (valor: string) => void
}) {
    return (
        <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700">
                {etiqueta}
            </label>

            <input
                type="number"
                min="0"
                step="1"
                value={valor}
                onChange={(evento) =>
                    onChange(
                        evento.target.value,
                    )
                }
                placeholder={placeholder}
                className="h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-300 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />

            <p className="mt-1.5 text-xs text-slate-400">
                Vacío = ilimitado
            </p>
        </div>
    )
}


function Interruptor({
                         activo,
                         titulo,
                         descripcion,
                         onCambiar,
                     }: {
    activo: boolean
    titulo: string
    descripcion?: string
    onCambiar: () => void
}) {
    return (
        <button
            type="button"
            onClick={onCambiar}
            className={[
                'flex min-h-11 w-full items-center justify-between gap-4 rounded-xl border px-4 py-2 text-left transition',

                activo
                    ? 'border-emerald-200 bg-emerald-50'
                    : 'border-slate-200 bg-slate-50',
            ].join(' ')}
        >
            <div>
                <p
                    className={[
                        'text-sm font-semibold',

                        activo
                            ? 'text-emerald-700'
                            : 'text-slate-600',
                    ].join(' ')}
                >
                    {titulo}
                </p>

                {descripcion && (
                    <p className="mt-0.5 text-xs text-slate-400">
                        {descripcion}
                    </p>
                )}
            </div>

            <span
                className={[
                    'relative h-6 w-11 shrink-0 rounded-full transition',

                    activo
                        ? 'bg-emerald-500'
                        : 'bg-slate-300',
                ].join(' ')}
            >
        <span
            className={[
                'absolute top-1 h-4 w-4 rounded-full bg-white shadow-sm transition',

                activo
                    ? 'left-6'
                    : 'left-1',
            ].join(' ')}
        />
      </span>
        </button>
    )
}


function OpcionFuncionalidad({
                                 titulo,
                                 descripcion,
                                 activo,
                                 onCambiar,
                             }: {
    titulo: string
    descripcion: string
    activo: boolean
    onCambiar: () => void
}) {
    return (
        <div
            className={[
                'flex min-h-[92px] items-center justify-between gap-4 rounded-2xl border p-4 transition',

                activo
                    ? 'border-blue-200 bg-blue-50/60'
                    : 'border-slate-200 bg-white',
            ].join(' ')}
        >
            <div>
                <p className="text-sm font-semibold text-slate-800">
                    {titulo}
                </p>

                <p className="mt-1 text-xs leading-5 text-slate-500">
                    {descripcion}
                </p>
            </div>

            <button
                type="button"
                onClick={onCambiar}
                aria-pressed={activo}
                className={[
                    'relative h-6 w-11 shrink-0 rounded-full transition',

                    activo
                        ? 'bg-blue-600'
                        : 'bg-slate-300',
                ].join(' ')}
            >
        <span
            className={[
                'absolute top-1 h-4 w-4 rounded-full bg-white shadow-sm transition',

                activo
                    ? 'left-6'
                    : 'left-1',
            ].join(' ')}
        />
            </button>
        </div>
    )
}