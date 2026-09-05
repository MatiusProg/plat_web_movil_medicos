/**
 * US-04 — Asignación de roles a los usuarios de la organización.
 *
 * El listado es de sólo lectura a propósito: el ABM de usuarios no está en el
 * Sprint 1 y el perfil propio es US-05. Lo que esta pantalla resuelve es la
 * tercera parte de la historia —*asignación de rol a los usuarios*—, y para
 * eso alcanza con saber quién es cada uno y qué roles tiene hoy.
 *
 * Las asignaciones de un usuario se piden al abrirlo y no en el listado: el
 * identificador que hace falta para revocar es el de la **asignación**, no el
 * del rol, y traerlo para todos de entrada sería una consulta por fila que
 * casi nadie va a usar.
 */

import { useEffect, useState } from 'react'

import {
  asignarRol,
  listarAsignacionesDe,
  listarRoles,
  listarUsuarios,
  revocarAsignacion,
  type Asignacion,
  type Rol,
  type UsuarioDeLaOrganizacion,
} from '@/api/roles'
import { ErrorApi } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'

export function Usuarios() {
  const { token, puede } = useSesion()
  useTitulo('Usuarios y roles')

  const [usuarios, setUsuarios] = useState<UsuarioDeLaOrganizacion[] | null>(null)
  const [roles, setRoles] = useState<Rol[]>([])
  const [error, setError] = useState<ErrorApi | null>(null)
  const [abierto, setAbierto] = useState<string | null>(null)

  const puedeAsignar = puede('users.role.assign')

  useEffect(() => {
    const control = new AbortController()

    Promise.all([
      listarUsuarios({ token }, control.signal),
      // Los roles alimentan el desplegable de asignación. Si no se pueden
      // leer, la pantalla sigue sirviendo para ver quién tiene qué.
      listarRoles({ token }, control.signal).catch(() => null),
    ])
      .then(([pagina, rolesPagina]) => {
        setUsuarios(pagina.results)
        setRoles((rolesPagina?.results ?? []).filter((rol) => rol.is_active))
      })
      .catch((e: unknown) => {
        if (e instanceof DOMException && e.name === 'AbortError') return
        setError(e instanceof ErrorApi ? e : null)
        setUsuarios([])
      })

    return () => control.abort()
  }, [token])

  const refrescarUsuarios = async () => {
    const pagina = await listarUsuarios({ token })
    setUsuarios(pagina.results)
  }

  if (!puede('users.user.read')) {
    return (
      <main className="mx-auto max-w-4xl px-5 py-10">
        <p className="text-tinta-500 text-[0.9375rem]">
          No tenés permiso para ver los usuarios de la organización.
        </p>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-5xl space-y-6 px-5 py-10">
      <div className="surgir">
        <p className="text-marca-700 dark:text-marca-400 text-sm font-medium">
          Usuarios y seguridad
        </p>
        <h1 className="text-tinta-900 dark:text-tinta-50 mt-1 text-2xl font-semibold tracking-tight">
          Usuarios y roles
        </h1>
        <p className="text-tinta-500 mt-1.5 text-[0.9375rem]">
          Quién trabaja en el centro médico y qué puede hacer cada uno. Un
          usuario puede tener más de un rol.
        </p>
      </div>

      {error && <Aviso codigo={error.codigo} mensaje={error.message} />}

      {usuarios === null ? (
        <p className="text-tinta-500 text-[0.9375rem]">Cargando…</p>
      ) : (
        <ul className="space-y-3">
          {usuarios.map((usuario) => (
            <FilaUsuario
              key={usuario.id}
              usuario={usuario}
              roles={roles}
              abierto={abierto === usuario.id}
              puedeAsignar={puedeAsignar}
              alAbrir={() =>
                setAbierto(abierto === usuario.id ? null : usuario.id)
              }
              alCambiar={refrescarUsuarios}
            />
          ))}
        </ul>
      )}
    </main>
  )
}

function FilaUsuario({
  usuario,
  roles,
  abierto,
  puedeAsignar,
  alAbrir,
  alCambiar,
}: {
  usuario: UsuarioDeLaOrganizacion
  roles: Rol[]
  abierto: boolean
  puedeAsignar: boolean
  alAbrir: () => void
  alCambiar: () => Promise<void>
}) {
  const { token } = useSesion()

  const [asignaciones, setAsignaciones] = useState<Asignacion[] | null>(null)
  const [elegido, setElegido] = useState('')
  const [trabajando, setTrabajando] = useState(false)
  const [error, setError] = useState<ErrorApi | null>(null)

  useEffect(() => {
    if (!abierto) return

    const control = new AbortController()

    listarAsignacionesDe(usuario.id, { token }, control.signal)
      .then((pagina) => setAsignaciones(pagina.results))
      .catch((e: unknown) => {
        if (e instanceof DOMException && e.name === 'AbortError') return
        setError(e instanceof ErrorApi ? e : null)
        setAsignaciones([])
      })

    return () => control.abort()
  }, [abierto, token, usuario.id])

  const recargar = async () => {
    const pagina = await listarAsignacionesDe(usuario.id, { token })
    setAsignaciones(pagina.results)
    await alCambiar()
  }

  const asignar = async () => {
    if (!elegido) return
    setTrabajando(true)
    setError(null)
    try {
      await asignarRol(usuario.id, elegido, { token })
      setElegido('')
      await recargar()
    } catch (e: unknown) {
      setError(e instanceof ErrorApi ? e : null)
    } finally {
      setTrabajando(false)
    }
  }

  const revocar = async (asignacion: Asignacion) => {
    setTrabajando(true)
    setError(null)
    try {
      await revocarAsignacion(asignacion.id, { token })
      await recargar()
    } catch (e: unknown) {
      setError(e instanceof ErrorApi ? e : null)
    } finally {
      setTrabajando(false)
    }
  }

  const yaTiene = new Set((asignaciones ?? []).map((una) => una.role))
  const disponibles = roles.filter((rol) => !yaTiene.has(rol.id))

  return (
    <li className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 rounded-2xl border bg-white">
      <div className="flex flex-wrap items-center gap-4 px-5 py-4">
        <span className="bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-400 grid size-10 shrink-0 place-items-center rounded-xl text-sm font-semibold">
          {usuario.first_name.charAt(0)}
          {usuario.last_name.charAt(0)}
        </span>

        <div className="min-w-0 flex-1">
          <p className="text-tinta-900 dark:text-tinta-50 truncate font-medium">
            {usuario.full_name}
            {!usuario.is_active && (
              <span className="text-tinta-500 bg-tinta-100 dark:bg-tinta-800 ml-2 rounded-lg px-2 py-0.5 text-xs font-medium">
                Dado de baja
              </span>
            )}
          </p>
          <p className="text-tinta-500 truncate text-sm">
            {usuario.email} · {usuario.document_type} {usuario.document_number}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {usuario.roles.length === 0 ? (
            <span className="text-tinta-500 text-sm">Sin rol</span>
          ) : (
            usuario.roles.map((rol) => (
              <span
                key={rol.id}
                className="text-tinta-600 dark:text-tinta-300 bg-tinta-100 dark:bg-tinta-800 rounded-lg px-2.5 py-1 text-xs font-medium"
              >
                {rol.name}
              </span>
            ))
          )}

          <button
            type="button"
            onClick={alAbrir}
            className="border-tinta-300 dark:border-tinta-700 text-tinta-700 dark:text-tinta-200 hover:bg-tinta-50 dark:hover:bg-tinta-800 rounded-xl border px-3.5 py-2 text-sm font-medium transition"
          >
            {abierto ? 'Cerrar' : 'Roles'}
          </button>
        </div>
      </div>

      {abierto && (
        <div className="border-tinta-200 dark:border-tinta-800 space-y-4 border-t px-5 py-5">
          {error && <Aviso codigo={error.codigo} mensaje={error.message} />}

          {asignaciones === null ? (
            <p className="text-tinta-500 text-sm">Cargando…</p>
          ) : asignaciones.length === 0 ? (
            <p className="text-tinta-500 text-sm">
              Este usuario no tiene ningún rol asignado, así que no puede hacer
              nada dentro del sistema.
            </p>
          ) : (
            <ul className="space-y-2">
              {asignaciones.map((asignacion) => (
                <li
                  key={asignacion.id}
                  className="border-tinta-200 dark:border-tinta-800 flex flex-wrap items-center gap-3 rounded-xl border px-3.5 py-2.5"
                >
                  <span className="text-tinta-800 dark:text-tinta-100 min-w-0 flex-1 truncate text-sm font-medium">
                    {asignacion.role_name}
                    <span className="text-tinta-500 font-normal">
                      {' '}
                      · {asignacion.role_code}
                    </span>
                  </span>

                  {puedeAsignar && (
                    <button
                      type="button"
                      onClick={() => revocar(asignacion)}
                      disabled={trabajando}
                      className="text-alerta-600 dark:text-alerta-500 hover:bg-alerta-50 dark:hover:bg-alerta-500/10 rounded-lg px-3 py-1.5 text-sm font-medium transition disabled:opacity-60"
                    >
                      Quitar
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}

          {puedeAsignar && (
            <div className="flex flex-wrap items-center gap-3">
              <select
                value={elegido}
                onChange={(e) => setElegido(e.target.value)}
                className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900/60 dark:text-tinta-50 focus:border-marca-500 focus:ring-marca-500/25 rounded-xl border bg-white px-3.5 py-2.5 text-[0.9375rem] focus:ring-4 focus:outline-none"
              >
                <option value="">Elegí un rol para agregar…</option>
                {disponibles.map((rol) => (
                  <option key={rol.id} value={rol.id}>
                    {rol.name}
                  </option>
                ))}
              </select>

              <button
                type="button"
                onClick={asignar}
                disabled={!elegido || trabajando}
                className="bg-marca-600 hover:bg-marca-700 rounded-xl px-4 py-2.5 text-[0.9375rem] font-semibold text-white transition disabled:pointer-events-none disabled:opacity-60"
              >
                Asignar
              </button>
            </div>
          )}
        </div>
      )}
    </li>
  )
}
