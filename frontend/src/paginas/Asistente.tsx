/**
 * US-31, US-32 y US-34 — El asistente de orientación, en la web.
 *
 * Es la misma conversación que la del móvil (`assistant_screen.dart`) sobre el
 * mismo endpoint, y hace cumplir las mismas tres reglas aunque el backend
 * falle:
 *
 *   1. **Si no hay respuesta, no se inventa una.** Servidor caído, sin red o
 *      un 503 del proveedor: se dice "no puedo responder ahora" y se ofrece
 *      reintentar. Nunca un texto de relleno.
 *   2. **Una urgencia corta el camino a la reserva (US-34).** Con `emergency`
 *      no se muestra especialidad ni el botón de buscar profesionales: se
 *      deriva a emergencias, en rojo y antes que cualquier otra cosa.
 *   3. **La sugerencia viaja con sus fragmentos.** Son los que muestran en qué
 *      se basó el asistente, y lo que demuestra que no alucinó.
 *
 * Desde US-32 el mismo chat contesta también lo administrativo —horarios,
 * sedes, precios, preparación—. Esa respuesta llega con `kind:
 * "administrativa"` y sin especialidad, así que no hay botón de reservar.
 *
 * **US-33 — Reservar sin salir de la conversación.** Cuando hay especialidad
 * (sugerida, o la del servicio por el que se preguntó), el asistente ofrece
 * turnos reales de `assistant/slots/`; si la pregunta ya pedía reservar ("quiero
 * una ficha el jueves") los pide solo. El paciente elige uno, confirma en el
 * mismo modal de la pantalla de reserva y la ficha nace pendiente de pago. El
 * modelo no elige turnos ni reserva: los turnos salen de la disponibilidad y
 * la reserva sólo existe detrás de *Confirmar reserva*.
 *
 * La conversación vive sólo en memoria y a propósito: quien le cuenta sus
 * síntomas a un chatbot está escribiendo información de salud, y dejarla en
 * `localStorage` la expone a cualquiera que use la misma computadora —que en
 * un centro médico es lo normal—.
 */

import { useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { Link } from 'react-router-dom'

import {
  consultarAsistente,
  pedirTurnos,
  reservarDesdeAsistente,
  type RespuestaAsistente,
  type RespuestaTurnos,
  type TurnoOfrecido,
} from '@/api/asistente'
import type { Ficha } from '@/api/fichas'
import { ErrorApi } from '@/api/tipos'
import { IconoAlerta } from '@/componentes/iconos'
import { ModalReservarFicha } from '@/componentes/ModalReservarFicha'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'

/** El mismo tope que `SuggestRequestSerializer`: cada carácter gasta cuota. */
const LARGO_MAXIMO = 1000

const EJEMPLOS = [
  'Tengo manchas en la piel que me pican hace una semana',
  'Me duele la rodilla cuando subo gradas',
  '¿A qué hora abre la sucursal?',
  '¿Tengo que ir en ayunas al análisis de sangre?',
]

/** Atajos para pedir otro horario sin escribir. Los entiende `preferences.py`. */
const PREFERENCIAS_RAPIDAS = ['Mañana', 'Por la mañana', 'Por la tarde', 'La semana que viene']

interface Especialidad {
  id: string
  name: string
}

/** Lo que hace falta para volver a pedir los mismos turnos. */
interface PedidoDeTurnos {
  especialidad: Especialidad
  preferencia: string
}

type OfertaDeTurnos = Extract<RespuestaTurnos, { emergency: false }>

type Turno =
  | { tipo: 'paciente'; texto: string }
  | { tipo: 'asistente'; respuesta: RespuestaAsistente }
  | { tipo: 'turnos'; pedido: PedidoDeTurnos; respuesta: OfertaDeTurnos }
  | { tipo: 'reservada'; ficha: Ficha }
  | { tipo: 'aviso'; texto: string }
  /** `texto` es la pregunta que hay que reintentar; `pedido`, los turnos. */
  | { tipo: 'error'; motivo: string; texto: string; pedido?: PedidoDeTurnos }

/** El turno que el paciente tocó, mientras decide en el modal. */
interface Eleccion {
  turno: TurnoOfrecido
  pedido: PedidoDeTurnos
}

export function Asistente() {
  const { token } = useSesion()
  useTitulo('Asistente de orientación')

  const [turnos, setTurnos] = useState<Turno[]>([])
  const [entrada, setEntrada] = useState('')
  const [esperando, setEsperando] = useState(false)

  // US-33: el turno elegido y el estado de su confirmación.
  const [eleccion, setEleccion] = useState<Eleccion | null>(null)
  const [reservando, setReservando] = useState(false)
  const [errorReserva, setErrorReserva] = useState<ErrorApi | null>(null)

  const fondo = useRef<HTMLDivElement | null>(null)
  const casilla = useRef<HTMLTextAreaElement | null>(null)
  const aborto = useRef<AbortController | null>(null)

  useEffect(() => () => aborto.current?.abort(), [])

  // Cada turno nuevo baja hasta el final, como en cualquier chat.
  useEffect(() => {
    fondo.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [turnos, esperando])

  const enviar = async (reintento?: string) => {
    const pregunta = (reintento ?? entrada).trim()
    if (!pregunta || esperando) return

    setTurnos((previos) =>
      reintento === undefined
        ? [...previos, { tipo: 'paciente', texto: pregunta }]
        : previos.filter((t) => !(t.tipo === 'error' && t.texto === pregunta)),
    )
    if (reintento === undefined) setEntrada('')
    setEsperando(true)

    aborto.current?.abort()
    const control = new AbortController()
    aborto.current = control

    let turno: Turno
    try {
      const respuesta = await consultarAsistente(pregunta, { token }, control.signal)
      turno = { tipo: 'asistente', respuesta }
    } catch (fallo: unknown) {
      if (fallo instanceof DOMException && fallo.name === 'AbortError') return
      turno = { tipo: 'error', motivo: motivoDelFallo(fallo), texto: pregunta }
    }

    setTurnos((previos) => [...previos, turno])

    // US-33: la pregunta ya pedía reservar. Los turnos se piden solos, con la
    // misma pregunta como preferencia: "…el jueves por la tarde" ya filtra.
    const pista = turno.tipo === 'asistente' ? turno.respuesta.booking : undefined
    if (pista?.available && pista.booking_intent && pista.specialty) {
      await buscarTurnos({ especialidad: pista.specialty, preferencia: pregunta }, control)
      return
    }

    setEsperando(false)
    casilla.current?.focus()
  }

  /**
   * US-33 — Pide turnos de una especialidad. `textoPaciente` es lo que tocó
   * o escribió el paciente ("Por la tarde"), y se muestra como su mensaje.
   */
  const buscarTurnos = async (
    pedido: PedidoDeTurnos,
    controlHeredado?: AbortController,
    textoPaciente?: string,
  ) => {
    let control = controlHeredado
    if (!control) {
      aborto.current?.abort()
      control = new AbortController()
      aborto.current = control
      if (textoPaciente) {
        setTurnos((previos) => [...previos, { tipo: 'paciente', texto: textoPaciente }])
      }
    }
    setEsperando(true)

    let turno: Turno
    try {
      const respuesta = await pedirTurnos(
        pedido.especialidad.id, pedido.preferencia, { token }, control.signal,
      )
      turno = respuesta.emergency
        ? { tipo: 'asistente', respuesta: derivacion(respuesta.answer) }
        : { tipo: 'turnos', pedido, respuesta }
    } catch (fallo: unknown) {
      if (fallo instanceof DOMException && fallo.name === 'AbortError') return
      turno = { tipo: 'error', motivo: motivoDelFallo(fallo), texto: '', pedido }
    }

    setTurnos((previos) => [...previos, turno])
    setEsperando(false)
    casilla.current?.focus()
  }

  const reintentarTurnos = (pedido: PedidoDeTurnos) => {
    setTurnos((previos) => previos.filter((t) => !(t.tipo === 'error' && t.pedido === pedido)))
    void buscarTurnos(pedido)
  }

  const cerrarModal = () => {
    if (reservando) return
    setEleccion(null)
    setErrorReserva(null)
  }

  const confirmarReserva = async ({ patientId }: { patientId: string }) => {
    if (!eleccion) return
    setReservando(true)
    setErrorReserva(null)
    try {
      const ficha = await reservarDesdeAsistente(
        { patient: patientId, turno: eleccion.turno },
        { token },
      )
      setEleccion(null)
      setTurnos((previos) => [...previos, { tipo: 'reservada', ficha }])
    } catch (fallo: unknown) {
      const error = fallo instanceof ErrorApi ? fallo : null
      // El turno se ocupó entre que se ofreció y que se confirmó: se avisa y
      // se vuelven a pedir los turnos con la misma preferencia.
      if (error?.codigo === 'turno_ocupado') {
        const { pedido } = eleccion
        setEleccion(null)
        setTurnos((previos) => [
          ...previos,
          { tipo: 'aviso', texto: 'Ese horario se acaba de ocupar. Estos son los que quedan.' },
        ])
        void buscarTurnos(pedido)
        return
      }
      setErrorReserva(error)
    } finally {
      setReservando(false)
    }
  }

  const alEnviar = (evento: FormEvent) => {
    evento.preventDefault()
    void enviar()
  }

  // Enter envía y Shift+Enter baja de línea: es lo que espera cualquiera que
  // haya usado un chat. `isComposing` evita mandar a medio escribir una tilde
  // con teclado de composición.
  const alPresionar = (evento: KeyboardEvent<HTMLTextAreaElement>) => {
    if (evento.key === 'Enter' && !evento.shiftKey && !evento.nativeEvent.isComposing) {
      evento.preventDefault()
      void enviar()
    }
  }

  return (
    <div className="flex h-[calc(100dvh-3.5rem)] flex-col md:h-dvh">
      <header className="border-tinta-200 dark:border-tinta-800 shrink-0 border-b bg-white/70 px-5 py-4 backdrop-blur dark:bg-tinta-900/40">
        <div className="mx-auto max-w-3xl">
          <h1 className="text-tinta-900 dark:text-tinta-50 text-lg font-semibold tracking-tight">
            Asistente de orientación
          </h1>
          <p className="text-tinta-500 mt-0.5 text-sm">
            Te orienta sobre qué especialidad consultar y responde dudas de
            horarios, sedes y precios. No reemplaza la consulta médica.
          </p>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto" aria-live="polite">
        <div className="mx-auto max-w-3xl space-y-4 px-5 py-6">
          {turnos.length === 0 && !esperando && (
            <Bienvenida
              alElegir={(ejemplo) => {
                setEntrada(ejemplo)
                casilla.current?.focus()
              }}
            />
          )}

          {turnos.map((turno, i) => {
            if (turno.tipo === 'paciente') {
              return <BurbujaPaciente key={i} texto={turno.texto} />
            }
            if (turno.tipo === 'error') {
              const { pedido } = turno
              return (
                <BurbujaError
                  key={i}
                  motivo={turno.motivo}
                  alReintentar={
                    esperando
                      ? undefined
                      : pedido
                        ? () => reintentarTurnos(pedido)
                        : () => void enviar(turno.texto)
                  }
                />
              )
            }
            if (turno.tipo === 'turnos') {
              return (
                <BurbujaTurnos
                  key={i}
                  respuesta={turno.respuesta}
                  ocupado={esperando}
                  alElegir={(elegido) => {
                    setErrorReserva(null)
                    setEleccion({ turno: elegido, pedido: turno.pedido })
                  }}
                  alPedirOtro={(preferencia) =>
                    void buscarTurnos(
                      { especialidad: turno.pedido.especialidad, preferencia },
                      undefined,
                      preferencia,
                    )
                  }
                />
              )
            }
            if (turno.tipo === 'reservada') {
              return <BurbujaReservada key={i} ficha={turno.ficha} />
            }
            if (turno.tipo === 'aviso') {
              return (
                <Burbuja key={i}>
                  <p className="text-espera-700 dark:text-espera-200 text-sm">{turno.texto}</p>
                </Burbuja>
              )
            }
            const especialidadReservable = turno.respuesta.booking?.available
              && !turno.respuesta.booking.booking_intent
              ? turno.respuesta.booking.specialty
              : null
            return (
              <BurbujaAsistente
                key={i}
                respuesta={turno.respuesta}
                ocupado={esperando}
                alVerHorarios={
                  especialidadReservable
                    ? () =>
                        void buscarTurnos(
                          { especialidad: especialidadReservable, preferencia: '' },
                          undefined,
                          `Ver horarios de ${especialidadReservable.name}`,
                        )
                    : undefined
                }
              />
            )
          })}

          {esperando && <Pensando />}

          <div ref={fondo} />
        </div>
      </div>

      <form
        onSubmit={alEnviar}
        className="border-tinta-200 dark:border-tinta-800 shrink-0 border-t bg-white px-5 py-3 dark:bg-tinta-900/60"
      >
        <div className="mx-auto flex max-w-3xl items-end gap-2">
          <label htmlFor="pregunta" className="sr-only">
            Escribe tu consulta para el asistente
          </label>
          <textarea
            id="pregunta"
            ref={casilla}
            rows={1}
            maxLength={LARGO_MAXIMO}
            value={entrada}
            onChange={(e) => setEntrada(e.target.value)}
            onKeyDown={alPresionar}
            disabled={esperando}
            placeholder="Tus síntomas, o un horario o precio…"
            className="border-tinta-300 dark:border-tinta-700 focus:border-marca-500 focus:ring-marca-500/25 placeholder:text-tinta-400 dark:bg-tinta-900/60 dark:text-tinta-50 disabled:bg-tinta-100 dark:disabled:bg-tinta-900 max-h-40 min-h-11 flex-1 resize-none rounded-xl border bg-white px-3.5 py-2.5 text-[0.9375rem] [field-sizing:content] focus:ring-4 focus:outline-none"
          />
          <button
            type="submit"
            disabled={esperando || !entrada.trim()}
            aria-label="Enviar"
            title="Enviar"
            className="bg-marca-600 hover:bg-marca-700 focus-visible:outline-marca-500 grid size-11 shrink-0 place-items-center rounded-xl text-white transition focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-50"
          >
            <IconoEnviar />
          </button>
        </div>
        {entrada.length > LARGO_MAXIMO * 0.8 && (
          <p className="text-tinta-500 mx-auto mt-1 max-w-3xl text-right text-xs tabular-nums">
            {entrada.length}/{LARGO_MAXIMO}
          </p>
        )}
      </form>

      <ModalReservarFicha
        abierto={eleccion !== null}
        slot={eleccion?.turno ?? null}
        practitionerName={eleccion?.turno.practitioner.full_name ?? ''}
        reservando={reservando}
        errorReserva={errorReserva}
        onCerrar={cerrarModal}
        onConfirmar={confirmarReserva}
      />
    </div>
  )
}

/** Una derivación que llegó por `slots/`, con la forma de la de `suggest/`. */
function derivacion(mensaje: string): RespuestaAsistente {
  return {
    emergency: true,
    answer: mensaje,
    generated_by: 'regla',
    specialty: null,
    alternatives: [],
    fragments: [],
  }
}

function motivoDelFallo(fallo: unknown): string {
  if (!(fallo instanceof ErrorApi)) {
    return 'El servidor respondió algo que no se pudo interpretar.'
  }
  if (fallo.codigo === 'sin_conexion') return 'No hay conexión con el servidor.'
  if (fallo.estado === 404) {
    return 'El asistente todavía no está disponible en este servidor.'
  }
  // El 503 trae en `detail` el error técnico del proveedor de embeddings, que
  // no le sirve de nada a un paciente.
  if (fallo.estado >= 500) return 'El asistente no está disponible en este momento.'
  return fallo.message
}

// ---------------------------------------------------------------------------

function Bienvenida({ alElegir }: { alElegir: (ejemplo: string) => void }) {
  return (
    <div className="surgir py-10 text-center">
      <div className="bg-marca-50 text-marca-600 dark:bg-marca-950 dark:text-marca-400 mx-auto grid size-14 place-items-center rounded-2xl">
        <IconoConversacion />
      </div>
      <p className="text-tinta-700 dark:text-tinta-200 mx-auto mt-4 max-w-md text-[0.9375rem]">
        Describe tus síntomas y te sugiero con qué especialidad consultar.
      </p>
      <p className="text-tinta-500 mx-auto mt-2 max-w-md text-sm">
        También puedes preguntarme horarios y direcciones de las sucursales,
        precios de consultas y estudios, cómo prepararte o cómo cancelar una
        ficha.
      </p>
      <p className="text-tinta-400 mt-6 text-xs font-semibold tracking-wider uppercase">
        Por ejemplo
      </p>
      <ul className="mt-3 flex flex-wrap justify-center gap-2">
        {EJEMPLOS.map((ejemplo) => (
          <li key={ejemplo}>
            <button
              type="button"
              onClick={() => alElegir(ejemplo)}
              className="border-tinta-200 text-tinta-600 hover:border-marca-300 hover:bg-marca-50 hover:text-marca-700 dark:border-tinta-700 dark:text-tinta-300 dark:hover:bg-marca-950/40 rounded-full border px-3.5 py-1.5 text-sm transition"
            >
              {ejemplo}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

function BurbujaPaciente({ texto }: { texto: string }) {
  return (
    <div className="flex justify-end">
      <p className="bg-marca-600 max-w-[85%] rounded-2xl rounded-br-md px-4 py-2.5 text-[0.9375rem] whitespace-pre-wrap text-white">
        {texto}
      </p>
    </div>
  )
}

function Burbuja({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex justify-start">
      <div className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/60 max-w-[85%] space-y-3 rounded-2xl rounded-bl-md border bg-white px-4 py-3 text-[0.9375rem]">
        {children}
      </div>
    </div>
  )
}

function BurbujaAsistente({
  respuesta,
  alVerHorarios,
  ocupado,
}: {
  respuesta: RespuestaAsistente
  /** US-33: sólo cuando se puede reservar y la pregunta no lo pidió ya. */
  alVerHorarios?: () => void
  ocupado: boolean
}) {
  const { puede } = useSesion()

  if (respuesta.emergency) return <AlertaEmergencia mensaje={respuesta.answer} />

  const especialidad = respuesta.specialty

  return (
    <Burbuja>
      {respuesta.answer && (
        <p className="text-tinta-800 dark:text-tinta-100 whitespace-pre-wrap">
          {respuesta.answer}
        </p>
      )}

      {especialidad && (
        <div className="bg-marca-50 dark:bg-marca-950/40 flex flex-wrap items-center justify-between gap-3 rounded-xl px-3.5 py-3">
          <div>
            <p className="text-marca-700 dark:text-marca-400 text-xs font-medium">
              Especialidad sugerida
            </p>
            <p className="text-tinta-900 dark:text-tinta-50 font-semibold">
              {especialidad.name}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {alVerHorarios && (
              <button
                type="button"
                onClick={alVerHorarios}
                disabled={ocupado}
                className="bg-marca-600 hover:bg-marca-700 rounded-lg px-3 py-1.5 text-sm font-semibold text-white transition disabled:opacity-50"
              >
                Ver horarios
              </button>
            )}
            {puede('catalog.professional.read') && (
              <Link
                to={`/buscar-profesionales?especialidad=${encodeURIComponent(especialidad.id)}`}
                className={
                  alVerHorarios
                    ? 'border-marca-300 text-marca-700 hover:bg-marca-100 dark:border-marca-800 dark:text-marca-300 dark:hover:bg-marca-950 rounded-lg border px-3 py-1.5 text-sm font-semibold transition'
                    : 'bg-marca-600 hover:bg-marca-700 rounded-lg px-3 py-1.5 text-sm font-semibold text-white transition'
                }
              >
                Ver profesionales
              </Link>
            )}
          </div>
        </div>
      )}

      {/* US-33: consulta administrativa que pedía reservar ("quiero un turno
          de cardiología"): no hay tarjeta de especialidad, pero sí horarios. */}
      {!especialidad && alVerHorarios && (
        <button
          type="button"
          onClick={alVerHorarios}
          disabled={ocupado}
          className="text-marca-600 dark:text-marca-400 text-sm font-semibold hover:underline disabled:opacity-50"
        >
          Ver horarios de {respuesta.booking?.specialty?.name}
        </button>
      )}

      {respuesta.alternatives.length > 0 && (
        <p className="text-tinta-500 text-sm">
          También podría ser:{' '}
          {respuesta.alternatives.map((alternativa) => alternativa.name).join(' · ')}
        </p>
      )}

      {respuesta.fragments.length > 0 && (
        <details className="group">
          <summary className="text-tinta-500 hover:text-tinta-700 dark:hover:text-tinta-300 cursor-pointer text-sm select-none">
            {respuesta.kind === 'administrativa' ? 'De dónde sale' : 'En qué se basa'}{' '}
            ({respuesta.fragments.length})
          </summary>
          <ul className="mt-2 space-y-2">
            {respuesta.fragments.map((fragmento) => (
              <li
                key={fragmento.id}
                className="border-marca-300 dark:border-marca-800 border-l-2 pl-3 text-sm"
              >
                <p className="text-tinta-700 dark:text-tinta-200">{fragmento.text}</p>
                <p className="text-tinta-400 mt-0.5 text-xs">
                  {fragmento.source_name} · similitud{' '}
                  <span className="tabular-nums">
                    {Math.round(fragmento.similarity * 100)}%
                  </span>
                </p>
              </li>
            ))}
          </ul>
        </details>
      )}
    </Burbuja>
  )
}

function fechaYHora(iso: string): string {
  return new Date(iso).toLocaleString('es-BO', {
    weekday: 'short', day: 'numeric', month: 'short',
    hour: '2-digit', minute: '2-digit',
  })
}

/**
 * US-33 — Los turnos ofrecidos. Cada uno es un botón que abre el modal de
 * confirmación: tocarlo no reserva nada.
 */
function BurbujaTurnos({
  respuesta,
  ocupado,
  alElegir,
  alPedirOtro,
}: {
  respuesta: OfertaDeTurnos
  ocupado: boolean
  alElegir: (turno: TurnoOfrecido) => void
  alPedirOtro: (preferencia: string) => void
}) {
  const [otro, setOtro] = useState('')
  const idCampo = useId()

  const pedirOtro = (evento: FormEvent) => {
    evento.preventDefault()
    const texto = otro.trim()
    if (!texto || ocupado) return
    setOtro('')
    alPedirOtro(texto)
  }

  return (
    <Burbuja>
      <p
        className={
          respuesta.matched_preference
            ? 'text-tinta-800 dark:text-tinta-100'
            : 'text-espera-700 dark:text-espera-200'
        }
      >
        {respuesta.answer}
      </p>

      {respuesta.offers.length > 0 && (
        <ul className="grid gap-2 sm:grid-cols-2">
          {respuesta.offers.map((turno) => (
            <li key={`${turno.schedule.id}-${turno.start}`}>
              <button
                type="button"
                onClick={() => alElegir(turno)}
                className="border-tinta-200 hover:border-marca-400 hover:bg-marca-50 dark:border-tinta-700 dark:hover:border-marca-700 dark:hover:bg-marca-950/40 w-full rounded-xl border px-3 py-2.5 text-left transition"
              >
                <span className="text-tinta-900 dark:text-tinta-50 block font-semibold capitalize">
                  {fechaYHora(turno.start)}
                </span>
                <span className="text-tinta-600 dark:text-tinta-300 block text-sm">
                  {turno.practitioner.full_name}
                </span>
                <span className="text-tinta-400 block text-xs">{turno.branch.name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="space-y-2">
        <p className="text-tinta-500 text-xs">¿Otro día u horario?</p>
        <div className="flex flex-wrap gap-1.5">
          {PREFERENCIAS_RAPIDAS.map((preferencia) => (
            <button
              key={preferencia}
              type="button"
              onClick={() => alPedirOtro(preferencia)}
              disabled={ocupado}
              className="border-tinta-200 text-tinta-600 hover:border-marca-300 hover:bg-marca-50 hover:text-marca-700 dark:border-tinta-700 dark:text-tinta-300 dark:hover:bg-marca-950/40 rounded-full border px-3 py-1 text-xs transition disabled:opacity-50"
            >
              {preferencia}
            </button>
          ))}
        </div>
        <form onSubmit={pedirOtro} className="flex gap-2">
          <label className="sr-only" htmlFor={idCampo}>
            Otro día u horario
          </label>
          <input
            id={idCampo}
            value={otro}
            onChange={(e) => setOtro(e.target.value)}
            maxLength={200}
            disabled={ocupado}
            placeholder="Ej.: el jueves por la tarde"
            className="border-tinta-300 dark:border-tinta-700 focus:border-marca-500 dark:bg-tinta-900/60 min-w-0 flex-1 rounded-lg border bg-white px-3 py-1.5 text-sm focus:outline-none"
          />
          <button
            type="submit"
            disabled={ocupado || !otro.trim()}
            className="text-marca-600 dark:text-marca-400 text-sm font-semibold disabled:opacity-50"
          >
            Buscar
          </button>
        </form>
      </div>
    </Burbuja>
  )
}

/** US-33 — La ficha quedó reservada, pendiente de pago, como por la pantalla. */
function BurbujaReservada({ ficha }: { ficha: Ficha }) {
  return (
    <Burbuja>
      <div className="bg-marca-50 dark:bg-marca-950/40 rounded-xl px-3.5 py-3">
        <p className="text-marca-700 dark:text-marca-400 text-xs font-medium">Ficha reservada</p>
        <p className="text-tinta-900 dark:text-tinta-50 font-semibold capitalize">
          {fechaYHora(ficha.starts_at)}
        </p>
        <p className="text-tinta-600 dark:text-tinta-300 text-sm">
          {ficha.practitioner_name} · {ficha.branch_name}
        </p>
        <p className="text-tinta-500 text-sm">Para {ficha.patient_name}</p>
      </div>
      <p className="text-tinta-700 dark:text-tinta-200 text-sm">
        Queda pendiente de pago. Págala desde tus fichas para confirmarla.
      </p>
      <Link
        to="/mis-fichas"
        className="bg-marca-600 hover:bg-marca-700 inline-block rounded-lg px-3 py-1.5 text-sm font-semibold text-white transition"
      >
        Ir a mis fichas
      </Link>
    </Burbuja>
  )
}

/**
 * US-34. Sin especialidad, sin fragmentos y sin botón de reservar: lo único
 * que tiene que leer la persona es que vaya a emergencias. El texto de abajo
 * es el de `triage.py`, el mismo para las dos capas de la barrera.
 */
function AlertaEmergencia({ mensaje }: { mensaje: string }) {
  return (
    <div
      role="alert"
      className="border-alerta-200 bg-alerta-50 text-alerta-700 dark:border-alerta-500/40 dark:bg-alerta-500/10 dark:text-alerta-200 surgir rounded-2xl border-2 p-4"
    >
      <div className="flex gap-3">
        <IconoAlerta className="mt-0.5 size-6 shrink-0" />
        <div className="space-y-1.5">
          <p className="font-semibold">
            Esto puede ser una urgencia. No esperes una ficha: acude ya a un
            servicio de emergencias o llama a una ambulancia.
          </p>
          {mensaje && <p className="text-sm">{mensaje}</p>}
        </div>
      </div>
    </div>
  )
}

function BurbujaError({
  motivo,
  alReintentar,
}: {
  motivo: string
  alReintentar?: () => void
}) {
  return (
    <Burbuja>
      <div>
        <p className="text-tinta-900 dark:text-tinta-50 font-semibold">
          No puedo responder ahora.
        </p>
        <p className="text-tinta-500 mt-0.5 text-sm">{motivo}</p>
      </div>
      <button
        type="button"
        onClick={alReintentar}
        disabled={!alReintentar}
        className="text-marca-600 dark:text-marca-400 text-sm font-semibold hover:underline disabled:opacity-50"
      >
        Reintentar
      </button>
    </Burbuja>
  )
}

function Pensando() {
  return (
    <Burbuja>
      <p className="text-tinta-500 flex items-center gap-2 text-sm" role="status">
        <svg className="size-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
          <path className="opacity-90" fill="currentColor" d="M12 2a10 10 0 0 1 10 10h-3a7 7 0 0 0-7-7V2Z" />
        </svg>
        Pensando…
      </p>
    </Burbuja>
  )
}

function IconoEnviar() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="size-5"
      aria-hidden="true"
    >
      <path d="M4 12 20 4l-6 16-3-7-7-1Z" />
    </svg>
  )
}

function IconoConversacion() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="size-7"
      aria-hidden="true"
    >
      <path d="M4 5h16v10H9l-5 4V5Z" />
      <path d="M8 9h8M8 12h5" />
    </svg>
  )
}
