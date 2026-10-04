import {
    useCallback,
    useEffect,
    useState,
    type FormEvent,
} from 'react'

import {
    buscarPacientes,
    crearPaciente,
    desactivarPaciente,
    editarPaciente,
    fusionarPacientes,
    obtenerPaciente,
    type PacienteDetalle,
    type PacienteGuardar,
    type PacienteResumen,
} from '@/api/pacientes'

import { ErrorApi } from '@/api/tipos'
import { Boton } from '@/componentes/Boton'
import { Campo } from '@/componentes/Campo'
import { useSesion } from '@/sesion/useSesion'


const VACIO: PacienteGuardar = {
    document_type: 'CI',
    document_number: '',
    first_name: '',
    last_name: '',
    birth_date: null,
    sex: '',
    phone: '',
}


export function Pacientes() {
    const {
        token,
        usuario,
        puede,
    } = useSesion()

    const contexto = {
        token,
        organizacion:
            usuario?.organization ?? null,
    }


    const [pacientes, setPacientes] =
        useState<PacienteResumen[]>([])

    const [total, setTotal] =
        useState(0)

    const [busqueda, setBusqueda] =
        useState('')

    const [estado, setEstado] =
        useState<
            'active' | 'inactive' | ''
        >('')

    const [cargando, setCargando] =
        useState(false)

    const [mensajeError, setMensajeError] =
        useState('')

    const [detalle, setDetalle] =
        useState<PacienteDetalle | null>(null)

    const [formulario, setFormulario] =
        useState<PacienteGuardar>(VACIO)

    const [editandoId, setEditandoId] =
        useState<string | null>(null)

    const [guardando, setGuardando] =
        useState(false)

    const [fusionOrigen, setFusionOrigen] =
        useState('')

    const [fusionDestino, setFusionDestino] =
        useState('')

    const [pacienteADesactivar, setPacienteADesactivar] =
        useState<PacienteResumen | null>(null)

    const [desactivando, setDesactivando] =
        useState(false)

    const [confirmandoFusion, setConfirmandoFusion] =
        useState(false)

    const [fusionando, setFusionando] =
        useState(false)


    const cargar = useCallback(
        async () => {
            setCargando(true)
            setMensajeError('')

            try {
                const respuesta =
                    await buscarPacientes(
                        {
                            q: busqueda,
                            status: estado,
                            pageSize: 100,
                        },
                        contexto,
                    )

                setPacientes(
                    respuesta.results,
                )

                setTotal(
                    respuesta.count,
                )
            } catch (error) {
                setMensajeError(
                    error instanceof Error
                        ? error.message
                        : 'No se pudieron cargar los pacientes.',
                )
            } finally {
                setCargando(false)
            }
        },
        [
            busqueda,
            estado,
            token,
            usuario?.organization,
        ],
    )


    useEffect(() => {
        void cargar()
    }, [cargar])


    const verDetalle =
        async (id: string) => {
            setMensajeError('')

            try {
                const paciente =
                    await obtenerPaciente(
                        id,
                        contexto,
                    )

                setDetalle(paciente)
            } catch (error) {
                setMensajeError(
                    error instanceof Error
                        ? error.message
                        : 'No se pudo consultar el paciente.',
                )
            }
        }


    const prepararEdicion =
        async (id: string) => {
            try {
                const paciente =
                    await obtenerPaciente(
                        id,
                        contexto,
                    )

                setFormulario({
                    document_type:
                    paciente.document_type,

                    document_number:
                    paciente.document_number,

                    first_name:
                    paciente.first_name,

                    last_name:
                    paciente.last_name,

                    birth_date:
                    paciente.birth_date,

                    sex:
                        paciente.sex ?? '',

                    phone:
                        paciente.phone ?? '',
                })

                setEditandoId(id)

                window.scrollTo({
                    top: 0,
                    behavior: 'smooth',
                })
            } catch (error) {
                setMensajeError(
                    error instanceof Error
                        ? error.message
                        : 'No se pudo cargar el paciente.',
                )
            }
        }


    const guardar =
        async (
            evento: FormEvent,
        ) => {
            evento.preventDefault()

            setGuardando(true)
            setMensajeError('')

            const datos: PacienteGuardar = {
                ...formulario,

                document_number:
                    formulario.document_number
                        ?.trim() || null,

                birth_date:
                    formulario.birth_date || null,

                first_name:
                    formulario.first_name.trim(),

                last_name:
                    formulario.last_name.trim(),

                phone:
                    formulario.phone.trim(),
            }

            try {
                if (editandoId) {
                    await editarPaciente(
                        editandoId,
                        datos,
                        contexto,
                    )
                } else {
                    await crearPaciente(
                        datos,
                        contexto,
                    )
                }

                setFormulario(VACIO)
                setEditandoId(null)

                await cargar()
            } catch (error) {
                setMensajeError(
                    error instanceof ErrorApi
                        ? error.message
                        : 'No se pudo guardar el paciente.',
                )
            } finally {
                setGuardando(false)
            }
        }


    const confirmarDesactivacion =
        async () => {
            if (!pacienteADesactivar) {
                return
            }

            setDesactivando(true)
            setMensajeError('')

            try {
                await desactivarPaciente(
                    pacienteADesactivar.id,
                    contexto,
                )

                if (
                    detalle?.id ===
                    pacienteADesactivar.id
                ) {
                    setDetalle(null)
                }

                setPacienteADesactivar(null)

                await cargar()
            } catch (error) {
                setMensajeError(
                    error instanceof Error
                        ? error.message
                        : 'No se pudo desactivar el paciente.',
                )
            } finally {
                setDesactivando(false)
            }
        }



    const solicitarFusion =
        () => {
            setMensajeError('')

            if (
                !fusionOrigen ||
                !fusionDestino
            ) {
                setMensajeError(
                    'Seleccioná el paciente origen y el paciente destino.',
                )
                return
            }

            if (
                fusionOrigen ===
                fusionDestino
            ) {
                setMensajeError(
                    'El origen y el destino no pueden ser el mismo paciente.',
                )
                return
            }

            setConfirmandoFusion(true)
        }


    const confirmarFusion =
        async () => {
            if (
                !fusionOrigen ||
                !fusionDestino
            ) {
                return
            }

            setFusionando(true)
            setMensajeError('')

            try {
                await fusionarPacientes(
                    {
                        source_patient:
                        fusionOrigen,

                        target_patient:
                        fusionDestino,
                    },
                    contexto,
                )

                setFusionOrigen('')
                setFusionDestino('')
                setConfirmandoFusion(false)
                setDetalle(null)

                await cargar()
            } catch (error) {
                setMensajeError(
                    error instanceof Error
                        ? error.message
                        : 'No se pudieron fusionar los pacientes.',
                )
            } finally {
                setFusionando(false)
            }
        }



    return (
        <div className="mx-auto max-w-7xl space-y-7">

            <header>
                <p className="text-sm font-semibold text-marca-400">
                    Gestión de pacientes
                </p>

                <h1 className="mt-1 text-3xl font-bold tracking-tight text-tinta-50">
                    Pacientes
                </h1>

                <p className="mt-2 text-sm text-tinta-400">
                    Buscá, consultá y administrá los pacientes de la organización.
                </p>
            </header>


            {mensajeError && (
                <div
                    role="alert"
                    className="rounded-xl border border-alerta-500/40 bg-alerta-500/10 px-4 py-3 text-sm text-alerta-200"
                >
                    {mensajeError}
                </div>
            )}


            <section className="rounded-2xl border border-tinta-800 bg-tinta-900 p-5">

                <div className="grid gap-4 md:grid-cols-[1fr_220px_auto]">

                    <Campo
                        etiqueta="Buscar paciente"
                        placeholder="Nombre, apellido o documento"
                        value={busqueda}
                        onChange={
                            evento =>
                                setBusqueda(
                                    evento.target.value,
                                )
                        }
                    />

                    <div className="space-y-1.5">
                        <label className="block text-sm font-medium text-tinta-300">
                            Estado
                        </label>

                        <select
                            value={estado}
                            onChange={
                                evento =>
                                    setEstado(
                                        evento.target.value as
                                            | 'active'
                                            | 'inactive'
                                            | '',
                                    )
                            }
                            className="w-full rounded-xl border border-tinta-700 bg-tinta-900 px-3.5 py-2.5 text-sm text-tinta-100 outline-none focus:border-marca-500"
                        >
                            <option value="">
                                Todos
                            </option>

                            <option value="active">
                                Activos
                            </option>

                            <option value="inactive">
                                Inactivos
                            </option>
                        </select>
                    </div>

                    <div className="flex items-end">
                        <Boton
                            type="button"
                            cargando={cargando}
                            onClick={() => void cargar()}
                        >
                            Buscar
                        </Boton>
                    </div>
                </div>
            </section>


            {(puede('patients.patient.create') ||
                puede('patients.patient.update')) && (
                <section className="rounded-2xl border border-tinta-800 bg-tinta-900 p-5">

                    <h2 className="text-lg font-semibold text-tinta-100">
                        {editandoId
                            ? 'Editar paciente'
                            : 'Registrar paciente'}
                    </h2>

                    <form
                        onSubmit={guardar}
                        className="mt-5 grid gap-4 md:grid-cols-2"
                    >

                        <div className="space-y-1.5">
                            <label className="block text-sm font-medium text-tinta-300">
                                Tipo de documento
                            </label>

                            <select
                                value={
                                    formulario.document_type
                                }
                                onChange={
                                    evento =>
                                        setFormulario(
                                            actual => ({
                                                ...actual,
                                                document_type:
                                                evento.target.value,
                                            }),
                                        )
                                }
                                className="w-full rounded-xl border border-tinta-700 bg-tinta-900 px-3.5 py-2.5 text-sm text-tinta-100"
                            >
                                <option value="CI">
                                    Cédula de identidad
                                </option>

                                <option value="PAS">
                                    Pasaporte
                                </option>

                                <option value="OTRO">
                                    Otro
                                </option>
                            </select>
                        </div>

                        <Campo
                            etiqueta="Número de documento"
                            value={
                                formulario.document_number ??
                                ''
                            }
                            onChange={
                                evento =>
                                    setFormulario(
                                        actual => ({
                                            ...actual,
                                            document_number:
                                            evento.target.value,
                                        }),
                                    )
                            }
                        />

                        <Campo
                            etiqueta="Nombres"
                            required
                            value={
                                formulario.first_name
                            }
                            onChange={
                                evento =>
                                    setFormulario(
                                        actual => ({
                                            ...actual,
                                            first_name:
                                            evento.target.value,
                                        }),
                                    )
                            }
                        />

                        <Campo
                            etiqueta="Apellidos"
                            required
                            value={
                                formulario.last_name
                            }
                            onChange={
                                evento =>
                                    setFormulario(
                                        actual => ({
                                            ...actual,
                                            last_name:
                                            evento.target.value,
                                        }),
                                    )
                            }
                        />

                        <Campo
                            etiqueta="Fecha de nacimiento"
                            type="date"
                            value={
                                formulario.birth_date ??
                                ''
                            }
                            onChange={
                                evento =>
                                    setFormulario(
                                        actual => ({
                                            ...actual,
                                            birth_date:
                                                evento.target.value ||
                                                null,
                                        }),
                                    )
                            }
                        />

                        <div className="space-y-1.5">
                            <label className="block text-sm font-medium text-tinta-300">
                                Sexo
                            </label>

                            <select
                                value={formulario.sex}
                                onChange={
                                    evento =>
                                        setFormulario(
                                            actual => ({
                                                ...actual,
                                                sex:
                                                evento.target.value,
                                            }),
                                        )
                                }
                                className="w-full rounded-xl border border-tinta-700 bg-tinta-900 px-3.5 py-2.5 text-sm text-tinta-100"
                            >
                                <option value="">
                                    Sin especificar
                                </option>

                                <option value="M">
                                    Masculino
                                </option>

                                <option value="F">
                                    Femenino
                                </option>

                                <option value="X">
                                    Otro
                                </option>
                            </select>
                        </div>

                        <Campo
                            etiqueta="Teléfono"
                            value={formulario.phone}
                            onChange={
                                evento =>
                                    setFormulario(
                                        actual => ({
                                            ...actual,
                                            phone:
                                            evento.target.value,
                                        }),
                                    )
                            }
                        />


                        <div className="flex items-end gap-3">

                            <Boton
                                type="submit"
                                cargando={guardando}
                            >
                                {editandoId
                                    ? 'Guardar cambios'
                                    : 'Registrar paciente'}
                            </Boton>

                            {editandoId && (
                                <button
                                    type="button"
                                    onClick={() => {
                                        setEditandoId(null)
                                        setFormulario(VACIO)
                                    }}
                                    className="rounded-xl border border-tinta-700 px-4 py-2.5 text-sm font-semibold text-tinta-300 hover:bg-tinta-800"
                                >
                                    Cancelar
                                </button>
                            )}
                        </div>

                    </form>
                </section>
            )}


            <section className="overflow-hidden rounded-2xl border border-tinta-800 bg-tinta-900">

                <div className="flex items-center justify-between border-b border-tinta-800 px-5 py-4">

                    <h2 className="font-semibold text-tinta-100">
                        Resultados
                    </h2>

                    <span className="text-sm text-tinta-500">
            {total} pacientes
          </span>
                </div>


                <div className="overflow-x-auto">

                    <table className="min-w-full text-sm">

                        <thead className="bg-tinta-950/40 text-left text-tinta-400">
                        <tr>
                            <th className="px-5 py-3">
                                Paciente
                            </th>

                            <th className="px-5 py-3">
                                Documento
                            </th>

                            <th className="px-5 py-3">
                                Teléfono
                            </th>

                            <th className="px-5 py-3">
                                Estado
                            </th>

                            <th className="px-5 py-3 text-right">
                                Acciones
                            </th>
                        </tr>
                        </thead>


                        <tbody className="divide-y divide-tinta-800">

                        {pacientes.map(
                            paciente => (
                                <tr
                                    key={paciente.id}
                                    className="text-tinta-300"
                                >

                                    <td className="px-5 py-4 font-medium text-tinta-100">
                                        {paciente.full_name}
                                    </td>

                                    <td className="px-5 py-4">
                                        {paciente.document_number ??
                                            'Sin documento'}
                                    </td>

                                    <td className="px-5 py-4">
                                        {paciente.phone ||
                                            '—'}
                                    </td>

                                    <td className="px-5 py-4">
                                        {paciente.is_active
                                            ? 'Activo'
                                            : 'Inactivo'}
                                    </td>

                                    <td className="px-5 py-4">

                                        <div className="flex justify-end gap-2">

                                            <button
                                                type="button"
                                                onClick={() =>
                                                    void verDetalle(
                                                        paciente.id,
                                                    )
                                                }
                                                className="rounded-lg border border-tinta-700 px-3 py-2 text-xs font-semibold hover:bg-tinta-800"
                                            >
                                                Ver
                                            </button>

                                            {puede(
                                                'patients.patient.update',
                                            ) && (
                                                <button
                                                    type="button"
                                                    onClick={() =>
                                                        void prepararEdicion(
                                                            paciente.id,
                                                        )
                                                    }
                                                    className="rounded-lg border border-tinta-700 px-3 py-2 text-xs font-semibold hover:bg-tinta-800"
                                                >
                                                    Editar
                                                </button>
                                            )}

                                            {paciente.is_active &&
                                                puede(
                                                    'patients.patient.deactivate',
                                                ) && (
                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            setPacienteADesactivar(
                                                                paciente,
                                                            )
                                                        }
                                                        className="rounded-lg border border-alerta-500/40 px-3 py-2 text-xs font-semibold text-alerta-300 hover:bg-alerta-500/10"
                                                    >
                                                        Desactivar
                                                    </button>
                                                )}

                                        </div>
                                    </td>
                                </tr>
                            ),
                        )}

                        </tbody>
                    </table>
                </div>
            </section>


            {puede(
                'patients.patient.merge',
            ) && (
                <section className="rounded-2xl border border-tinta-800 bg-tinta-900 p-5">

                    <h2 className="text-lg font-semibold text-tinta-100">
                        Fusionar duplicados
                    </h2>

                    <p className="mt-1 text-sm text-tinta-500">
                        El registro origen será absorbido por el registro destino.
                    </p>

                    <div className="mt-4 grid gap-4 md:grid-cols-[1fr_1fr_auto]">

                        <select
                            value={fusionOrigen}
                            onChange={
                                evento =>
                                    setFusionOrigen(
                                        evento.target.value,
                                    )
                            }
                            className="rounded-xl border border-tinta-700 bg-tinta-900 px-3.5 py-2.5 text-sm text-tinta-100"
                        >
                            <option value="">
                                Paciente origen
                            </option>

                            {pacientes
                                .filter(
                                    paciente =>
                                        paciente.is_active,
                                )
                                .map(
                                    paciente => (
                                        <option
                                            key={paciente.id}
                                            value={paciente.id}
                                        >
                                            {paciente.full_name}
                                        </option>
                                    ),
                                )}
                        </select>


                        <select
                            value={fusionDestino}
                            onChange={
                                evento =>
                                    setFusionDestino(
                                        evento.target.value,
                                    )
                            }
                            className="rounded-xl border border-tinta-700 bg-tinta-900 px-3.5 py-2.5 text-sm text-tinta-100"
                        >
                            <option value="">
                                Paciente destino
                            </option>

                            {pacientes
                                .filter(
                                    paciente =>
                                        paciente.is_active,
                                )
                                .map(
                                    paciente => (
                                        <option
                                            key={paciente.id}
                                            value={paciente.id}
                                        >
                                            {paciente.full_name}
                                        </option>
                                    ),
                                )}
                        </select>


                        <Boton
                            type="button"
                            onClick={
                                solicitarFusion
                            }
                        >
                            Fusionar
                        </Boton>

                    </div>
                </section>
            )}


            {detalle && (
                <section className="rounded-2xl border border-marca-800 bg-marca-950/30 p-5">

                    <div className="flex items-start justify-between gap-4">

                        <div>
                            <p className="text-sm font-semibold text-marca-400">
                                Detalle del paciente
                            </p>

                            <h2 className="mt-1 text-xl font-bold text-tinta-100">
                                {detalle.full_name}
                            </h2>
                        </div>

                        <button
                            type="button"
                            onClick={() =>
                                setDetalle(null)
                            }
                            className="rounded-lg px-3 py-2 text-sm text-tinta-400 hover:bg-tinta-800"
                        >
                            Cerrar
                        </button>
                    </div>


                    <div className="mt-5 grid gap-4 text-sm md:grid-cols-3">

                        <Dato
                            etiqueta="Documento"
                            valor={
                                detalle.document_number ??
                                'Sin documento'
                            }
                        />

                        <Dato
                            etiqueta="Fecha de nacimiento"
                            valor={
                                detalle.birth_date ??
                                'No registrada'
                            }
                        />

                        <Dato
                            etiqueta="Teléfono"
                            valor={
                                detalle.phone ||
                                'No registrado'
                            }
                        />

                    </div>


                    <div className="mt-6">

                        <h3 className="font-semibold text-tinta-200">
                            Próximas fichas
                        </h3>

                        {detalle.upcoming_appointments.length ===
                        0 ? (
                            <p className="mt-3 text-sm text-tinta-500">
                                No tiene próximas fichas.
                            </p>
                        ) : (
                            <div className="mt-3 space-y-2">

                                {detalle.upcoming_appointments.map(
                                    ficha => (
                                        <div
                                            key={ficha.id}
                                            className="rounded-xl border border-tinta-800 bg-tinta-950/40 px-4 py-3 text-sm"
                                        >
                                            <p className="font-medium text-tinta-200">
                                                {
                                                    ficha.practitioner_name
                                                }
                                            </p>

                                            <p className="mt-1 text-tinta-500">
                                                {ficha.branch_name}
                                                {' · '}
                                                {new Date(
                                                    ficha.starts_at,
                                                ).toLocaleString()}
                                                {' · '}
                                                {ficha.status_label}
                                            </p>
                                        </div>
                                    ),
                                )}

                            </div>
                        )}

                    </div>

                </section>
            )}


            {/* =========================================================
                MODAL — DESACTIVAR PACIENTE
            ========================================================= */}

            {pacienteADesactivar && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-[2px]"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="titulo-desactivar-paciente"
                    onMouseDown={
                        evento => {
                            if (
                                evento.target ===
                                evento.currentTarget &&
                                !desactivando
                            ) {
                                setPacienteADesactivar(null)
                            }
                        }
                    }
                >
                    <div className="w-full max-w-md rounded-2xl border border-tinta-700 bg-tinta-900 p-6 shadow-2xl">

                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-500/10 text-red-400">
                            <svg
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="1.8"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                className="h-6 w-6"
                                aria-hidden="true"
                            >
                                <path d="M12 9v4" />
                                <path d="M12 17h.01" />
                                <path d="M10.3 3.7 2.8 17a2 2 0 0 0 1.7 3h15a2 2 0 0 0 1.7-3L13.7 3.7a2 2 0 0 0-3.4 0Z" />
                            </svg>
                        </div>


                        <h2
                            id="titulo-desactivar-paciente"
                            className="mt-5 text-xl font-bold text-tinta-100"
                        >
                            Desactivar paciente
                        </h2>


                        <p className="mt-2 text-sm leading-6 text-tinta-400">
                            ¿Seguro que deseas desactivar a{' '}
                            <strong className="text-tinta-200">
                                {pacienteADesactivar.full_name}
                            </strong>
                            ?
                        </p>


                        <p className="mt-2 text-sm leading-6 text-tinta-500">
                            El paciente permanecerá registrado y podrás consultarlo
                            usando el filtro de pacientes inactivos.
                        </p>


                        <div className="mt-6 flex justify-end gap-3">

                            <button
                                type="button"
                                disabled={desactivando}
                                onClick={() =>
                                    setPacienteADesactivar(null)
                                }
                                className="rounded-xl border border-tinta-700 px-4 py-2.5 text-sm font-semibold text-tinta-300 transition hover:bg-tinta-800 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                                Cancelar
                            </button>


                            <button
                                type="button"
                                disabled={desactivando}
                                onClick={() =>
                                    void confirmarDesactivacion()
                                }
                                className="rounded-xl bg-red-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                                {desactivando
                                    ? 'Desactivando...'
                                    : 'Sí, desactivar'}
                            </button>

                        </div>

                    </div>
                </div>
            )}


            {/* =========================================================
                MODAL — FUSIONAR PACIENTES
            ========================================================= */}

            {confirmandoFusion && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-[2px]"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="titulo-fusionar-pacientes"
                    onMouseDown={
                        evento => {
                            if (
                                evento.target ===
                                evento.currentTarget &&
                                !fusionando
                            ) {
                                setConfirmandoFusion(false)
                            }
                        }
                    }
                >
                    <div className="w-full max-w-lg rounded-2xl border border-tinta-700 bg-tinta-900 p-6 shadow-2xl">

                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-500/10 text-amber-400">
                            <svg
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="1.8"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                className="h-6 w-6"
                                aria-hidden="true"
                            >
                                <path d="M7 7h7a4 4 0 0 1 4 4v6" />
                                <path d="m15 14 3 3 3-3" />
                                <path d="M17 7h-7a4 4 0 0 0-4 4v6" />
                                <path d="m9 14-3 3-3-3" />
                            </svg>
                        </div>


                        <h2
                            id="titulo-fusionar-pacientes"
                            className="mt-5 text-xl font-bold text-tinta-100"
                        >
                            Confirmar fusión de pacientes
                        </h2>


                        <p className="mt-2 text-sm leading-6 text-tinta-400">
                            El paciente origen será absorbido por el paciente destino.
                            El registro destino es el que se conservará.
                        </p>


                        <div className="mt-5 grid gap-3 rounded-xl border border-tinta-800 bg-tinta-950/40 p-4 sm:grid-cols-2">

                            <div>
                                <p className="text-xs font-semibold uppercase tracking-wide text-tinta-500">
                                    Origen
                                </p>

                                <p className="mt-1 font-semibold text-tinta-200">
                                    {
                                        pacientes.find(
                                            paciente =>
                                                paciente.id === fusionOrigen,
                                        )?.full_name ?? 'Paciente seleccionado'
                                    }
                                </p>

                                <p className="mt-1 text-xs text-red-300">
                                    Será absorbido
                                </p>
                            </div>


                            <div>
                                <p className="text-xs font-semibold uppercase tracking-wide text-tinta-500">
                                    Destino
                                </p>

                                <p className="mt-1 font-semibold text-tinta-200">
                                    {
                                        pacientes.find(
                                            paciente =>
                                                paciente.id === fusionDestino,
                                        )?.full_name ?? 'Paciente seleccionado'
                                    }
                                </p>

                                <p className="mt-1 text-xs text-emerald-300">
                                    Se conservará
                                </p>
                            </div>

                        </div>


                        <p className="mt-4 text-sm leading-6 text-tinta-500">
                            Realizá esta operación únicamente cuando ambos registros
                            correspondan a la misma persona.
                        </p>


                        <div className="mt-6 flex justify-end gap-3">

                            <button
                                type="button"
                                disabled={fusionando}
                                onClick={() =>
                                    setConfirmandoFusion(false)
                                }
                                className="rounded-xl border border-tinta-700 px-4 py-2.5 text-sm font-semibold text-tinta-300 transition hover:bg-tinta-800 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                                Cancelar
                            </button>


                            <button
                                type="button"
                                disabled={fusionando}
                                onClick={() =>
                                    void confirmarFusion()
                                }
                                className="rounded-xl bg-amber-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-amber-500 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                                {fusionando
                                    ? 'Fusionando...'
                                    : 'Sí, fusionar'}
                            </button>

                        </div>

                    </div>
                </div>
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
