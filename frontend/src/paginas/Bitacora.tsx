/**
 * US-06 — Consulta de la bitácora de auditoría.
 *
 * La ve quien tiene `audit.log.read`, que en la práctica es el Administrador
 * de Organización. Filtros por actor, tipo de acción y rango de fechas, del
 * asiento más reciente al más antiguo.
 *
 * **No hay ningún botón que escriba.** No es un olvido de esta pantalla: la
 * bitácora no expone verbos de escritura ni siquiera al administrador, y la
 * base tampoco los admite —`audit_log` tiene revocados UPDATE y DELETE—. Una
 * bitácora que se puede editar no sirve para lo que existe.
 *
 * El detalle de cada asiento se muestra desplegado y no en un modal: lo que
 * cambió es lo que se viene a mirar, y esconderlo detrás de un clic convierte
 * revisar veinte asientos en veinte clics.
 */

import { useEffect, useMemo, useRef, useState } from 'react'

import {
  listarAccionesBitacora,
  listarBitacora,
  type AccionBitacora,
  type AsientoBitacora,
} from '@/api/bitacora'
import { listarUsuarios, type UsuarioDeLaOrganizacion } from '@/api/roles'
import { ErrorApi } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'

const POR_PAGINA = 25

function momento(iso: string): string {
  const fecha = new Date(iso)
  const dia = String(fecha.getDate()).padStart(2, '0')
  const mes = String(fecha.getMonth() + 1).padStart(2, '0')
  const hora = String(fecha.getHours()).padStart(2, '0')
  const minuto = String(fecha.getMinutes()).padStart(2, '0')
  return `${dia}/${mes}/${fecha.getFullYear()} ${hora}:${minuto}`
}

/**
 * El detalle, en una línea por dato.
 *
 * US-04 guarda los cambios como `{ campo: { antes, despues } }` y el resto de
 * las historias como pares sueltos. Se contemplan las dos formas: mostrar el
 * JSON crudo sería más corto de escribir y bastante inútil de leer.
 */
function lineasDelDetalle(detalle: Record<string, unknown>): string[] {
  return Object.entries(detalle).map(([clave, valor]) => {
    if (
      valor !== null &&
      typeof valor === 'object' &&
      !Array.isArray(valor) &&
      'antes' in (valor as Record<string, unknown>)
    ) {
      const cambio = valor as { antes: unknown; despues: unknown }
      return `${clave}: ${JSON.stringify(cambio.antes)} → ${JSON.stringify(cambio.despues)}`
    }
    if (Array.isArray(valor)) {
      return `${clave}: ${valor.length === 0 ? '—' : valor.join(', ')}`
    }
    return `${clave}: ${String(valor)}`
  })
}

export function Bitacora() {
  const { token, puede } = useSesion()
  useTitulo('Bitácora de auditoría')

  const [acciones, setAcciones] = useState<AccionBitacora[]>([])
  const [usuarios, setUsuarios] = useState<UsuarioDeLaOrganizacion[]>([])

  const [actor, setActor] = useState('')
  const [accion, setAccion] = useState('')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [pagina, setPagina] = useState(1)

  const [asientos, setAsientos] = useState<AsientoBitacora[]>([])
  const [total, setTotal] = useState(0)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState<ErrorApi | null>(null)

  const aborto = useRef<AbortController | null>(null)

  const autorizada = puede('audit.log.read')

  // El catálogo del filtro y la lista de actores. La de usuarios puede fallar
  // con 403 —leer la bitácora no obliga a poder listar usuarios—, y en ese
  // caso el filtro por actor simplemente no se ofrece.
  useEffect(() => {
    if (!autorizada) return
    const control = new AbortController()

    listarAccionesBitacora({ token }, control.signal)
      .then(setAcciones)
      .catch(() => {})

    listarUsuarios({ token }, control.signal)
      .then((pagina) => setUsuarios(pagina.results))
      .catch(() => setUsuarios([]))

    return () => control.abort()
  }, [token, autorizada])

  useEffect(() => {
    setPagina(1)
  }, [actor, accion, desde, hasta])

  useEffect(() => {
    if (!autorizada) return

    aborto.current?.abort()
    const control = new AbortController()
    aborto.current = control
    setCargando(true)
    setError(null)

    listarBitacora(
      {
        actor: actor || undefined,
        action: accion || undefined,
        date_from: desde || undefined,
        date_to: hasta || undefined,
        page: pagina,
      },
      { token },
      control.signal,
    )
      .then((datos) => {
        setAsientos(datos.results)
        setTotal(datos.count)
      })
      .catch((fallo: unknown) => {
        if (fallo instanceof DOMException && fallo.name === 'AbortError') return
        setError(fallo instanceof ErrorApi ? fallo : null)
        setAsientos([])
        setTotal(0)
      })
      .finally(() => setCargando(false))

    return () => control.abort()
  }, [actor, accion, desde, hasta, pagina, token, autorizada])

  const paginas = useMemo(
    () => Math.max(1, Math.ceil(total / POR_PAGINA)),
    [total],
  )

  const hayFiltros = Boolean(actor || accion || desde || hasta)

  if (!autorizada) {
    return (
      <main className="mx-auto max-w-4xl px-5 py-10">
        <p className="text-tinta-500 text-[0.9375rem]">
          No tenés permiso para consultar la bitácora de auditoría.
        </p>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-5xl space-y-6 px-5 py-10">
      <div className="surgir">
        <p className="text-marca-700 dark:text-marca-400 text-sm font-medium">
          Seguridad de la organización
        </p>
        <h1 className="text-tinta-900 dark:text-tinta-50 mt-1 text-2xl font-semibold tracking-tight">
          Bitácora de auditoría
        </h1>
        <p className="text-tinta-500 mt-1.5 text-[0.9375rem]">
          Registro cronológico de las acciones sensibles de tu organización. Es
          de sólo lectura: no se edita ni se borra desde la aplicación.
        </p>
      </div>

      {/* Filtros — punto (e) de la historia */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {usuarios.length > 0 && (
          <label className="block">
            <span className="text-tinta-600 dark:text-tinta-400 mb-1 block text-xs font-medium">
              Actor
            </span>
            <select
              value={actor}
              onChange={(e) => setActor(e.target.value)}
              className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-xl border px-3 py-2 text-sm"
            >
              <option value="">Cualquiera</option>
              {usuarios.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="block">
          <span className="text-tinta-600 dark:text-tinta-400 mb-1 block text-xs font-medium">
            Acción
          </span>
          <select
            value={accion}
            onChange={(e) => setAccion(e.target.value)}
            className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-xl border px-3 py-2 text-sm"
          >
            <option value="">Todas</option>
            {acciones.map((a) => (
              <option key={a.code} value={a.code}>
                {a.label}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-tinta-600 dark:text-tinta-400 mb-1 block text-xs font-medium">
            Desde
          </span>
          <input
            type="date"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-xl border px-3 py-2 text-sm"
          />
        </label>

        <label className="block">
          <span className="text-tinta-600 dark:text-tinta-400 mb-1 block text-xs font-medium">
            Hasta
          </span>
          <input
            type="date"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
            className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 w-full rounded-xl border px-3 py-2 text-sm"
          />
        </label>
      </div>

      {hayFiltros && (
        <button
          type="button"
          onClick={() => {
            setActor('')
            setAccion('')
            setDesde('')
            setHasta('')
          }}
          className="text-marca-600 dark:text-marca-400 text-sm font-medium hover:underline"
        >
          Limpiar filtros
        </button>
      )}

      {error && <Aviso codigo={error.codigo} mensaje={error.message} />}

      <p className="text-tinta-500 text-sm">
        {cargando
          ? 'Cargando…'
          : `${total} ${total === 1 ? 'asiento' : 'asientos'}`}
      </p>

      {asientos.length === 0 && !cargando ? (
        <p className="text-tinta-500 text-[0.9375rem]">
          {hayFiltros
            ? 'No hay asientos que coincidan con estos filtros.'
            : 'Todavía no hay nada registrado.'}
        </p>
      ) : (
        <ul className="space-y-2">
          {asientos.map((asiento) => {
            const lineas = lineasDelDetalle(asiento.detail)
            return (
              <li
                key={asiento.id}
                className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 rounded-2xl border bg-white p-4"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                  <p className="text-tinta-900 dark:text-tinta-50 font-semibold">
                    {asiento.action_label}
                  </p>
                  <p className="text-tinta-500 text-xs tabular-nums">
                    {momento(asiento.occurred_at)}
                  </p>
                </div>

                <p className="text-tinta-500 mt-0.5 text-sm">
                  {asiento.actor
                    ? `${asiento.actor.full_name} · ${asiento.actor.email}`
                    : 'Sin actor identificado'}
                </p>

                {lineas.length > 0 && (
                  <ul className="text-tinta-600 dark:text-tinta-300 mt-2 space-y-0.5 text-sm">
                    {lineas.map((linea) => (
                      <li key={linea} className="break-words">
                        {linea}
                      </li>
                    ))}
                  </ul>
                )}

                <p className="text-tinta-400 mt-2 text-xs">
                  {asiento.entity}
                  {asiento.entity_id && ` · ${asiento.entity_id}`}
                  {asiento.ip_address && ` · ${asiento.ip_address}`}
                </p>
                {asiento.user_agent && (
                  <p className="text-tinta-400 mt-0.5 truncate text-xs">
                    {asiento.user_agent}
                  </p>
                )}
              </li>
            )
          })}
        </ul>
      )}

      {paginas > 1 && (
        <div className="flex items-center justify-between gap-3">
          <button
            type="button"
            disabled={pagina <= 1 || cargando}
            onClick={() => setPagina((p) => p - 1)}
            className="border-tinta-300 dark:border-tinta-700 text-tinta-700 dark:text-tinta-200 rounded-xl border px-4 py-2 text-sm font-medium disabled:opacity-40"
          >
            Anterior
          </button>

          <span className="text-tinta-500 text-sm">
            Página {pagina} de {paginas}
          </span>

          <button
            type="button"
            disabled={pagina >= paginas || cargando}
            onClick={() => setPagina((p) => p + 1)}
            className="border-tinta-300 dark:border-tinta-700 text-tinta-700 dark:text-tinta-200 rounded-xl border px-4 py-2 text-sm font-medium disabled:opacity-40"
          >
            Siguiente
          </button>
        </div>
      )}
    </main>
  )
}
