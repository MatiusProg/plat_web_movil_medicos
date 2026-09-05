/**
 * US-04 — Roles de la organización y sus permisos (RF-W-02).
 *
 * La pantalla la ve quien tiene `users.role.read`. Los botones de alta,
 * edición y baja aparecen sólo con su permiso, pero **la puerta real la pone
 * el backend**: esconder un botón no autoriza nada, y cada endpoint exige su
 * propio código de permiso.
 *
 * A diferencia de las pantallas de plataforma, acá sí se mira `permissions` y
 * no `is_platform_admin`: el Superadministrador no administra los roles de
 * ningún inquilino —su rol sólo lleva permisos del módulo `platform`— y esta
 * pantalla no es suya.
 */

import { useEffect, useMemo, useState } from 'react'

import {
  crearRol,
  editarRol,
  eliminarRol,
  guardarPermisosDelRol,
  listarPermisos,
  listarRoles,
  type Permiso,
  type Rol,
} from '@/api/roles'
import { ErrorApi } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { Boton } from '@/componentes/Boton'
import { Campo } from '@/componentes/Campo'
import { IconoEscudo } from '@/componentes/iconos'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'

/** Cómo se llama cada módulo en la pantalla. El código es en inglés; esto no. */
const MODULOS: Record<string, string> = {
  users: 'Usuarios y seguridad',
  catalog: 'Catálogo del centro médico',
  patients: 'Pacientes',
  scheduling: 'Agendas y disponibilidad',
}

export function Roles() {
  const { token, puede } = useSesion()
  useTitulo('Roles y permisos')

  const [roles, setRoles] = useState<Rol[] | null>(null)
  const [permisos, setPermisos] = useState<Permiso[]>([])
  const [error, setError] = useState<ErrorApi | null>(null)
  const [enEdicion, setEnEdicion] = useState<Rol | null>(null)
  const [creando, setCreando] = useState(false)

  const puedeCrear = puede('users.role.create')
  const puedeEditar = puede('users.role.update')
  const puedeEliminar = puede('users.role.delete')

  useEffect(() => {
    const control = new AbortController()

    Promise.all([
      listarRoles({ token }, control.signal),
      listarPermisos({ token }, control.signal),
    ])
      .then(([pagina, catalogo]) => {
        setRoles(pagina.results)
        setPermisos(catalogo)
      })
      .catch((e: unknown) => {
        if (e instanceof DOMException && e.name === 'AbortError') return
        setError(e instanceof ErrorApi ? e : null)
        setRoles([])
      })

    return () => control.abort()
  }, [token])

  const reemplazar = (rol: Rol) =>
    setRoles((actuales) =>
      (actuales ?? []).map((uno) => (uno.id === rol.id ? rol : uno)),
    )

  const quitar = (id: string) =>
    setRoles((actuales) => (actuales ?? []).filter((uno) => uno.id !== id))

  const borrar = async (rol: Rol) => {
    setError(null)
    try {
      await eliminarRol(rol.id, { token })
      quitar(rol.id)
      if (enEdicion?.id === rol.id) setEnEdicion(null)
    } catch (e: unknown) {
      setError(e instanceof ErrorApi ? e : null)
    }
  }

  if (!puede('users.role.read')) {
    return (
      <main className="mx-auto max-w-4xl px-5 py-10">
        <p className="text-tinta-500 text-[0.9375rem]">
          No tenés permiso para ver los roles de la organización.
        </p>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-5xl space-y-6 px-5 py-10">
      <div className="surgir flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-marca-700 dark:text-marca-400 text-sm font-medium">
            Usuarios y seguridad
          </p>
          <h1 className="text-tinta-900 dark:text-tinta-50 mt-1 text-2xl font-semibold tracking-tight">
            Roles y permisos
          </h1>
          <p className="text-tinta-500 mt-1.5 text-[0.9375rem]">
            Cada rol reúne los permisos que una persona necesita para trabajar.
            Los cuatro que trae la organización se pueden ajustar; también podés
            crear los tuyos.
          </p>
        </div>

        {puedeCrear && (
          <button
            type="button"
            onClick={() => {
              setCreando(true)
              setEnEdicion(null)
            }}
            className="bg-marca-600 hover:bg-marca-700 focus-visible:outline-marca-600 inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-[0.9375rem] font-semibold text-white transition focus-visible:outline-2 focus-visible:outline-offset-2"
          >
            Crear rol
          </button>
        )}
      </div>

      {error && <Aviso codigo={error.codigo} mensaje={error.message} />}

      {creando && (
        <FormularioDeRol
          permisos={permisos}
          alCancelar={() => setCreando(false)}
          alGuardar={async (datos) => {
            const rol = await crearRol(datos, { token })
            setRoles((actuales) => [...(actuales ?? []), rol])
            setCreando(false)
          }}
        />
      )}

      {roles === null ? (
        <p className="text-tinta-500 text-[0.9375rem]">Cargando…</p>
      ) : roles.length === 0 && !error ? (
        <div className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 rounded-2xl border bg-white px-5 py-10 text-center">
          <span className="bg-tinta-100 dark:bg-tinta-800 text-tinta-400 mx-auto grid size-11 place-items-center rounded-xl">
            <IconoEscudo className="size-5" />
          </span>
          <p className="text-tinta-600 dark:text-tinta-300 mt-3 text-[0.9375rem] font-medium">
            La organización todavía no tiene roles.
          </p>
        </div>
      ) : (
        <ul className="space-y-3">
          {roles.map((rol) => (
            <Fila
              key={rol.id}
              rol={rol}
              abierto={enEdicion?.id === rol.id}
              puedeEditar={puedeEditar}
              puedeEliminar={puedeEliminar}
              alAbrir={() => {
                setCreando(false)
                setEnEdicion(enEdicion?.id === rol.id ? null : rol)
              }}
              alEliminar={() => borrar(rol)}
            >
              <PanelDePermisos
                rol={rol}
                permisos={permisos}
                soloLectura={!puedeEditar}
                alGuardar={async (codigos) => {
                  const actualizado = await guardarPermisosDelRol(
                    rol.id,
                    codigos,
                    { token },
                  )
                  reemplazar(actualizado)
                  setEnEdicion(actualizado)
                }}
                alRenombrar={async (datos) => {
                  const actualizado = await editarRol(rol.id, datos, { token })
                  reemplazar(actualizado)
                  setEnEdicion(actualizado)
                }}
              />
            </Fila>
          ))}
        </ul>
      )}
    </main>
  )
}

function Fila({
  rol,
  abierto,
  puedeEditar,
  puedeEliminar,
  alAbrir,
  alEliminar,
  children,
}: {
  rol: Rol
  abierto: boolean
  puedeEditar: boolean
  puedeEliminar: boolean
  alAbrir: () => void
  alEliminar: () => void
  children: React.ReactNode
}) {
  return (
    <li className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 rounded-2xl border bg-white">
      <div className="flex flex-wrap items-center gap-4 px-5 py-4">
        <span className="bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-400 grid size-10 shrink-0 place-items-center rounded-xl">
          <IconoEscudo className="size-5" />
        </span>

        <div className="min-w-0 flex-1">
          <p className="text-tinta-900 dark:text-tinta-50 truncate font-medium">
            {rol.name}
            {!rol.is_active && (
              <span className="text-tinta-500 bg-tinta-100 dark:bg-tinta-800 ml-2 rounded-lg px-2 py-0.5 text-xs font-medium">
                Inactivo
              </span>
            )}
          </p>
          <p className="text-tinta-500 truncate text-sm">
            {rol.code} · {rol.permissions.length} permiso(s) ·{' '}
            {rol.assigned_users} usuario(s)
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={alAbrir}
            className="border-tinta-300 dark:border-tinta-700 text-tinta-700 dark:text-tinta-200 hover:bg-tinta-50 dark:hover:bg-tinta-800 rounded-xl border px-3.5 py-2 text-sm font-medium transition"
          >
            {abierto ? 'Cerrar' : puedeEditar ? 'Permisos' : 'Ver permisos'}
          </button>

          {puedeEliminar && (
            <button
              type="button"
              onClick={alEliminar}
              className="text-alerta-600 dark:text-alerta-500 hover:bg-alerta-50 dark:hover:bg-alerta-500/10 rounded-xl px-3.5 py-2 text-sm font-medium transition"
            >
              Eliminar
            </button>
          )}
        </div>
      </div>

      {abierto && (
        <div className="border-tinta-200 dark:border-tinta-800 border-t px-5 py-5">
          {children}
        </div>
      )}
    </li>
  )
}

/**
 * Las casillas de permisos de un rol, agrupadas por módulo.
 *
 * Guarda el conjunto **completo**, no lo que cambió: es lo que espera el PUT
 * del backend, y es lo que permite revocar. Mientras no se guarda, lo marcado
 * vive en el estado local; si se cierra el panel, no pasó nada.
 */
function PanelDePermisos({
  rol,
  permisos,
  soloLectura,
  alGuardar,
  alRenombrar,
}: {
  rol: Rol
  permisos: Permiso[]
  soloLectura: boolean
  alGuardar: (codigos: string[]) => Promise<void>
  alRenombrar: (datos: { name: string; description: string }) => Promise<void>
}) {
  const [marcados, setMarcados] = useState<Set<string>>(
    () => new Set(rol.permissions),
  )
  const [nombre, setNombre] = useState(rol.name)
  const [descripcion, setDescripcion] = useState(rol.description)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState<ErrorApi | null>(null)
  const [guardado, setGuardado] = useState(false)

  const porModulo = useMemo(() => {
    const grupos = new Map<string, Permiso[]>()
    for (const permiso of permisos) {
      const actuales = grupos.get(permiso.module) ?? []
      actuales.push(permiso)
      grupos.set(permiso.module, actuales)
    }
    return [...grupos.entries()]
  }, [permisos])

  const alternar = (code: string) => {
    setGuardado(false)
    setMarcados((actuales) => {
      const siguiente = new Set(actuales)
      if (siguiente.has(code)) siguiente.delete(code)
      else siguiente.add(code)
      return siguiente
    })
  }

  const guardar = async () => {
    setGuardando(true)
    setError(null)
    setGuardado(false)
    try {
      if (nombre !== rol.name || descripcion !== rol.description) {
        await alRenombrar({ name: nombre, description: descripcion })
      }
      await alGuardar([...marcados])
      setGuardado(true)
    } catch (e: unknown) {
      setError(e instanceof ErrorApi ? e : null)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="space-y-5">
      {error && <Aviso codigo={error.codigo} mensaje={error.message} />}

      {!soloLectura && (
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo
            etiqueta="Nombre"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            maxLength={80}
          />
          <Campo
            etiqueta="Descripción"
            value={descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
            maxLength={200}
            ayuda="Para qué sirve este rol dentro del centro médico."
          />
        </div>
      )}

      <div className="space-y-5">
        {porModulo.map(([modulo, delModulo]) => (
          <fieldset key={modulo}>
            <legend className="text-tinta-700 dark:text-tinta-300 text-sm font-semibold">
              {MODULOS[modulo] ?? modulo}
            </legend>

            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {delModulo.map((permiso) => (
                <label
                  key={permiso.id}
                  className="border-tinta-200 dark:border-tinta-800 hover:bg-tinta-50 dark:hover:bg-tinta-800/50 flex cursor-pointer items-start gap-3 rounded-xl border px-3.5 py-2.5"
                >
                  <input
                    type="checkbox"
                    checked={marcados.has(permiso.code)}
                    disabled={soloLectura}
                    onChange={() => alternar(permiso.code)}
                    className="accent-marca-600 mt-0.5 size-4 shrink-0"
                  />
                  <span className="min-w-0">
                    <span className="text-tinta-800 dark:text-tinta-100 block text-sm font-medium">
                      {permiso.description || permiso.code}
                    </span>
                    <span className="text-tinta-500 block truncate text-xs">
                      {permiso.code}
                    </span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
        ))}
      </div>

      {!soloLectura && (
        <div className="flex items-center gap-3">
          <Boton
            type="button"
            onClick={guardar}
            cargando={guardando}
            textoCargando="Guardando…"
            className="w-auto"
          >
            Guardar permisos
          </Boton>

          {guardado && (
            <span className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
              Guardado.
            </span>
          )}
        </div>
      )}
    </div>
  )
}

/** El formulario de alta. Pide lo mínimo; los permisos se ajustan después. */
function FormularioDeRol({
  permisos,
  alGuardar,
  alCancelar,
}: {
  permisos: Permiso[]
  alGuardar: (datos: {
    code: string
    name: string
    description: string
    permissions: string[]
  }) => Promise<void>
  alCancelar: () => void
}) {
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [marcados, setMarcados] = useState<Set<string>>(new Set())
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState<ErrorApi | null>(null)

  const enviar = async (evento: React.FormEvent) => {
    evento.preventDefault()
    setGuardando(true)
    setError(null)
    try {
      await alGuardar({ code, name, description, permissions: [...marcados] })
    } catch (e: unknown) {
      setError(e instanceof ErrorApi ? e : null)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <form
      onSubmit={enviar}
      className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 space-y-5 rounded-2xl border bg-white px-5 py-5"
    >
      <h2 className="text-tinta-900 dark:text-tinta-50 text-lg font-semibold">
        Nuevo rol
      </h2>

      {error && (
        <Aviso
          codigo={error.codigo}
          mensaje={
            error.porCampo?.code?.[0] ??
            error.porCampo?.permissions?.[0] ??
            error.message
          }
        />
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Campo
          etiqueta="Código"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          required
          maxLength={40}
          placeholder="caja"
          error={error?.porCampo?.code?.[0]}
          ayuda="Minúsculas, números y guión bajo. No se puede repetir."
        />
        <Campo
          etiqueta="Nombre"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={80}
          placeholder="Caja"
        />
      </div>

      <Campo
        etiqueta="Descripción"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        maxLength={200}
        placeholder="Cobra fichas y cierra la caja del día."
      />

      <details className="border-tinta-200 dark:border-tinta-800 rounded-xl border px-4 py-3">
        <summary className="text-tinta-700 dark:text-tinta-300 cursor-pointer text-sm font-medium">
          Permisos ({marcados.size} marcado(s))
        </summary>

        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {permisos.map((permiso) => (
            <label
              key={permiso.id}
              className="text-tinta-700 dark:text-tinta-200 flex cursor-pointer items-start gap-3 text-sm"
            >
              <input
                type="checkbox"
                checked={marcados.has(permiso.code)}
                onChange={() =>
                  setMarcados((actuales) => {
                    const siguiente = new Set(actuales)
                    if (siguiente.has(permiso.code)) siguiente.delete(permiso.code)
                    else siguiente.add(permiso.code)
                    return siguiente
                  })
                }
                className="accent-marca-600 mt-0.5 size-4 shrink-0"
              />
              <span className="min-w-0 truncate">
                {permiso.description || permiso.code}
              </span>
            </label>
          ))}
        </div>
      </details>

      <div className="flex items-center gap-3">
        <Boton
          type="submit"
          cargando={guardando}
          textoCargando="Creando…"
          className="w-auto"
        >
          Crear rol
        </Boton>

        <button
          type="button"
          onClick={alCancelar}
          className="text-tinta-600 dark:text-tinta-300 hover:bg-tinta-100 dark:hover:bg-tinta-800 rounded-xl px-4 py-2.5 text-[0.9375rem] font-medium transition"
        >
          Cancelar
        </button>
      </div>
    </form>
  )
}
