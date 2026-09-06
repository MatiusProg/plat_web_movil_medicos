/**
 * US-13 — Agendas médicas.
 *
 * La ve quien tiene `scheduling.schedule.read`. La agenda se define como regla
 * —profesional, sucursal, día, franja, duración y cupo— y de ella se derivan
 * los espacios, que se ven en el calendario semanal. El alta, la edición y la
 * baja aparecen sólo con su permiso; la puerta real la pone el backend.
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  bajaAgenda,
  calendarioSemanal,
  crearAgenda,
  editarAgenda,
  listarAgendas,
  type AgendaNueva,
  type AgendaRegla,
  type DiaCalendario,
} from '@/api/agenda'
import { buscarProfesionales, listarSucursales, type Sucursal } from '@/api/catalogo'
import { ErrorApi } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'

const DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

function lunesDeEstaSemana(): string {
  const hoy = new Date()
  const dif = (hoy.getDay() + 6) % 7
  hoy.setDate(hoy.getDate() - dif)
  return hoy.toISOString().slice(0, 10)
}

const REGLA_VACIA = (): AgendaNueva => ({
  practitioner: '',
  branch: '',
  weekday: 0,
  start_time: '09:00',
  end_time: '13:00',
  slot_minutes: 30,
  capacity: 1,
  valid_from: new Date().toISOString().slice(0, 10),
})

export function Agendas() {
  const { token, puede } = useSesion()
  useTitulo('Agendas')

  const puedeCrear = puede('scheduling.schedule.create')
  const puedeEditar = puede('scheduling.schedule.update')

  const [profesionales, setProfesionales] = useState<
    { id: string; full_name: string }[]
  >([])
  const [sucursales, setSucursales] = useState<Sucursal[]>([])
  const [profesional, setProfesional] = useState('')

  const [reglas, setReglas] = useState<AgendaRegla[]>([])
  const [semana, setSemana] = useState<DiaCalendario[]>([])
  const [lunes, setLunes] = useState(lunesDeEstaSemana())

  const [formulario, setFormulario] = useState<AgendaNueva | null>(null)
  const [error, setError] = useState<ErrorApi | null>(null)
  const [guardando, setGuardando] = useState(false)

  const aborto = useRef<AbortController | null>(null)

  useEffect(() => {
    const control = new AbortController()
    Promise.all([
      buscarProfesionales({}, { token }, control.signal),
      listarSucursales({ token }, control.signal),
    ])
      .then(([p, s]) => {
        setProfesionales(p.results)
        setSucursales(s)
      })
      .catch(() => {})
    return () => control.abort()
  }, [token])

  const recargar = useMemo(
    () => async () => {
      if (!profesional) {
        setReglas([])
        setSemana([])
        return
      }
      aborto.current?.abort()
      const control = new AbortController()
      aborto.current = control
      try {
        const [pagina, calendario] = await Promise.all([
          listarAgendas({ practitioner: profesional }, { token }, control.signal),
          calendarioSemanal(profesional, lunes, { token }, control.signal),
        ])
        setReglas(pagina.results)
        setSemana(calendario.days)
      } catch (fallo) {
        if (fallo instanceof DOMException && fallo.name === 'AbortError') return
        setError(fallo instanceof ErrorApi ? fallo : null)
      }
    },
    [profesional, lunes, token],
  )

  useEffect(() => {
    void recargar()
  }, [recargar])

  const guardar = async () => {
    if (!formulario || guardando) return
    setGuardando(true)
    setError(null)
    try {
      await crearAgenda(
        { ...formulario, practitioner: profesional },
        { token },
      )
      setFormulario(null)
      await recargar()
    } catch (fallo) {
      setError(fallo instanceof ErrorApi ? fallo : null)
    } finally {
      setGuardando(false)
    }
  }

  const alternarActiva = async (regla: AgendaRegla) => {
    setError(null)
    try {
      if (regla.is_active) {
        await bajaAgenda(regla.id, { token })
      } else {
        await editarAgenda(regla.id, { is_active: true }, { token })
      }
      await recargar()
    } catch (fallo) {
      setError(fallo instanceof ErrorApi ? fallo : null)
    }
  }

  if (!puede('scheduling.schedule.read')) {
    return (
      <main className="mx-auto max-w-4xl px-5 py-10">
        <p className="text-tinta-500 text-[0.9375rem]">
          No tenés permiso para ver las agendas.
        </p>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-5xl space-y-6 px-5 py-10">
      <div className="surgir flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-marca-700 dark:text-marca-400 text-sm font-medium">
            Agendas y disponibilidad
          </p>
          <h1 className="text-tinta-900 dark:text-tinta-50 mt-1 text-2xl font-semibold tracking-tight">
            Agendas médicas
          </h1>
          <p className="text-tinta-500 mt-1.5 text-[0.9375rem]">
            La agenda se guarda como regla; de ella se derivan los espacios
            reservables.
          </p>
        </div>
        <Link
          to="/agendas/bloqueos"
          className="text-marca-600 dark:text-marca-400 text-sm font-semibold hover:underline"
        >
          Bloqueos y feriados →
        </Link>
      </div>

      <label className="text-sm">
        <span className="text-tinta-700 dark:text-tinta-300 mb-1 block font-medium">
          Profesional
        </span>
        <select
          value={profesional}
          onChange={(e) => setProfesional(e.target.value)}
          className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full max-w-sm rounded-xl border px-3 py-2"
        >
          <option value="">Elegí un profesional…</option>
          {profesionales.map((p) => (
            <option key={p.id} value={p.id}>
              {p.full_name}
            </option>
          ))}
        </select>
      </label>

      {error && <Aviso codigo={error.codigo} mensaje={error.message} />}

      {profesional && (
        <>
          {/* Reglas */}
          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-tinta-800 dark:text-tinta-100 font-semibold">
                Reglas de agenda
              </h2>
              {puedeCrear && !formulario && (
                <button
                  type="button"
                  onClick={() => setFormulario(REGLA_VACIA())}
                  className="bg-marca-600 hover:bg-marca-700 rounded-xl px-3 py-1.5 text-sm font-semibold text-white"
                >
                  Nueva regla
                </button>
              )}
            </div>

            {formulario && (
              <FormularioRegla
                valor={formulario}
                sucursales={sucursales}
                guardando={guardando}
                onCambio={setFormulario}
                onGuardar={guardar}
                onCancelar={() => setFormulario(null)}
              />
            )}

            {reglas.length === 0 ? (
              <p className="text-tinta-500 text-sm">
                Este profesional todavía no tiene reglas de agenda.
              </p>
            ) : (
              <ul className="space-y-2">
                {reglas.map((r) => (
                  <li
                    key={r.id}
                    className={[
                      'border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 flex flex-wrap items-center gap-3 rounded-xl border bg-white px-4 py-3 text-sm',
                      r.is_active ? '' : 'opacity-50',
                    ].join(' ')}
                  >
                    <span className="font-medium">{DIAS[r.weekday]}</span>
                    <span>
                      {r.start_time.slice(0, 5)}–{r.end_time.slice(0, 5)}
                    </span>
                    <span className="text-tinta-500">{r.branch_name}</span>
                    <span className="text-tinta-400">
                      {r.slot_minutes} min · cupo {r.capacity}
                    </span>
                    {r.valid_until && (
                      <span className="text-tinta-400">
                        hasta {r.valid_until}
                      </span>
                    )}
                    {puedeEditar && (
                      <button
                        type="button"
                        onClick={() => alternarActiva(r)}
                        className="text-tinta-500 hover:text-tinta-800 dark:hover:text-tinta-100 ml-auto text-xs underline"
                      >
                        {r.is_active ? 'Dar de baja' : 'Reactivar'}
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Calendario semanal */}
          <section className="space-y-2">
            <div className="flex items-center gap-3">
              <h2 className="text-tinta-800 dark:text-tinta-100 font-semibold">
                Calendario semanal
              </h2>
              <input
                type="date"
                value={lunes}
                onChange={(e) => setLunes(e.target.value)}
                className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 rounded-lg border px-2 py-1 text-sm"
              />
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7">
              {semana.map((dia, i) => (
                <div
                  key={dia.date}
                  className="border-tinta-200 dark:border-tinta-800 rounded-xl border p-2"
                >
                  <p className="text-tinta-500 mb-1 text-xs font-semibold">
                    {DIAS[i]} {dia.date.slice(8, 10)}
                  </p>
                  <div className="space-y-1">
                    {dia.slots.length === 0 ? (
                      <p className="text-tinta-300 text-xs">—</p>
                    ) : (
                      dia.slots.map((s, j) => (
                        <p
                          key={`${s.start}-${j}`}
                          className="bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-300 rounded px-1.5 py-0.5 text-xs"
                          title={s.branch.name}
                        >
                          {s.start.slice(11, 16)}
                        </p>
                      ))
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  )
}

function FormularioRegla({
  valor,
  sucursales,
  guardando,
  onCambio,
  onGuardar,
  onCancelar,
}: {
  valor: AgendaNueva
  sucursales: Sucursal[]
  guardando: boolean
  onCambio: (v: AgendaNueva) => void
  onGuardar: () => void
  onCancelar: () => void
}) {
  const set = <K extends keyof AgendaNueva>(clave: K, v: AgendaNueva[K]) =>
    onCambio({ ...valor, [clave]: v })

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        onGuardar()
      }}
      className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 grid gap-3 rounded-2xl border bg-white p-4 sm:grid-cols-3"
    >
      <label className="text-sm">
        <span className="text-tinta-600 dark:text-tinta-300 mb-1 block">Sucursal</span>
        <select
          required
          value={valor.branch}
          onChange={(e) => set('branch', e.target.value)}
          className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-lg border px-2 py-1.5"
        >
          <option value="">Elegí…</option>
          {sucursales.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </label>

      <label className="text-sm">
        <span className="text-tinta-600 dark:text-tinta-300 mb-1 block">Día</span>
        <select
          value={valor.weekday}
          onChange={(e) => set('weekday', Number(e.target.value))}
          className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-lg border px-2 py-1.5"
        >
          {DIAS.map((d, i) => (
            <option key={d} value={i}>
              {d}
            </option>
          ))}
        </select>
      </label>

      <label className="text-sm">
        <span className="text-tinta-600 dark:text-tinta-300 mb-1 block">Cupo</span>
        <input
          type="number"
          min={1}
          value={valor.capacity}
          onChange={(e) => set('capacity', Number(e.target.value))}
          className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-lg border px-2 py-1.5"
        />
      </label>

      <label className="text-sm">
        <span className="text-tinta-600 dark:text-tinta-300 mb-1 block">Desde</span>
        <input
          type="time"
          value={valor.start_time}
          onChange={(e) => set('start_time', e.target.value)}
          className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-lg border px-2 py-1.5"
        />
      </label>

      <label className="text-sm">
        <span className="text-tinta-600 dark:text-tinta-300 mb-1 block">Hasta</span>
        <input
          type="time"
          value={valor.end_time}
          onChange={(e) => set('end_time', e.target.value)}
          className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-lg border px-2 py-1.5"
        />
      </label>

      <label className="text-sm">
        <span className="text-tinta-600 dark:text-tinta-300 mb-1 block">
          Duración (min)
        </span>
        <input
          type="number"
          min={5}
          step={5}
          value={valor.slot_minutes}
          onChange={(e) => set('slot_minutes', Number(e.target.value))}
          className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-lg border px-2 py-1.5"
        />
      </label>

      <label className="text-sm">
        <span className="text-tinta-600 dark:text-tinta-300 mb-1 block">
          Vigencia desde
        </span>
        <input
          type="date"
          value={valor.valid_from}
          onChange={(e) => set('valid_from', e.target.value)}
          className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-lg border px-2 py-1.5"
        />
      </label>

      <label className="text-sm">
        <span className="text-tinta-600 dark:text-tinta-300 mb-1 block">
          Vigencia hasta (opcional)
        </span>
        <input
          type="date"
          value={valor.valid_until ?? ''}
          onChange={(e) => set('valid_until', e.target.value || null)}
          className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-lg border px-2 py-1.5"
        />
      </label>

      <div className="flex items-end gap-2">
        <button
          type="submit"
          disabled={guardando}
          className="bg-marca-600 hover:bg-marca-700 rounded-lg px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
        >
          {guardando ? 'Guardando…' : 'Guardar'}
        </button>
        <button
          type="button"
          onClick={onCancelar}
          className="text-tinta-500 text-sm underline"
        >
          Cancelar
        </button>
      </div>
    </form>
  )
}
