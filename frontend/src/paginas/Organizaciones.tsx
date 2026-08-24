/**
 * US-43 — Las organizaciones cliente de la plataforma (RF-W-01).
 *
 * Sólo la ve el Superadministrador. La puerta real la pone el backend, que
 * responde 403 a cualquier otro; acá se evita mostrar una pantalla que igual
 * llegaría vacía.
 *
 * **Por qué mira `is_platform_admin` y no `permissions`.** El superadmin no
 * tiene filas en `user_roles`: esa tabla está protegida por RLS con
 * `organization_id = app_current_tenant()`, y las suyas irían con
 * `organization_id` NULL, que nunca compara verdadero. Su lista de permisos
 * llega **vacía**, así que un `permissions.includes('platform.…')` esconde la
 * pantalla justo de quien administra la plataforma. Es el mismo motivo por el
 * que el backend usa la clase `IsPlatformAdmin` y no `has_permission`.
 */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { listarOrganizaciones, type Organizacion } from '@/api/organizaciones'
import { ErrorApi } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { Cabecera } from '@/componentes/Cabecera'
import { IconoEdificio } from '@/componentes/iconos'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'

export function Organizaciones() {
  const { usuario, token } = useSesion()
  const [organizaciones, setOrganizaciones] = useState<Organizacion[] | null>(null)
  const [error, setError] = useState<ErrorApi | null>(null)
  useTitulo('Organizaciones')

  useEffect(() => {
    const control = new AbortController()

    // El estado sólo se toca dentro de las respuestas, nunca de forma síncrona
    // acá: hacerlo dispara un render en cascada, y además no hace falta —
    // `error` ya arranca en null.
    listarOrganizaciones({ token }, control.signal)
      .then((pagina) => setOrganizaciones(pagina.results))
      .catch((e: unknown) => {
        // Cancelar al desmontar no es un fallo que haya que mostrar.
        if (e instanceof DOMException && e.name === 'AbortError') return
        setError(e instanceof ErrorApi ? e : null)
        setOrganizaciones([])
      })

    return () => control.abort()
  }, [token])

  if (!usuario) return null

  if (!usuario.is_platform_admin) {
    return (
      <div className="bg-tinta-50 dark:bg-tinta-950 min-h-dvh">
        <Cabecera />
        <main className="mx-auto max-w-4xl px-5 py-10">
          <p className="text-tinta-500 text-[0.9375rem]">
            Esta sección es del Superadministrador de Plataforma.
          </p>
        </main>
      </div>
    )
  }

  return (
    <div className="bg-tinta-50 dark:bg-tinta-950 min-h-dvh">
      <Cabecera />

      <main className="mx-auto max-w-4xl space-y-6 px-5 py-10">
        <div className="surgir flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-marca-700 dark:text-marca-400 text-sm font-medium">
              Plataforma
            </p>
            <h1 className="text-tinta-900 dark:text-tinta-50 mt-1 text-2xl font-semibold tracking-tight">
              Organizaciones
            </h1>
            <p className="text-tinta-500 mt-1.5 text-[0.9375rem]">
              Los centros médicos que usan la plataforma, cada uno con sus datos
              aislados del resto.
            </p>
          </div>

          <Link
            to="/organizaciones/nueva"
            className="bg-marca-600 hover:bg-marca-700 focus-visible:outline-marca-600 inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-[0.9375rem] font-semibold text-white transition focus-visible:outline-2 focus-visible:outline-offset-2"
          >
            Registrar organización
          </Link>
        </div>

        {error && <Aviso codigo={error.codigo} mensaje={error.message} />}

        {organizaciones === null ? (
          <p className="text-tinta-500 text-[0.9375rem]">Cargando…</p>
        ) : organizaciones.length === 0 && !error ? (
          <div className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 rounded-2xl border bg-white px-5 py-10 text-center">
            <span className="bg-tinta-100 dark:bg-tinta-800 text-tinta-400 mx-auto grid size-11 place-items-center rounded-xl">
              <IconoEdificio className="size-5" />
            </span>
            <p className="text-tinta-600 dark:text-tinta-300 mt-3 text-[0.9375rem] font-medium">
              Todavía no hay ninguna organización registrada.
            </p>
            <p className="text-tinta-500 mt-1 text-sm">
              La primera que registres queda operativa al instante, con su
              administrador y sus roles.
            </p>
          </div>
        ) : (
          <ul className="space-y-3">
            {organizaciones.map((organizacion) => (
              <Fila key={organizacion.id} organizacion={organizacion} />
            ))}
          </ul>
        )}
      </main>
    </div>
  )
}

function Fila({ organizacion }: { organizacion: Organizacion }) {
  return (
    <li className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 flex flex-wrap items-center gap-4 rounded-2xl border bg-white px-5 py-4">
      <span className="bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-400 grid size-10 shrink-0 place-items-center rounded-xl">
        <IconoEdificio className="size-5" />
      </span>

      <div className="min-w-0 flex-1">
        <p className="text-tinta-900 dark:text-tinta-50 truncate font-medium">
          {organizacion.name}
        </p>
        <p className="text-tinta-500 truncate text-sm">
          {organizacion.slug} · NIT {organizacion.tax_id}
          {organizacion.city && ` · ${organizacion.city}`}
        </p>
      </div>

      <div className="flex items-center gap-2">
        <Etiqueta estado={organizacion.status} />
        <span className="text-tinta-600 dark:text-tinta-300 bg-tinta-100 dark:bg-tinta-800 rounded-lg px-2.5 py-1 text-xs font-medium">
          {organizacion.current_plan?.name ?? 'Sin plan'}
        </span>
      </div>
    </li>
  )
}

const ESTADOS = {
  active: { texto: 'Activa', clase: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400' },
  suspended: { texto: 'Suspendida', clase: 'bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-400' },
  inactive: { texto: 'Inactiva', clase: 'bg-tinta-100 text-tinta-600 dark:bg-tinta-800 dark:text-tinta-400' },
} as const

function Etiqueta({ estado }: { estado: Organizacion['status'] }) {
  const { texto, clase } = ESTADOS[estado]
  return (
    <span className={`rounded-lg px-2.5 py-1 text-xs font-medium ${clase}`}>
      {texto}
    </span>
  )
}
