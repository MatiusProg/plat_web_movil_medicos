/**
 * Mis fichas: pagar (US-18), ver el comprobante (US-19), confirmar la
 * asistencia (US-21), cancelar o reprogramar (US-20).
 *
 * **La web nunca da una ficha por pagada.** "Pagar" abre el checkout de Stripe
 * y, al volver (`?ficha=…&pago=pagado`), la pantalla vuelve a pedir las fichas
 * hasta que el backend diga `confirmed`: quien confirma es el webhook firmado
 * de Stripe (regla 10 del Sprint 2). Lo mismo con la devolución: sólo se
 * muestra `refund_eligible`, nunca se calcula acá.
 */

import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import type { Espacio } from '@/api/disponibilidad'
import {
  cancelarFicha, confirmarAsistencia, ETIQUETA_ESTADO_FICHA as ETIQUETA_ESTADO, iniciarPago,
  misFichas, reprogramarFicha, type Ficha,
} from '@/api/fichas'
import {
  miListaDeEspera, salirDeListaDeEspera, type EntradaEspera,
} from '@/api/listaEspera'
import { ErrorApi } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { ModalComprobante } from '@/componentes/ModalComprobante'
import { ModalReprogramarFicha } from '@/componentes/ModalReprogramarFicha'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'

const COLOR_ESTADO: Record<Ficha['status'], string> = {
  pending_payment: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
  confirmed: 'bg-marca-50 text-marca-700 dark:bg-marca-950/40 dark:text-marca-300',
  attended: 'bg-tinta-100 text-tinta-600 dark:bg-tinta-800 dark:text-tinta-300',
  cancelled: 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300',
  rescheduled: 'bg-tinta-100 text-tinta-500 dark:bg-tinta-800 dark:text-tinta-400',
  expired: 'bg-tinta-100 text-tinta-500 dark:bg-tinta-800 dark:text-tinta-400',
  no_show: 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300',
}

const ACCIONABLES: Ficha['status'][] = ['pending_payment', 'confirmed']

// Al volver de Stripe, cada cuánto y hasta cuándo se vuelve a pedir la ficha
// esperando el webhook. En general llega en unos segundos.
const ESPERA_PAGO_MS = 3000
const ESPERA_PAGO_INTENTOS = 20

function importe(ficha: Ficha): string {
  const moneda = ficha.fee.currency === 'BOB' ? 'Bs' : ficha.fee.currency
  return `${moneda} ${Number(ficha.fee.amount).toFixed(2)}`
}

function fechaYHora(iso: string): string {
  return new Date(iso).toLocaleString('es-BO', {
    weekday: 'long', day: 'numeric', month: 'long',
    hour: '2-digit', minute: '2-digit',
  })
}

/** `YYYY-MM-DD` a `DD/MM/AAAA`, sin pasar por `Date` para no correr el día. */
function fechaCorta(iso: string): string {
  const [anio, mes, dia] = iso.split('-')
  return `${dia}/${mes}/${anio}`
}

function segundosHasta(iso: string): number {
  return Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 1000) || 0)
}

/**
 * US-52 — Cuenta regresiva en vivo hasta que vence el cupo liberado. Al llegar
 * a cero avisa una sola vez, para que la pantalla vuelva a pedir las fichas.
 */
function CuentaRegresivaCupo({ hasta, alVencer }: { hasta: string; alVencer: () => void }) {
  const [restante, setRestante] = useState(() => segundosHasta(hasta))
  const alVencerRef = useRef(alVencer)
  useEffect(() => { alVencerRef.current = alVencer })

  useEffect(() => {
    const reloj = window.setInterval(() => {
      const quedan = segundosHasta(hasta)
      setRestante(quedan)
      if (quedan <= 0) {
        window.clearInterval(reloj)
        alVencerRef.current()
      }
    }, 1000)
    return () => window.clearInterval(reloj)
  }, [hasta])

  const minutos = Math.floor(restante / 60)
  const segundos = restante % 60
  return (
    <span role="timer" aria-label="Tiempo que queda para pagar" className="font-semibold tabular-nums">
      {String(minutos).padStart(2, '0')}:{String(segundos).padStart(2, '0')}
    </span>
  )
}

export function MisFichas() {
  const { token } = useSesion()
  useTitulo('Mis fichas')

  const [fichas, setFichas] = useState<Ficha[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<ErrorApi | null>(null)
  const [recargaClave, setRecargaClave] = useState(0)

  // US-52: la lista de espera. `enabled` es falso si el plan no la incluye.
  const [listaEspera, setListaEspera] = useState<{ enabled: boolean; entradas: EntradaEspera[] }>(
    { enabled: false, entradas: [] },
  )
  const [saliendoId, setSaliendoId] = useState<string | null>(null)

  const [cancelandoId, setCancelandoId] = useState<string | null>(null)
  const [avisoCancelacion, setAvisoCancelacion] = useState<string | null>(null)

  const [parametros, setParametros] = useSearchParams()
  const fichaPagada = parametros.get('pago') === 'pagado' ? parametros.get('ficha') : null
  const [esperandoPago, setEsperandoPago] = useState(fichaPagada !== null)
  const [intentos, setIntentos] = useState(0)
  const [pagandoId, setPagandoId] = useState<string | null>(null)
  const [confirmandoId, setConfirmandoId] = useState<string | null>(null)
  const [comprobanteId, setComprobanteId] = useState<string | null>(null)

  const [fichaAReprogramar, setFichaAReprogramar] = useState<Ficha | null>(null)
  const [reprogramando, setReprogramando] = useState(false)
  const [errorReprogramar, setErrorReprogramar] = useState<ErrorApi | null>(null)

  useEffect(() => {
    const control = new AbortController()
    setCargando(true)
    setError(null)
    misFichas({ token }, control.signal)
      .then(setFichas)
      .catch((fallo: unknown) => {
        if (fallo instanceof DOMException && fallo.name === 'AbortError') return
        setError(fallo instanceof ErrorApi ? fallo : null)
      })
      .finally(() => setCargando(false))
    return () => control.abort()
  }, [token, recargaClave])

  // La lista de espera va aparte: si falla, el resto de la pantalla sigue igual.
  useEffect(() => {
    const control = new AbortController()
    miListaDeEspera({ token }, control.signal)
      .then((r) => setListaEspera({ enabled: r.enabled, entradas: r.results }))
      .catch((fallo: unknown) => {
        if (fallo instanceof DOMException && fallo.name === 'AbortError') return
        setListaEspera({ enabled: false, entradas: [] })
      })
    return () => control.abort()
  }, [token, recargaClave])

  // Vuelta de Stripe: un aviso para el pago cancelado, y para el pagado, una
  // espera hasta que el webhook confirme la ficha.
  useEffect(() => {
    if (parametros.get('pago') === 'cancelado') {
      setAvisoCancelacion('Pago cancelado: no se cobró nada. Podés intentarlo de nuevo.')
      setParametros({}, { replace: true })
    }
  }, [parametros, setParametros])

  useEffect(() => {
    if (!esperandoPago || !fichaPagada || cargando) return
    const ficha = fichas.find((f) => f.id === fichaPagada)
    if (ficha && ficha.status !== 'pending_payment') {
      setEsperandoPago(false)
      setAvisoCancelacion(
        ficha.status === 'confirmed'
          ? 'Pago confirmado. Tu ficha está confirmada: ya podés ver el comprobante.'
          : 'El pago llegó, pero la ficha ya no estaba disponible: se devolvió el importe.',
      )
      setParametros({}, { replace: true })
      return
    }
    if (intentos >= ESPERA_PAGO_INTENTOS) {
      setEsperandoPago(false)
      setAvisoCancelacion(
        'Todavía no recibimos la confirmación del pago. Actualizá la página en unos minutos.',
      )
      return
    }
    const espera = window.setTimeout(() => {
      setIntentos((n) => n + 1)
      setRecargaClave((clave) => clave + 1)
    }, ESPERA_PAGO_MS)
    return () => window.clearTimeout(espera)
  }, [esperandoPago, fichaPagada, fichas, cargando, intentos, setParametros])

  const pagar = async (ficha: Ficha) => {
    setPagandoId(ficha.id)
    setError(null)
    try {
      const sesion = await iniciarPago(ficha.id, { token })
      // Se sale de la web hacia Stripe; Stripe vuelve a esta misma pantalla.
      window.location.assign(sesion.checkout_url)
    } catch (fallo: unknown) {
      setError(fallo instanceof ErrorApi ? fallo : null)
      setPagandoId(null)
    }
  }

  const salirDeLaLista = async (entrada: EntradaEspera) => {
    if (!window.confirm('¿Salir de la lista de espera? Perderás tu lugar en la fila.')) return
    setSaliendoId(entrada.id)
    setError(null)
    try {
      await salirDeListaDeEspera(entrada.id, { token })
      setAvisoCancelacion('Saliste de la lista de espera.')
      setRecargaClave((clave) => clave + 1)
    } catch (fallo: unknown) {
      setError(fallo instanceof ErrorApi ? fallo : null)
    } finally {
      setSaliendoId(null)
    }
  }

  const confirmar = async (ficha: Ficha) => {
    setConfirmandoId(ficha.id)
    setError(null)
    try {
      await confirmarAsistencia(ficha.id, { token })
      setAvisoCancelacion('Asistencia confirmada. ¡Te esperamos!')
      setRecargaClave((clave) => clave + 1)
    } catch (fallo: unknown) {
      setError(fallo instanceof ErrorApi ? fallo : null)
    } finally {
      setConfirmandoId(null)
    }
  }

  const cancelar = async (ficha: Ficha) => {
    const pagada = ficha.payment_status === 'succeeded'
    if (!window.confirm(
      `¿Cancelar la ficha del ${fechaYHora(ficha.starts_at)}?`
      + (pagada
        ? '\n\nSi cancelás dentro del plazo de anticipación se te devuelve el pago; fuera de plazo, no.'
        : ''),
    )) return
    setCancelandoId(ficha.id)
    setError(null)
    try {
      const actualizada = await cancelarFicha(ficha.id, { token })
      setAvisoCancelacion(
        actualizada.payment_status === 'refunded'
          ? 'Ficha cancelada. Se devolvió el pago.'
          : actualizada.refund_eligible
            ? 'Ficha cancelada. Corresponde devolución.'
            : 'Ficha cancelada. Fuera del plazo de anticipación: no corresponde devolución.',
      )
      setRecargaClave((clave) => clave + 1)
    } catch (fallo: unknown) {
      setError(fallo instanceof ErrorApi ? fallo : null)
    } finally {
      setCancelandoId(null)
    }
  }

  const confirmarReprogramacion = async (slot: Espacio) => {
    if (!fichaAReprogramar) return
    setReprogramando(true)
    setErrorReprogramar(null)
    try {
      await reprogramarFicha(
        fichaAReprogramar.id,
        { branch: slot.branch.id, schedule: slot.schedule.id, startsAt: slot.start },
        { token },
      )
      setFichaAReprogramar(null)
      setAvisoCancelacion('Ficha reprogramada.')
      setRecargaClave((clave) => clave + 1)
    } catch (fallo: unknown) {
      setErrorReprogramar(fallo instanceof ErrorApi ? fallo : null)
    } finally {
      setReprogramando(false)
    }
  }

  return (
    <main className="mx-auto max-w-3xl space-y-6 px-5 py-10">
      <div className="surgir">
        <p className="text-marca-700 dark:text-marca-400 text-sm font-medium">
          Mis fichas
        </p>
        <h1 className="text-tinta-900 dark:text-tinta-50 mt-1 text-2xl font-semibold tracking-tight">
          Reservas
        </h1>
        <p className="text-tinta-500 mt-1.5 text-[1.0625rem]">
          Pagá tu reserva para confirmarla, mostrá el comprobante en recepción y
          confirmá que vas a asistir. Cancelá o reprogramá dentro del plazo de
          anticipación de tu centro médico: fuera de plazo, la cancelación no da
          derecho a devolución.
        </p>
      </div>

      {error && <Aviso codigo={error.codigo} mensaje={error.message} />}
      {esperandoPago && (
        <div
          role="status"
          className="rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-3 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300"
        >
          Pago recibido. Esperando la confirmación del procesador de pagos…
        </div>
      )}
      {avisoCancelacion && (
        <div
          role="status"
          className="border-marca-200 bg-marca-50 text-marca-700 dark:border-marca-900 dark:bg-marca-950/40 dark:text-marca-300 rounded-xl border px-3.5 py-3 text-sm"
        >
          {avisoCancelacion}
        </div>
      )}

      {cargando ? (
        <p className="text-tinta-500 text-[1.0625rem]">Cargando…</p>
      ) : fichas.length === 0 ? (
        <p className="text-tinta-500 text-[1.0625rem]">
          Todavía no reservaste ninguna ficha.
        </p>
      ) : (
        <div className="space-y-3">
          {fichas.map((ficha) => {
            const deListaDeEspera = listaEspera.entradas.some(
              (e) => e.offered_appointment === ficha.id,
            )
            const futura = new Date(ficha.starts_at).getTime() > Date.now()
            const accionable = ACCIONABLES.includes(ficha.status) && futura
            const pendiente = ficha.status === 'pending_payment' && futura
              && (!ficha.expires_at || new Date(ficha.expires_at).getTime() > Date.now())
            const conComprobante = ficha.status === 'confirmed' || ficha.status === 'attended'
            const puedeConfirmar = ficha.status === 'confirmed' && futura
              && !ficha.attendance_confirmed_at
            return (
              <div
                key={ficha.id}
                className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 rounded-2xl border bg-white p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-tinta-900 dark:text-tinta-50 font-semibold capitalize">
                      {fechaYHora(ficha.starts_at)}
                    </p>
                    <p className="text-tinta-500 mt-0.5 text-sm">
                      {ficha.practitioner_name} · {ficha.branch_name}
                    </p>
                    <p className="text-tinta-400 mt-0.5 text-xs">
                      Para {ficha.patient_name}
                    </p>
                  </div>
                  <span
                    className={`rounded-md px-2 py-1 text-xs font-medium ${COLOR_ESTADO[ficha.status]}`}
                  >
                    {ETIQUETA_ESTADO[ficha.status]}
                  </span>
                </div>

                {pendiente && deListaDeEspera && (
                  <div
                    role="status"
                    className="border-marca-200 bg-marca-50 text-marca-700 dark:border-marca-900 dark:bg-marca-950/40 dark:text-marca-300 mt-3 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 rounded-xl border px-3 py-2 text-sm"
                  >
                    <span className="font-semibold">Cupo liberado para ti</span>
                    {ficha.expires_at && (
                      <span>
                        Te lo guardamos por{' '}
                        <CuentaRegresivaCupo
                          hasta={ficha.expires_at}
                          alVencer={() => setRecargaClave((clave) => clave + 1)}
                        />
                      </span>
                    )}
                  </div>
                )}
                {pendiente && (
                  <p className="text-tinta-500 mt-2 text-xs">
                    Pagá {importe(ficha)} para confirmarla
                    {ficha.expires_at && (
                      <> antes de las {new Date(ficha.expires_at).toLocaleTimeString('es-BO', {
                        hour: '2-digit', minute: '2-digit',
                      })}</>
                    )}
                    : pasado ese momento el turno se libera.
                  </p>
                )}
                {ficha.attendance_confirmed_at && ficha.status === 'confirmed' && (
                  <p className="text-marca-700 dark:text-marca-400 mt-2 text-xs font-medium">
                    ✓ Confirmaste tu asistencia
                  </p>
                )}

                {(accionable || conComprobante) && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {pendiente && (
                      <button
                        type="button"
                        onClick={() => pagar(ficha)}
                        disabled={pagandoId === ficha.id}
                        className="bg-marca-600 hover:bg-marca-700 rounded-xl px-3 py-1.5 text-sm font-semibold text-white transition disabled:opacity-50"
                      >
                        {pagandoId === ficha.id ? 'Abriendo el pago…' : `Pagar ${importe(ficha)}`}
                      </button>
                    )}
                    {conComprobante && (
                      <button
                        type="button"
                        onClick={() => setComprobanteId(ficha.id)}
                        className="border-marca-300 text-marca-700 dark:border-marca-800 dark:text-marca-300 hover:bg-marca-50 dark:hover:bg-marca-950/40 rounded-xl border px-3 py-1.5 text-sm font-semibold transition"
                      >
                        Ver comprobante
                      </button>
                    )}
                    {puedeConfirmar && (
                      <button
                        type="button"
                        onClick={() => confirmar(ficha)}
                        disabled={confirmandoId === ficha.id}
                        className="border-marca-300 text-marca-700 dark:border-marca-800 dark:text-marca-300 hover:bg-marca-50 dark:hover:bg-marca-950/40 rounded-xl border px-3 py-1.5 text-sm font-semibold transition disabled:opacity-50"
                      >
                        {confirmandoId === ficha.id ? 'Confirmando…' : 'Confirmar asistencia'}
                      </button>
                    )}
                    {accionable && (
                      <>
                    <button
                      type="button"
                      onClick={() => setFichaAReprogramar(ficha)}
                      className="border-tinta-300 dark:border-tinta-700 text-tinta-600 dark:text-tinta-300 hover:bg-tinta-100 dark:hover:bg-tinta-800 rounded-xl border px-3 py-1.5 text-sm font-semibold transition"
                    >
                      Reprogramar
                    </button>
                    <button
                      type="button"
                      onClick={() => cancelar(ficha)}
                      disabled={cancelandoId === ficha.id}
                      className="rounded-xl border border-red-300 px-3 py-1.5 text-sm font-semibold text-red-600 transition hover:bg-red-50 disabled:opacity-50 dark:border-red-900 dark:text-red-300 dark:hover:bg-red-950/40"
                    >
                      {cancelandoId === ficha.id ? 'Cancelando…' : 'Cancelar'}
                    </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {listaEspera.enabled && listaEspera.entradas.length > 0 && (
        <section aria-label="En lista de espera" className="space-y-3">
          <div>
            <h2 className="text-tinta-900 dark:text-tinta-50 text-lg font-semibold">
              En lista de espera
            </h2>
            <p className="text-tinta-500 mt-0.5 text-sm">
              Si alguien cancela, te guardamos el turno 15 minutos y te avisamos.
            </p>
          </div>
          {listaEspera.entradas.map((entrada) => (
            <div
              key={entrada.id}
              className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 rounded-2xl border bg-white p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-tinta-900 dark:text-tinta-50 font-semibold">
                    {entrada.practitioner_name
                      ?? (entrada.specialty_name
                        ? `Cualquier profesional de ${entrada.specialty_name}`
                        : 'Cualquier profesional')}
                  </p>
                  <p className="text-tinta-500 mt-0.5 text-sm">
                    Del {fechaCorta(entrada.date_from)} al {fechaCorta(entrada.date_to)}
                    {entrada.branch_name && <> · {entrada.branch_name}</>}
                  </p>
                  <p className="text-tinta-400 mt-0.5 text-xs">Para {entrada.patient_name}</p>
                </div>
                {entrada.status === 'offered' ? (
                  <span className="rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700 dark:bg-amber-950/40 dark:text-amber-300">
                    Turno ofrecido
                  </span>
                ) : (
                  entrada.position !== null && (
                    <span className="bg-tinta-100 text-tinta-600 dark:bg-tinta-800 dark:text-tinta-300 rounded-md px-2 py-1 text-xs font-medium">
                      Eres el N.º <span className="tabular-nums">{entrada.position}</span>
                    </span>
                  )
                )}
              </div>
              {entrada.status === 'offered' && (
                <p className="text-tinta-500 mt-2 text-xs">
                  Te guardamos un turno: míralo arriba en tus fichas y págalo para confirmarlo.
                </p>
              )}
              <div className="mt-3">
                <button
                  type="button"
                  onClick={() => salirDeLaLista(entrada)}
                  disabled={saliendoId === entrada.id}
                  className="border-tinta-300 dark:border-tinta-700 text-tinta-600 dark:text-tinta-300 hover:bg-tinta-100 dark:hover:bg-tinta-800 min-h-11 rounded-xl border px-3 py-1.5 text-sm font-semibold transition disabled:opacity-50 sm:min-h-0"
                >
                  {saliendoId === entrada.id ? 'Saliendo…' : 'Salir de la lista'}
                </button>
              </div>
            </div>
          ))}
        </section>
      )}

      <ModalComprobante
        fichaId={comprobanteId}
        onCerrar={() => setComprobanteId(null)}
      />

      <ModalReprogramarFicha
        abierto={fichaAReprogramar !== null}
        ficha={fichaAReprogramar}
        reprogramando={reprogramando}
        errorReprogramar={errorReprogramar}
        onCerrar={() => {
          if (reprogramando) return
          setFichaAReprogramar(null)
          setErrorReprogramar(null)
        }}
        onConfirmar={confirmarReprogramacion}
      />
    </main>
  )
}
