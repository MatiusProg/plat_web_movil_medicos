/**
 * US-17 — Confirmar la reserva de un turno.
 *
 * Se abre desde la grilla de `Disponibilidad.tsx` con el espacio ya elegido
 * —sucursal, profesional, fecha y hora—; acá sólo falta decidir para quién es
 * la ficha. El selector de paciente lo arma el mismo endpoint que consume
 * `PatientSelector` en la app móvil (US-07 h): el titular siempre primero, y
 * si no hay dependientes no se muestra ningún desplegable.
 */

import { useEffect, useState } from 'react'

import type { Espacio } from '@/api/disponibilidad'
import { listarOpcionesDePaciente, type OpcionDePaciente } from '@/api/pacientes'
import { ErrorApi } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { Boton } from '@/componentes/Boton'
import { useSesion } from '@/sesion/useSesion'

interface Props {
  abierto: boolean
  slot: Espacio | null
  practitionerName: string
  reservando?: boolean
  /** El error de la última confirmación (turno ocupado, política, etc.). */
  errorReserva?: ErrorApi | null
  onCerrar: () => void
  onConfirmar: (datos: { patientId: string }) => void | Promise<void>
}

function fechaYHora(iso: string): string {
  const fecha = new Date(iso)
  return fecha.toLocaleString('es-BO', {
    weekday: 'long', day: 'numeric', month: 'long',
    hour: '2-digit', minute: '2-digit',
  })
}

export function ModalReservarFicha({
  abierto, slot, practitionerName, reservando = false, errorReserva = null,
  onCerrar, onConfirmar,
}: Props) {
  const { token } = useSesion()
  const [opciones, setOpciones] = useState<OpcionDePaciente[] | null>(null)
  const [pacienteId, setPacienteId] = useState('')
  const [error, setError] = useState<ErrorApi | null>(null)

  useEffect(() => {
    if (!abierto) return
    setError(null)
    setOpciones(null)
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
  }, [abierto, token])

  if (!abierto || !slot) return null

  const confirmar = async () => {
    if (!pacienteId) return
    await onConfirmar({ patientId: pacienteId })
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      onMouseDown={onCerrar}
    >
      <div
        className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900 w-full max-w-md rounded-3xl border bg-white shadow-2xl"
        onMouseDown={(evento) => evento.stopPropagation()}
      >
        <header className="border-tinta-200 dark:border-tinta-800 flex items-start justify-between border-b px-6 py-5">
          <div>
            <p className="text-marca-600 dark:text-marca-400 text-xs font-semibold uppercase tracking-wider">
              Reservar ficha
            </p>
            <h2 className="text-tinta-900 dark:text-tinta-50 mt-1 text-xl font-bold">
              {practitionerName}
            </h2>
            <p className="text-tinta-500 mt-1 text-sm capitalize">
              {fechaYHora(slot.start)} · {slot.branch.name}
            </p>
          </div>
          <button
            type="button"
            onClick={onCerrar}
            disabled={reservando}
            className="text-tinta-500 hover:bg-tinta-100 dark:hover:bg-tinta-800 hover:text-tinta-800 dark:hover:text-tinta-100 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-xl transition disabled:opacity-50"
            aria-label="Cerrar"
          >
            ×
          </button>
        </header>

        <div className="space-y-4 px-6 py-5">
          {error && <Aviso codigo={error.codigo} mensaje={error.message} />}
          {errorReserva && (
            <Aviso codigo={errorReserva.codigo} mensaje={errorReserva.message} />
          )}

          {opciones === null ? (
            <p className="text-tinta-500 text-sm">Cargando…</p>
          ) : opciones.length > 1 ? (
            <label className="text-sm">
              <span className="text-tinta-700 dark:text-tinta-300 mb-1 block font-medium">
                ¿Para quién es?
              </span>
              <select
                value={pacienteId}
                onChange={(e) => setPacienteId(e.target.value)}
                className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-xl border px-3 py-2"
              >
                {opciones.map((opcion) => (
                  <option key={opcion.id} value={opcion.id}>
                    {opcion.is_self ? opcion.full_name : `${opcion.full_name} · ${opcion.relationship_label}`}
                  </option>
                ))}
              </select>
            </label>
          ) : opciones.length === 1 ? (
            <p className="text-tinta-700 dark:text-tinta-300 text-sm">
              Para <strong>{opciones[0].full_name}</strong>.
            </p>
          ) : (
            !error && (
              <p className="text-tinta-500 text-sm">
                No hay a quién reservarle una ficha todavía.
              </p>
            )
          )}
        </div>

        <footer className="border-tinta-200 dark:border-tinta-800 border-t px-6 py-4">
          <div className="flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onCerrar}
              disabled={reservando}
              className="border-tinta-300 dark:border-tinta-700 text-tinta-600 dark:text-tinta-300 hover:bg-tinta-100 dark:hover:bg-tinta-800 h-11 rounded-xl border px-5 text-sm font-semibold transition disabled:opacity-50"
            >
              Cancelar
            </button>
            <Boton
              onClick={confirmar}
              cargando={reservando}
              textoCargando="Reservando…"
              disabled={!pacienteId}
              className="w-auto px-5"
            >
              Confirmar reserva
            </Boton>
          </div>
        </footer>
      </div>
    </div>
  )
}
