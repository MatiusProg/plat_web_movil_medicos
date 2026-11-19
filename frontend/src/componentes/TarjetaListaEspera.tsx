/**
 * US-52 — «¿Quieres que te avisemos?»
 *
 * Se muestra en `Disponibilidad.tsx` cuando el profesional no tiene espacios
 * libres en el rango consultado. El paciente (o un dependiente) se anota con un
 * rango de fechas de hasta 30 días y, si alguien cancela, el backend le guarda
 * el turno 15 minutos y le avisa. Qué tan arriba queda en la fila lo decide el
 * backend: acá sólo se muestra la posición que devuelve.
 *
 * Quien monta la tarjeta debería ponerle una `key` con profesional y rango, así
 * se reinicia sola cuando cambia la consulta.
 */

import { useEffect, useState } from 'react'

import { anotarseEnListaDeEspera, type EntradaEspera } from '@/api/listaEspera'
import { listarOpcionesDePaciente, type OpcionDePaciente } from '@/api/pacientes'
import { ErrorApi, type CodigoError } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { Boton } from '@/componentes/Boton'
import { useSesion } from '@/sesion/useSesion'

const MAXIMO_DIAS = 30

const MENSAJES: Partial<Record<CodigoError, string>> = {
  hay_turnos: 'Ya hay turnos libres en esas fechas: reserva uno.',
  ya_anotado: 'Ya estás en la lista de espera para esta búsqueda.',
  rango_largo: `El rango puede ser de hasta ${MAXIMO_DIAS} días.`,
  rango_pasado: 'Las fechas no pueden estar en el pasado.',
  rango_invalido: 'La fecha final no puede ser anterior a la inicial.',
  no_es_paciente: 'Tu cuenta no tiene un paciente al que anotar.',
}

const CAMPO =
  'border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 h-11 w-full rounded-xl border px-3 py-2 text-sm'

/** Días entre dos fechas `YYYY-MM-DD`, contando el primero y el último. */
function diasDelRango(desde: string, hasta: string): number {
  const inicio = Date.parse(`${desde}T00:00:00Z`)
  const fin = Date.parse(`${hasta}T00:00:00Z`)
  if (Number.isNaN(inicio) || Number.isNaN(fin)) return 0
  return Math.round((fin - inicio) / 86_400_000) + 1
}

/** Recorta un rango largo a lo que admite el backend, sin tocar el inicio. */
function hastaPermitido(desde: string, hasta: string): string {
  if (!desde || !hasta || diasDelRango(desde, hasta) <= MAXIMO_DIAS) return hasta
  const tope = new Date(`${desde}T00:00:00Z`)
  tope.setUTCDate(tope.getUTCDate() + MAXIMO_DIAS - 1)
  return tope.toISOString().slice(0, 10)
}

interface Props {
  practitionerId: string
  practitionerName: string
  /** Las especialidades del profesional; vacío si no se conocen. */
  specialties: { id: string; name: string }[]
  /** Sucursal elegida en la consulta, si hay una. */
  branchId?: string
  desde: string
  hasta: string
}

export function TarjetaListaEspera({
  practitionerId, practitionerName, specialties, branchId, desde, hasta,
}: Props) {
  const { token } = useSesion()
  const [opciones, setOpciones] = useState<OpcionDePaciente[] | null>(null)
  const [pacienteId, setPacienteId] = useState('')
  const [fechaDesde, setFechaDesde] = useState(desde)
  const [fechaHasta, setFechaHasta] = useState(() => hastaPermitido(desde, hasta))
  const [porEspecialidad, setPorEspecialidad] = useState(false)
  const [especialidadId, setEspecialidadId] = useState(specialties[0]?.id ?? '')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<ErrorApi | null>(null)
  const [entrada, setEntrada] = useState<EntradaEspera | null>(null)

  useEffect(() => {
    const control = new AbortController()
    listarOpcionesDePaciente({ token }, control.signal)
      .then((lista) => {
        setOpciones(lista)
        setPacienteId(lista[0]?.id ?? '')
      })
      .catch((fallo: unknown) => {
        if (fallo instanceof DOMException && fallo.name === 'AbortError') return
        setError(fallo instanceof ErrorApi ? fallo : null)
        setOpciones([])
      })
    return () => control.abort()
  }, [token])

  const dias = diasDelRango(fechaDesde, fechaHasta)
  const rangoValido = dias >= 1 && dias <= MAXIMO_DIAS
  const especialidad = specialties.find((s) => s.id === especialidadId) ?? specialties[0]

  const anotarse = async () => {
    if (!pacienteId || !rangoValido) return
    setEnviando(true)
    setError(null)
    try {
      const creada = await anotarseEnListaDeEspera(
        {
          patient: pacienteId,
          practitioner: porEspecialidad ? undefined : practitionerId,
          specialty: porEspecialidad ? especialidad?.id : undefined,
          branch: branchId || undefined,
          dateFrom: fechaDesde,
          dateTo: fechaHasta,
        },
        { token },
      )
      setEntrada(creada)
    } catch (fallo: unknown) {
      setError(fallo instanceof ErrorApi ? fallo : null)
    } finally {
      setEnviando(false)
    }
  }

  // El plan no incluye la función: se dice una vez y no se insiste.
  if (error && error.estado === 403 && error.codigo === 'plan_limit') {
    return <Aviso codigo={error.codigo} mensaje={error.message} />
  }

  return (
    <section
      aria-label="Lista de espera"
      className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 space-y-4 rounded-2xl border bg-white p-4"
    >
      <div>
        <h2 className="text-tinta-900 dark:text-tinta-50 font-semibold">
          ¿Quieres que te avisemos?
        </h2>
        <p className="text-tinta-500 mt-1 text-sm">
          Si alguien cancela un turno de {practitionerName}, te lo guardamos 15 minutos
          y te avisamos para que lo reserves.
        </p>
      </div>

      {entrada ? (
        <div
          role="status"
          className="border-marca-200 bg-marca-50 text-marca-700 dark:border-marca-900 dark:bg-marca-950/40 dark:text-marca-300 rounded-xl border px-3.5 py-3 text-sm"
        >
          <p className="font-medium">Quedaste en la lista de espera.</p>
          {entrada.position !== null && (
            <p className="mt-0.5">
              Eres el N.º <span className="font-semibold tabular-nums">{entrada.position}</span> de
              la fila. Puedes verla y salir de ella en «Mis fichas».
            </p>
          )}
        </div>
      ) : (
        <>
          {error && (
            <Aviso codigo={error.codigo} mensaje={MENSAJES[error.codigo] ?? error.message} />
          )}

          {opciones === null ? (
            <p className="text-tinta-500 text-sm">Cargando…</p>
          ) : opciones.length === 0 ? (
            !error && (
              <p className="text-tinta-500 text-sm">No hay a quién anotar en la lista todavía.</p>
            )
          ) : (
            <div className="grid gap-3 sm:grid-cols-3">
              {opciones.length > 1 && (
                <label className="text-sm sm:col-span-3">
                  <span className="text-tinta-700 dark:text-tinta-300 mb-1 block font-medium">
                    ¿Para quién es?
                  </span>
                  <select
                    value={pacienteId}
                    onChange={(e) => setPacienteId(e.target.value)}
                    className={CAMPO}
                  >
                    {opciones.map((opcion) => (
                      <option key={opcion.id} value={opcion.id}>
                        {opcion.is_self
                          ? opcion.full_name
                          : `${opcion.full_name} · ${opcion.relationship_label}`}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              <label className="text-sm">
                <span className="text-tinta-700 dark:text-tinta-300 mb-1 block font-medium">
                  Desde
                </span>
                <input
                  type="date"
                  value={fechaDesde}
                  onChange={(e) => setFechaDesde(e.target.value)}
                  className={CAMPO}
                />
              </label>
              <label className="text-sm">
                <span className="text-tinta-700 dark:text-tinta-300 mb-1 block font-medium">
                  Hasta
                </span>
                <input
                  type="date"
                  value={fechaHasta}
                  onChange={(e) => setFechaHasta(e.target.value)}
                  className={CAMPO}
                />
              </label>
              <p
                className={`self-end pb-2 text-xs ${
                  rangoValido ? 'text-tinta-500' : 'text-alerta-700 dark:text-alerta-200'
                }`}
              >
                {rangoValido
                  ? `${dias} ${dias === 1 ? 'día' : 'días'} (máximo ${MAXIMO_DIAS})`
                  : dias > MAXIMO_DIAS
                    ? `El rango puede ser de hasta ${MAXIMO_DIAS} días.`
                    : 'La fecha final no puede ser anterior a la inicial.'}
              </p>

              {specialties.length > 0 && (
                <div className="space-y-2 text-sm sm:col-span-3">
                  <label className="flex min-h-11 items-center gap-3">
                    <input
                      type="checkbox"
                      checked={porEspecialidad}
                      onChange={(e) => setPorEspecialidad(e.target.checked)}
                      className="accent-marca-600 size-5 shrink-0"
                    />
                    <span className="text-tinta-700 dark:text-tinta-300">
                      {specialties.length === 1
                        ? `O cualquier profesional de ${specialties[0].name}`
                        : 'O cualquier profesional de una especialidad'}
                    </span>
                  </label>
                  {porEspecialidad && specialties.length > 1 && (
                    <select
                      aria-label="Especialidad"
                      value={especialidad?.id ?? ''}
                      onChange={(e) => setEspecialidadId(e.target.value)}
                      className={CAMPO}
                    >
                      {specialties.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              )}

              <div className="sm:col-span-3">
                <Boton
                  onClick={anotarse}
                  cargando={enviando}
                  textoCargando="Anotando…"
                  disabled={!pacienteId || !rangoValido}
                  className="min-h-11 sm:w-auto sm:px-5"
                >
                  Anotarme en lista de espera
                </Boton>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  )
}
