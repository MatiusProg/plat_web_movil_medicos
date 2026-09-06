/**
 * US-16 — Búsqueda de profesionales.
 *
 * La ve quien tiene `catalog.professional.read`. Búsqueda por nombre (parcial,
 * sin distinguir mayúsculas ni tildes) y navegación por especialidad como
 * pantalla de entrada. Cada resultado lleva al detalle de disponibilidad
 * (US-15). Búsqueda vacía devuelve el catálogo completo paginado.
 */

import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  buscarProfesionales,
  listarEspecialidades,
  listarSucursales,
  type Especialidad,
  type ProfesionalTarjeta,
  type Sucursal,
} from '@/api/catalogo'
import { ErrorApi } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'

function proximoEspacio(iso: string | null): string {
  if (!iso) return 'Sin agenda cargada'
  const fecha = new Date(iso)
  return `Próximo: ${fecha.getDate()}/${fecha.getMonth() + 1} ${iso.slice(11, 16)}`
}

export function BuscarProfesionales() {
  const { token, puede } = useSesion()
  useTitulo('Buscar profesionales')

  const [especialidades, setEspecialidades] = useState<Especialidad[]>([])
  const [sucursales, setSucursales] = useState<Sucursal[]>([])

  const [texto, setTexto] = useState('')
  const [especialidad, setEspecialidad] = useState('')
  const [sucursal, setSucursal] = useState('')
  const [pagina, setPagina] = useState(1)

  const [resultados, setResultados] = useState<ProfesionalTarjeta[]>([])
  const [hayMas, setHayMas] = useState(false)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState<ErrorApi | null>(null)

  const aborto = useRef<AbortController | null>(null)

  useEffect(() => {
    const control = new AbortController()
    Promise.all([
      listarEspecialidades({ token }, control.signal),
      listarSucursales({ token }, control.signal),
    ])
      .then(([e, s]) => {
        setEspecialidades(e)
        setSucursales(s)
      })
      .catch(() => {})
    return () => control.abort()
  }, [token])

  useEffect(() => {
    setPagina(1)
  }, [texto, especialidad, sucursal])

  useEffect(() => {
    aborto.current?.abort()
    const control = new AbortController()
    aborto.current = control
    setCargando(true)
    setError(null)

    buscarProfesionales(
      {
        q: texto.trim() || undefined,
        specialty: especialidad || undefined,
        branch: sucursal || undefined,
        page: pagina,
      },
      { token },
      control.signal,
    )
      .then((datos) => {
        setResultados((previos) =>
          pagina === 1 ? datos.results : [...previos, ...datos.results],
        )
        setHayMas(Boolean(datos.next))
      })
      .catch((fallo: unknown) => {
        if (fallo instanceof DOMException && fallo.name === 'AbortError') return
        setError(fallo instanceof ErrorApi ? fallo : null)
      })
      .finally(() => setCargando(false))

    return () => control.abort()
  }, [texto, especialidad, sucursal, pagina, token])

  if (!puede('catalog.professional.read')) {
    return (
      <main className="mx-auto max-w-4xl px-5 py-10">
        <p className="text-tinta-500 text-[0.9375rem]">
          No tenés permiso para consultar el catálogo de profesionales.
        </p>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-5xl space-y-6 px-5 py-10">
      <div className="surgir">
        <p className="text-marca-700 dark:text-marca-400 text-sm font-medium">
          Catálogo del centro médico
        </p>
        <h1 className="text-tinta-900 dark:text-tinta-50 mt-1 text-2xl font-semibold tracking-tight">
          Buscar profesionales
        </h1>
        <p className="text-tinta-500 mt-1.5 text-[0.9375rem]">
          Por especialidad o por nombre. Cada resultado lleva a la
          disponibilidad del profesional.
        </p>
      </div>

      {/* Pantalla de entrada por especialidad */}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setEspecialidad('')}
          className={[
            'rounded-full border px-3 py-1.5 text-sm',
            especialidad === ''
              ? 'border-marca-600 bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-300'
              : 'border-tinta-300 dark:border-tinta-700 text-tinta-600 dark:text-tinta-300',
          ].join(' ')}
        >
          Todas
        </button>
        {especialidades.map((e) => (
          <button
            key={e.id}
            type="button"
            onClick={() => setEspecialidad(e.id)}
            className={[
              'rounded-full border px-3 py-1.5 text-sm',
              especialidad === e.id
                ? 'border-marca-600 bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-300'
                : 'border-tinta-300 dark:border-tinta-700 text-tinta-600 dark:text-tinta-300',
            ].join(' ')}
          >
            {e.name}
          </button>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <input
          type="search"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Buscar por nombre…"
          className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-xl border px-3 py-2 text-sm"
        />
        <select
          value={sucursal}
          onChange={(e) => setSucursal(e.target.value)}
          className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-xl border px-3 py-2 text-sm"
        >
          <option value="">Todas las sucursales</option>
          {sucursales.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </div>

      {error && <Aviso codigo={error.codigo} mensaje={error.message} />}

      {resultados.length === 0 && !cargando ? (
        <p className="text-tinta-500 text-[0.9375rem]">
          No hay profesionales que coincidan.
        </p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {resultados.map((p) => (
            <li
              key={p.id}
              className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 rounded-2xl border bg-white p-4"
            >
              <p className="text-tinta-900 dark:text-tinta-50 font-semibold">
                {p.full_name}
              </p>
              <p className="text-tinta-500 mt-0.5 text-sm">
                {p.specialties.map((s) => s.name).join(' · ') || 'Sin especialidad'}
              </p>
              <p className="text-tinta-400 mt-1 text-xs">
                {p.branches.map((b) => b.name).join(' · ')}
              </p>
              <p className="text-marca-700 dark:text-marca-400 mt-2 text-sm">
                {proximoEspacio(p.next_available_slot)}
              </p>
              <Link
                to={`/disponibilidad?professional=${p.id}`}
                className="text-marca-600 dark:text-marca-400 mt-2 inline-block text-sm font-semibold hover:underline"
              >
                Ver disponibilidad →
              </Link>
            </li>
          ))}
        </ul>
      )}

      {cargando && (
        <p className="text-tinta-500 text-[0.9375rem]">Cargando…</p>
      )}

      {hayMas && !cargando && (
        <button
          type="button"
          onClick={() => setPagina((p) => p + 1)}
          className="border-tinta-300 dark:border-tinta-700 text-tinta-700 dark:text-tinta-200 mx-auto block rounded-xl border px-4 py-2 text-sm font-medium"
        >
          Cargar más
        </button>
      )}
    </main>
  )
}
