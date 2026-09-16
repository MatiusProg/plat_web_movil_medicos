/**
 * US-20 — Elegir el nuevo horario al reprogramar una ficha.
 *
 * Reutiliza el mismo endpoint de disponibilidad de US-15 sobre el
 * profesional de la ficha: reprogramar es, para quien reserva, volver a
 * elegir un turno como en US-17. El backend hace el resto —liberar el viejo y
 * tomar el nuevo en una sola transacción—.
 */

import { useEffect, useState } from 'react'

import {
  disponibilidadConsolidada,
  type Disponibilidad as DatosDisponibilidad,
  type Espacio,
} from '@/api/disponibilidad'
import type { Ficha } from '@/api/fichas'
import { ErrorApi } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { Boton } from '@/componentes/Boton'
import { useSesion } from '@/sesion/useSesion'

interface Props {
  abierto: boolean
  ficha: Ficha | null
  reprogramando?: boolean
  errorReprogramar?: ErrorApi | null
  onCerrar: () => void
  onConfirmar: (slot: Espacio) => void | Promise<void>
}

function isoHoy(desplazamiento = 0): string {
  const fecha = new Date()
  fecha.setDate(fecha.getDate() + desplazamiento)
  return fecha.toISOString().slice(0, 10)
}

function fechaYHora(iso: string): string {
  return new Date(iso).toLocaleString('es-BO', {
    weekday: 'short', day: 'numeric', month: 'short',
    hour: '2-digit', minute: '2-digit',
  })
}

export function ModalReprogramarFicha({
  abierto, ficha, reprogramando = false, errorReprogramar = null,
  onCerrar, onConfirmar,
}: Props) {
  const { token } = useSesion()
  const [datos, setDatos] = useState<DatosDisponibilidad | null>(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState<ErrorApi | null>(null)
  const [slotElegido, setSlotElegido] = useState<Espacio | null>(null)

  useEffect(() => {
    if (!abierto || !ficha) return
    setCargando(true)
    setError(null)
    setSlotElegido(null)
    const control = new AbortController()
    disponibilidadConsolidada(
      { practitioner: ficha.practitioner, from: isoHoy(), to: isoHoy(14) },
      { token },
      control.signal,
    )
      .then(setDatos)
      .catch((fallo: unknown) => {
        if (fallo instanceof DOMException && fallo.name === 'AbortError') return
        setError(fallo instanceof ErrorApi ? fallo : null)
      })
      .finally(() => setCargando(false))
    return () => control.abort()
  }, [abierto, ficha, token])

  if (!abierto || !ficha) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      onMouseDown={onCerrar}
    >
      <div
        className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900 flex max-h-[calc(100dvh-2rem)] w-full max-w-lg flex-col overflow-hidden rounded-3xl border bg-white shadow-2xl"
        onMouseDown={(evento) => evento.stopPropagation()}
      >
        <header className="border-tinta-200 dark:border-tinta-800 flex shrink-0 items-start justify-between border-b px-6 py-5">
          <div>
            <p className="text-marca-600 dark:text-marca-400 text-xs font-semibold uppercase tracking-wider">
              Reprogramar
            </p>
            <h2 className="text-tinta-900 dark:text-tinta-50 mt-1 text-xl font-bold">
              {ficha.practitioner_name}
            </h2>
            <p className="text-tinta-500 mt-1 text-sm">
              Turno actual: {fechaYHora(ficha.starts_at)}
            </p>
          </div>
          <button
            type="button"
            onClick={onCerrar}
            disabled={reprogramando}
            className="text-tinta-500 hover:bg-tinta-100 dark:hover:bg-tinta-800 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-xl transition disabled:opacity-50"
            aria-label="Cerrar"
          >
            ×
          </button>
        </header>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-5">
          {error && <Aviso codigo={error.codigo} mensaje={error.message} />}
          {errorReprogramar && (
            <Aviso codigo={errorReprogramar.codigo} mensaje={errorReprogramar.message} />
          )}

          {cargando ? (
            <p className="text-tinta-500 text-sm">Cargando horarios…</p>
          ) : !datos || datos.days.every((d) => d.slots.length === 0) ? (
            <p className="text-tinta-500 text-sm">
              No hay otros horarios libres en las próximas dos semanas.
            </p>
          ) : (
            datos.days.map((dia) => (
              <div key={dia.date}>
                <h3 className="text-tinta-700 dark:text-tinta-300 mb-1.5 text-xs font-semibold uppercase">
                  {dia.date}
                </h3>
                <div className="flex flex-wrap gap-2">
                  {dia.slots.filter((s) => s.reservable).map((slot, i) => (
                    <button
                      key={`${slot.start}-${i}`}
                      type="button"
                      onClick={() => setSlotElegido(slot)}
                      className={[
                        'rounded-xl border px-3 py-1.5 text-sm transition',
                        slotElegido?.start === slot.start && slotElegido.branch.id === slot.branch.id
                          ? 'border-marca-600 bg-marca-50 text-marca-700 dark:bg-marca-950/40 dark:text-marca-300'
                          : 'border-tinta-200 dark:border-tinta-700 hover:border-marca-400',
                      ].join(' ')}
                    >
                      {slot.start.slice(11, 16)} · {slot.branch.name}
                    </button>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        <footer className="border-tinta-200 dark:border-tinta-800 shrink-0 border-t px-6 py-4">
          <div className="flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onCerrar}
              disabled={reprogramando}
              className="border-tinta-300 dark:border-tinta-700 text-tinta-600 dark:text-tinta-300 hover:bg-tinta-100 dark:hover:bg-tinta-800 h-11 rounded-xl border px-5 text-sm font-semibold transition disabled:opacity-50"
            >
              Cancelar
            </button>
            <Boton
              onClick={() => slotElegido && onConfirmar(slotElegido)}
              cargando={reprogramando}
              textoCargando="Reprogramando…"
              disabled={!slotElegido}
              className="w-auto px-5"
            >
              Confirmar nuevo horario
            </Boton>
          </div>
        </footer>
      </div>
    </div>
  )
}
