import {
    useState,
    type FormEvent,
} from 'react'

import {
    realizarCheckIn,
    type CheckInResultado,
} from '@/api/fichas'

import { Boton } from '@/componentes/Boton'
import { Campo } from '@/componentes/Campo'
import { useSesion } from '@/sesion/useSesion'


export function CheckIn() {
    const {
        token,
        usuario,
    } = useSesion()

    const contexto = {
        token,
        organizacion:
            usuario?.organization ?? null,
    }

    const [modo, setModo] =
        useState<'documento' | 'qr'>(
            'documento',
        )

    const [documento, setDocumento] =
        useState('')

    const [qr, setQr] =
        useState('')

    const [cargando, setCargando] =
        useState(false)

    const [error, setError] =
        useState('')

    const [resultado, setResultado] =
        useState<CheckInResultado | null>(
            null,
        )


    const enviar =
        async (
            evento: FormEvent,
        ) => {
            evento.preventDefault()

            setError('')
            setResultado(null)

            const valor =
                modo === 'documento'
                    ? documento.trim()
                    : qr.trim()

            if (!valor) {
                setError(
                    modo === 'documento'
                        ? 'Ingresá el número de documento.'
                        : 'Ingresá el código QR.',
                )
                return
            }

            setCargando(true)

            try {
                const respuesta =
                    await realizarCheckIn(
                        modo === 'documento'
                            ? {
                                document_number:
                                valor,
                            }
                            : {
                                qr_code:
                                valor,
                            },
                        contexto,
                    )

                setResultado(
                    respuesta,
                )

                setDocumento('')
                setQr('')
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : 'No se pudo realizar el check-in.',
                )
            } finally {
                setCargando(false)
            }
        }


    return (
        <div className="mx-auto max-w-4xl space-y-7">

            <header>
                <p className="text-sm font-semibold text-marca-400">
                    Recepción
                </p>

                <h1 className="mt-1 text-3xl font-bold tracking-tight text-tinta-50">
                    Check-in de pacientes
                </h1>

                <p className="mt-2 text-sm text-tinta-400">
                    Registrá la llegada de un paciente mediante documento o código QR.
                </p>
            </header>


            <section className="rounded-2xl border border-tinta-800 bg-tinta-900 p-5">

                <div className="flex gap-2">

                    <button
                        type="button"
                        onClick={() =>
                            setModo('documento')
                        }
                        className={
                            modo === 'documento'
                                ? 'rounded-xl bg-marca-500 px-4 py-2 text-sm font-semibold text-white'
                                : 'rounded-xl border border-tinta-700 px-4 py-2 text-sm font-semibold text-tinta-300'
                        }
                    >
                        Por documento
                    </button>

                    <button
                        type="button"
                        onClick={() =>
                            setModo('qr')
                        }
                        className={
                            modo === 'qr'
                                ? 'rounded-xl bg-marca-500 px-4 py-2 text-sm font-semibold text-white'
                                : 'rounded-xl border border-tinta-700 px-4 py-2 text-sm font-semibold text-tinta-300'
                        }
                    >
                        Por QR
                    </button>

                </div>


                <form
                    onSubmit={enviar}
                    className="mt-5 space-y-4"
                >

                    {modo === 'documento' ? (
                        <Campo
                            etiqueta="Número de documento"
                            placeholder="Ej. 9002001"
                            value={documento}
                            onChange={
                                evento =>
                                    setDocumento(
                                        evento.target.value,
                                    )
                            }
                        />
                    ) : (
                        <Campo
                            etiqueta="Código QR"
                            placeholder="Pegá o escaneá el código"
                            value={qr}
                            onChange={
                                evento =>
                                    setQr(
                                        evento.target.value,
                                    )
                            }
                        />
                    )}


                    {error && (
                        <div
                            role="alert"
                            className="rounded-xl border border-alerta-500/40 bg-alerta-500/10 px-4 py-3 text-sm text-alerta-200"
                        >
                            {error}
                        </div>
                    )}


                    <Boton
                        type="submit"
                        cargando={cargando}
                    >
                        Registrar llegada
                    </Boton>

                </form>

            </section>


            {resultado && (
                <section className="rounded-2xl border border-marca-700 bg-marca-950/30 p-5">

                    <p className="text-sm font-semibold text-marca-400">
                        Check-in realizado
                    </p>

                    <h2 className="mt-1 text-xl font-bold text-tinta-100">
                        {resultado.patient.name}
                    </h2>


                    <div className="mt-5 grid gap-4 text-sm md:grid-cols-2">

                        <Dato
                            etiqueta="Documento"
                            valor={
                                resultado.patient
                                    .document_number ??
                                'Sin documento'
                            }
                        />

                        <Dato
                            etiqueta="Estado"
                            valor="Atendido"
                        />

                        <Dato
                            etiqueta="Sucursal"
                            valor={
                                resultado.branch.name
                            }
                        />

                        <Dato
                            etiqueta="Profesional"
                            valor={
                                resultado.practitioner
                                    .name
                            }
                        />

                        <Dato
                            etiqueta="Hora de ficha"
                            valor={
                                new Date(
                                    resultado.starts_at,
                                ).toLocaleString()
                            }
                        />

                        <Dato
                            etiqueta="Check-in"
                            valor={
                                new Date(
                                    resultado.checked_in_at,
                                ).toLocaleString()
                            }
                        />

                    </div>

                </section>
            )}

        </div>
    )
}


function Dato({
                  etiqueta,
                  valor,
              }: {
    etiqueta: string
    valor: string
}) {
    return (
        <div>
            <p className="text-tinta-500">
                {etiqueta}
            </p>

            <p className="mt-1 font-medium text-tinta-200">
                {valor}
            </p>
        </div>
    )
}