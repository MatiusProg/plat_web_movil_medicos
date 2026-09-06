/**
 * US-14 — Bloqueo de agenda.
 *
 * Los bloqueos tapan rangos de la agenda por vacaciones, feriados o ausencias.
 * Un bloqueo sin profesional es un feriado de toda la organización. La regla
 * de agenda no se toca: al levantar el bloqueo, la agenda vuelve sola.
 */

import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  crearBloqueo,
  fichasAfectadas,
  levantarBloqueo,
  listarBloqueos,
  type Bloqueo,
  type BloqueoNuevo,
  type MotivoBloqueo,
} from '@/api/agenda'
import { buscarProfesionales } from '@/api/catalogo'
import { ErrorApi } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'

const MOTIVOS: Record<MotivoBloqueo, string> = {
  vacation: 'Vacaciones',
  holiday: 'Feriado',
  leave: 'Licencia',
  absence: 'Ausencia imprevista',
}

function formNuevo(): BloqueoNuevo {
  const hoy = new Date().toISOString().slice(0, 16)
  return {
    practitioner: '',
    starts_at: hoy,
    ends_at: hoy,
    reason: 'vacation',
    note: '',
  }
}

export function BloqueosAgenda() {
  const { token, puede } = useSesion()
  useTitulo('Bloqueos de agenda')

  const puedeCrear = puede('scheduling.block.create')
  const puedeLevantar = puede('scheduling.block.update')

  const [profesionales, setProfesionales] = useState<
    { id: string; full_name: string }[]
  >([])
  const [bloqueos, setBloqueos] = useState<Bloqueo[]>([])
  const [formulario, setFormulario] = useState<BloqueoNuevo | null>(null)
  const [afectadas, setAfectadas] = useState<Record<string, number>>({})
  const [error, setError] = useState<ErrorApi | null>(null)
  const [guardando, setGuardando] = useState(false)

  const aborto = useRef<AbortController | null>(null)

  const recargar = async () => {
    aborto.current?.abort()
    const control = new AbortController()
    aborto.current = control
    try {
      const pagina = await listarBloqueos({}, { token }, control.signal)
      setBloqueos(pagina.results)
      const conteos: Record<string, number> = {}
      await Promise.all(
        pagina.results
          .filter((b) => b.is_active)
          .map(async (b) => {
            const resumen = await fichasAfectadas(b.id, { token })
            conteos[b.id] = resumen.count
          }),
      )
      setAfectadas(conteos)
    } catch (fallo) {
      if (fallo instanceof DOMException && fallo.name === 'AbortError') return
      setError(fallo instanceof ErrorApi ? fallo : null)
    }
  }

  useEffect(() => {
    const control = new AbortController()
    buscarProfesionales({}, { token }, control.signal)
      .then((p) => setProfesionales(p.results))
      .catch(() => {})
    void recargar()
    return () => control.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const guardar = async () => {
    if (!formulario || guardando) return
    setGuardando(true)
    setError(null)
    try {
      await crearBloqueo(
        {
          ...formulario,
          practitioner: formulario.practitioner || null,
          note: formulario.note || undefined,
        },
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

  const levantar = async (bloqueo: Bloqueo) => {
    setError(null)
    try {
      await levantarBloqueo(bloqueo.id, { token })
      await recargar()
    } catch (fallo) {
      setError(fallo instanceof ErrorApi ? fallo : null)
    }
  }

  if (!puede('scheduling.block.read')) {
    return (
      <main className="mx-auto max-w-4xl px-5 py-10">
        <p className="text-tinta-500 text-[0.9375rem]">
          No tenés permiso para ver los bloqueos de agenda.
        </p>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-4xl space-y-6 px-5 py-10">
      <div className="surgir flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-marca-700 dark:text-marca-400 text-sm font-medium">
            Agendas y disponibilidad
          </p>
          <h1 className="text-tinta-900 dark:text-tinta-50 mt-1 text-2xl font-semibold tracking-tight">
            Bloqueos y feriados
          </h1>
          <p className="text-tinta-500 mt-1.5 text-[0.9375rem]">
            Los espacios bloqueados dejan de ofrecerse; la regla de agenda no se
            toca.
          </p>
        </div>
        <Link
          to="/agendas"
          className="text-marca-600 dark:text-marca-400 text-sm font-semibold hover:underline"
        >
          ← Agendas
        </Link>
      </div>

      {error && <Aviso codigo={error.codigo} mensaje={error.message} />}

      {puedeCrear && (
        <div>
          {formulario ? (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                guardar()
              }}
              className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 grid gap-3 rounded-2xl border bg-white p-4 sm:grid-cols-2"
            >
              <label className="text-sm">
                <span className="text-tinta-600 dark:text-tinta-300 mb-1 block">
                  Profesional (vacío = feriado de toda la organización)
                </span>
                <select
                  value={formulario.practitioner ?? ''}
                  onChange={(e) =>
                    setFormulario({ ...formulario, practitioner: e.target.value })
                  }
                  className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-lg border px-2 py-1.5"
                >
                  <option value="">Feriado de la organización</option>
                  {profesionales.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.full_name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="text-sm">
                <span className="text-tinta-600 dark:text-tinta-300 mb-1 block">
                  Motivo
                </span>
                <select
                  value={formulario.reason}
                  onChange={(e) =>
                    setFormulario({
                      ...formulario,
                      reason: e.target.value as MotivoBloqueo,
                    })
                  }
                  className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-lg border px-2 py-1.5"
                >
                  {Object.entries(MOTIVOS).map(([valor, etiqueta]) => (
                    <option key={valor} value={valor}>
                      {etiqueta}
                    </option>
                  ))}
                </select>
              </label>

              <label className="text-sm">
                <span className="text-tinta-600 dark:text-tinta-300 mb-1 block">
                  Desde
                </span>
                <input
                  type="datetime-local"
                  value={formulario.starts_at}
                  onChange={(e) =>
                    setFormulario({ ...formulario, starts_at: e.target.value })
                  }
                  className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-lg border px-2 py-1.5"
                />
              </label>

              <label className="text-sm">
                <span className="text-tinta-600 dark:text-tinta-300 mb-1 block">
                  Hasta
                </span>
                <input
                  type="datetime-local"
                  value={formulario.ends_at}
                  onChange={(e) =>
                    setFormulario({ ...formulario, ends_at: e.target.value })
                  }
                  className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-lg border px-2 py-1.5"
                />
              </label>

              <label className="text-sm sm:col-span-2">
                <span className="text-tinta-600 dark:text-tinta-300 mb-1 block">
                  Nota (opcional)
                </span>
                <input
                  type="text"
                  value={formulario.note ?? ''}
                  onChange={(e) =>
                    setFormulario({ ...formulario, note: e.target.value })
                  }
                  className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-lg border px-2 py-1.5"
                />
              </label>

              <div className="flex items-end gap-2">
                <button
                  type="submit"
                  disabled={guardando}
                  className="bg-marca-600 hover:bg-marca-700 rounded-lg px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
                >
                  {guardando ? 'Guardando…' : 'Crear bloqueo'}
                </button>
                <button
                  type="button"
                  onClick={() => setFormulario(null)}
                  className="text-tinta-500 text-sm underline"
                >
                  Cancelar
                </button>
              </div>
            </form>
          ) : (
            <button
              type="button"
              onClick={() => setFormulario(formNuevo())}
              className="bg-marca-600 hover:bg-marca-700 rounded-xl px-4 py-2 text-sm font-semibold text-white"
            >
              Nuevo bloqueo
            </button>
          )}
        </div>
      )}

      <ul className="space-y-2">
        {bloqueos.length === 0 && (
          <p className="text-tinta-500 text-sm">No hay bloqueos cargados.</p>
        )}
        {bloqueos.map((b) => (
          <li
            key={b.id}
            className={[
              'border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 rounded-xl border bg-white px-4 py-3 text-sm',
              b.is_active ? '' : 'opacity-50',
            ].join(' ')}
          >
            <div className="flex flex-wrap items-center gap-3">
              <span className="font-medium">
                {b.practitioner_name ?? 'Toda la organización'}
              </span>
              <span className="text-tinta-500">{MOTIVOS[b.reason]}</span>
              <span className="text-tinta-400">
                {b.starts_at.slice(0, 16).replace('T', ' ')} →{' '}
                {b.ends_at.slice(0, 16).replace('T', ' ')}
              </span>
              {b.is_active && afectadas[b.id] > 0 && (
                <span className="text-alerta-600 dark:text-alerta-500">
                  {afectadas[b.id]} ficha(s) afectada(s)
                </span>
              )}
              {puedeLevantar && b.is_active && (
                <button
                  type="button"
                  onClick={() => levantar(b)}
                  className="text-tinta-500 hover:text-tinta-800 dark:hover:text-tinta-100 ml-auto text-xs underline"
                >
                  Levantar
                </button>
              )}
            </div>
            {b.note && (
              <p className="text-tinta-400 mt-1 text-xs">{b.note}</p>
            )}
          </li>
        ))}
      </ul>
    </main>
  )
}
