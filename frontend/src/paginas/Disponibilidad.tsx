/**
 * US-15 — Disponibilidad consolidada.
 *
 * La ve quien tiene `scheduling.slot.read`. Muestra los espacios libres de un
 * profesional entre **todas** sus sucursales, en una sola vista, ordenados por
 * fecha y etiquetados con la sede. Es el mismo endpoint que consume la app
 * móvil del paciente.
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { listarSucursales, buscarProfesionales, type Sucursal } from '@/api/catalogo'
import {
  disponibilidadConsolidada,
  type Disponibilidad as DatosDisponibilidad,
  type Espacio,
} from '@/api/disponibilidad'
import { reservarFicha } from '@/api/fichas'
import { ErrorApi } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { ModalReservarFicha } from '@/componentes/ModalReservarFicha'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

function isoHoy(desplazamiento = 0): string {
  const fecha = new Date()
  fecha.setDate(fecha.getDate() + desplazamiento)
  return fecha.toISOString().slice(0, 10)
}

function hora(iso: string): string {
  return iso.slice(11, 16)
}

function fechaLarga(iso: string): string {
  const fecha = new Date(`${iso}T00:00:00`)
  return `${DIAS[(fecha.getDay() + 6) % 7]} ${fecha.getDate()}/${fecha.getMonth() + 1}`
}

export function Disponibilidad() {
  const { token, puede } = useSesion()
  useTitulo('Disponibilidad')

  const [parametrosUrl] = useSearchParams()
  const [profesionales, setProfesionales] = useState<
    { id: string; full_name: string }[]
  >([])
  const [sucursales, setSucursales] = useState<Sucursal[]>([])

  const [profesional, setProfesional] = useState(
    parametrosUrl.get('professional') ?? '',
  )
  const [desde, setDesde] = useState(isoHoy())
  const [hasta, setHasta] = useState(isoHoy(14))
  const [sucursal, setSucursal] = useState('')

  const [datos, setDatos] = useState<DatosDisponibilidad | null>(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState<ErrorApi | null>(null)

  // ---------- US-17: reservar el turno elegido ---------------------------
  const [slotElegido, setSlotElegido] = useState<Espacio | null>(null)
  const [reservando, setReservando] = useState(false)
  const [errorReserva, setErrorReserva] = useState<ErrorApi | null>(null)
  const [avisoReserva, setAvisoReserva] = useState<string | null>(null)

  const aborto = useRef<AbortController | null>(null)
  // Cambia tras una reserva exitosa: el turno tomado tiene que desaparecer.
  const [recargaClave, setRecargaClave] = useState(0)

  useEffect(() => {
    const control = new AbortController()
    Promise.all([
      buscarProfesionales({}, { token }, control.signal),
      listarSucursales({ token }, control.signal),
    ])
      .then(([pagina, sedes]) => {
        setProfesionales(pagina.results)
        setSucursales(sedes)
      })
      .catch(() => {})
    return () => control.abort()
  }, [token])

  useEffect(() => {
    if (!profesional) {
      setDatos(null)
      return
    }
    aborto.current?.abort()
    const control = new AbortController()
    aborto.current = control
    setCargando(true)
    setError(null)

    disponibilidadConsolidada(
      { practitioner: profesional, from: desde, to: hasta, branch: sucursal || undefined },
      { token },
      control.signal,
    )
      .then(setDatos)
      .catch((fallo: unknown) => {
        if (fallo instanceof DOMException && fallo.name === 'AbortError') return
        setError(fallo instanceof ErrorApi ? fallo : null)
        setDatos(null)
      })
      .finally(() => setCargando(false))

    return () => control.abort()
  }, [profesional, desde, hasta, sucursal, token, recargaClave])

  const totalEspacios = useMemo(
    () => datos?.days.reduce((suma, dia) => suma + dia.slots.length, 0) ?? 0,
    [datos],
  )

  const puedeReservar = puede('appointments.appointment.create')

  const confirmarReserva = async ({ patientId }: { patientId: string }) => {
    if (!slotElegido) return
    setReservando(true)
    setErrorReserva(null)
    try {
      await reservarFicha(
        {
          patient: patientId,
          practitioner: profesional,
          branch: slotElegido.branch.id,
          schedule: slotElegido.schedule.id,
          startsAt: slotElegido.start,
        },
        { token },
      )
      setSlotElegido(null)
      setAvisoReserva('Ficha reservada. Quedó pendiente de pago.')
      setRecargaClave((clave) => clave + 1)
    } catch (fallo: unknown) {
      const error = fallo instanceof ErrorApi ? fallo : null
      setErrorReserva(error)
      // El turno se ocupó entre que se mostró y que se confirmó: no tiene
      // sentido dejar el modal abierto sobre un espacio que ya no existe.
      if (error?.codigo === 'turno_ocupado') {
        setSlotElegido(null)
        setRecargaClave((clave) => clave + 1)
      }
    } finally {
      setReservando(false)
    }
  }

  if (!puede('scheduling.slot.read')) {
    return (
      <main className="mx-auto max-w-4xl px-5 py-10">
        <p className="text-tinta-500 text-[0.9375rem]">
          No tenés permiso para consultar la disponibilidad.
        </p>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-5xl space-y-6 px-5 py-10">
      <div className="surgir">
        <p className="text-marca-700 dark:text-marca-400 text-sm font-medium">
          Agendas y disponibilidad
        </p>
        <h1 className="text-tinta-900 dark:text-tinta-50 mt-1 text-2xl font-semibold tracking-tight">
          Disponibilidad consolidada
        </h1>
        <p className="text-tinta-500 mt-1.5 text-[0.9375rem]">
          Los espacios libres de un profesional en todas las sucursales donde
          atiende, en una sola vista.
        </p>
      </div>

      <div className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 grid gap-4 rounded-2xl border bg-white p-4 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-sm">
          <span className="text-tinta-700 dark:text-tinta-300 mb-1 block font-medium">
            Profesional
          </span>
          <select
            value={profesional}
            onChange={(e) => setProfesional(e.target.value)}
            className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-xl border px-3 py-2"
          >
            <option value="">Elegí un profesional…</option>
            {profesionales.map((p) => (
              <option key={p.id} value={p.id}>
                {p.full_name}
              </option>
            ))}
          </select>
        </label>

        <label className="text-sm">
          <span className="text-tinta-700 dark:text-tinta-300 mb-1 block font-medium">
            Desde
          </span>
          <input
            type="date"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-xl border px-3 py-2"
          />
        </label>

        <label className="text-sm">
          <span className="text-tinta-700 dark:text-tinta-300 mb-1 block font-medium">
            Hasta
          </span>
          <input
            type="date"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
            className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-xl border px-3 py-2"
          />
        </label>

        <label className="text-sm">
          <span className="text-tinta-700 dark:text-tinta-300 mb-1 block font-medium">
            Sucursal
          </span>
          <select
            value={sucursal}
            onChange={(e) => setSucursal(e.target.value)}
            className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-xl border px-3 py-2"
          >
            <option value="">Todas</option>
            {sucursales.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && <Aviso codigo={error.codigo} mensaje={error.message} />}
      {avisoReserva && (
        <div
          role="status"
          className="rounded-xl border border-marca-200 bg-marca-50 px-3.5 py-3 text-sm text-marca-700 dark:border-marca-900 dark:bg-marca-950/40 dark:text-marca-300"
        >
          {avisoReserva}
        </div>
      )}

      {!profesional ? (
        <p className="text-tinta-500 text-[0.9375rem]">
          Elegí un profesional para ver su disponibilidad.
        </p>
      ) : cargando ? (
        <p className="text-tinta-500 text-[0.9375rem]">Cargando…</p>
      ) : totalEspacios === 0 ? (
        <p className="text-tinta-500 text-[0.9375rem]">
          No hay espacios libres en ese rango.
        </p>
      ) : (
        <div className="space-y-5">
          {datos?.days.map((dia) => (
            <div key={dia.date}>
              <h2 className="text-tinta-700 dark:text-tinta-300 mb-2 text-sm font-semibold">
                {fechaLarga(dia.date)}
              </h2>
              <div className="flex flex-wrap gap-2">
                {dia.slots.map((slot, i) => {
                  const puedeElegirlo = slot.reservable && puedeReservar
                  const Elemento = puedeElegirlo ? 'button' : 'span'
                  return (
                    <Elemento
                      key={`${slot.start}-${i}`}
                      type={puedeElegirlo ? 'button' : undefined}
                      onClick={
                        puedeElegirlo
                          ? () => {
                              setErrorReserva(null)
                              setAvisoReserva(null)
                              setSlotElegido(slot)
                            }
                          : undefined
                      }
                      title={
                        slot.reservable
                          ? puedeReservar
                            ? 'Reservar este horario'
                            : undefined
                          : slot.reason === 'profesional_inactivo'
                            ? 'Profesional inactivo'
                            : 'Sucursal inactiva'
                      }
                      className={[
                        'inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm',
                        slot.reservable
                          ? 'border-tinta-200 dark:border-tinta-700 dark:bg-tinta-900 bg-white'
                          : 'border-tinta-200 dark:border-tinta-800 text-tinta-400 line-through opacity-60',
                        puedeElegirlo
                          ? 'hover:border-marca-400 hover:bg-marca-50 dark:hover:bg-marca-950/40 cursor-pointer transition'
                          : '',
                      ].join(' ')}
                    >
                      <span className="font-medium">{hora(slot.start)}</span>
                      <span className="bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-300 rounded-md px-1.5 py-0.5 text-xs">
                        {slot.branch.name}
                      </span>
                      {slot.capacity > 1 && (
                        <span className="text-tinta-400 text-xs">
                          cupo {slot.capacity}
                        </span>
                      )}
                    </Elemento>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      <ModalReservarFicha
        abierto={slotElegido !== null}
        slot={slotElegido}
        practitionerName={datos?.practitioner.full_name ?? ''}
        reservando={reservando}
        errorReserva={errorReserva}
        onCerrar={() => {
          if (reservando) return
          setSlotElegido(null)
          setErrorReserva(null)
        }}
        onConfirmar={confirmarReserva}
      />
    </main>
  )
}
