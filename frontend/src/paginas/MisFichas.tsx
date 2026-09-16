/**
 * US-20 — Mis fichas: cancelar o reprogramar.
 *
 * Dentro de la política de anticipación de la organización, que decide el
 * backend: acá sólo se muestra si la cancelación da derecho a devolución
 * (`refund_eligible`), nunca se calcula en el cliente (regla 10 del Sprint 2).
 */

import { useEffect, useState } from 'react'

import type { Espacio } from '@/api/disponibilidad'
import {
  cancelarFicha, misFichas, reprogramarFicha, type Ficha,
} from '@/api/fichas'
import { ErrorApi } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { ModalReprogramarFicha } from '@/componentes/ModalReprogramarFicha'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'

const ETIQUETA_ESTADO: Record<Ficha['status'], string> = {
  pending_payment: 'Pendiente de pago',
  confirmed: 'Confirmada',
  attended: 'Atendida',
  cancelled: 'Cancelada',
  rescheduled: 'Reprogramada',
  expired: 'Vencida',
  no_show: 'Ausente',
}

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

function fechaYHora(iso: string): string {
  return new Date(iso).toLocaleString('es-BO', {
    weekday: 'long', day: 'numeric', month: 'long',
    hour: '2-digit', minute: '2-digit',
  })
}

export function MisFichas() {
  const { token } = useSesion()
  useTitulo('Mis fichas')

  const [fichas, setFichas] = useState<Ficha[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<ErrorApi | null>(null)
  const [recargaClave, setRecargaClave] = useState(0)

  const [cancelandoId, setCancelandoId] = useState<string | null>(null)
  const [avisoCancelacion, setAvisoCancelacion] = useState<string | null>(null)

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

  const cancelar = async (ficha: Ficha) => {
    if (!window.confirm(
      `¿Cancelar la ficha del ${fechaYHora(ficha.starts_at)}?`,
    )) return
    setCancelandoId(ficha.id)
    setError(null)
    try {
      const actualizada = await cancelarFicha(ficha.id, { token })
      setAvisoCancelacion(
        actualizada.refund_eligible
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
        <p className="text-tinta-500 mt-1.5 text-[0.9375rem]">
          Cancelá o reprogramá dentro del plazo de anticipación de tu centro
          médico. Fuera de plazo, la cancelación no da derecho a devolución.
        </p>
      </div>

      {error && <Aviso codigo={error.codigo} mensaje={error.message} />}
      {avisoCancelacion && (
        <div
          role="status"
          className="border-marca-200 bg-marca-50 text-marca-700 dark:border-marca-900 dark:bg-marca-950/40 dark:text-marca-300 rounded-xl border px-3.5 py-3 text-sm"
        >
          {avisoCancelacion}
        </div>
      )}

      {cargando ? (
        <p className="text-tinta-500 text-[0.9375rem]">Cargando…</p>
      ) : fichas.length === 0 ? (
        <p className="text-tinta-500 text-[0.9375rem]">
          Todavía no reservaste ninguna ficha.
        </p>
      ) : (
        <div className="space-y-3">
          {fichas.map((ficha) => {
            const accionable = ACCIONABLES.includes(ficha.status)
              && new Date(ficha.starts_at).getTime() > Date.now()
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

                {accionable && (
                  <div className="mt-3 flex gap-2">
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
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

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
