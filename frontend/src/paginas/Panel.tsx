/**
 * Pantalla de aterrizaje después de iniciar sesión.
 *
 * **Es deliberadamente un lugar de paso.** US-02 termina cuando la sesión
 * queda abierta; lo que va acá adentro lo definen las historias de cada
 * módulo en los sprints siguientes. Lo que sí hace esta pantalla es demostrar
 * la parte de la historia que se suele dar por sentada —*"para acceder a las
 * funciones según mi rol"*—: muestra los roles y los permisos que devolvió el
 * backend, que es exactamente lo que va a decidir qué menú se dibuja.
 */

import { useState } from 'react'

import { Boton } from '@/componentes/Boton'
import { IconoEscudo, IconoPulso, IconoSalir } from '@/componentes/iconos'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'

export function Panel() {
  const { usuario, salir } = useSesion()
  const [saliendo, setSaliendo] = useState(false)
  useTitulo('Panel')

  if (!usuario) return null

  const alSalir = async () => {
    setSaliendo(true)
    await salir()
  }

  return (
    <div className="bg-tinta-50 dark:bg-tinta-950 min-h-dvh">
      <header className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 border-b bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-4 px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            <span className="bg-marca-600 grid size-8 place-items-center rounded-lg text-white">
              <IconoPulso className="size-4.5" />
            </span>
            <span className="text-tinta-800 dark:text-tinta-100 text-[0.9375rem] font-semibold">
              Centro Médico
            </span>
          </div>

          <button
            onClick={alSalir}
            disabled={saliendo}
            className="text-tinta-600 hover:bg-tinta-100 hover:text-tinta-900 dark:text-tinta-400 dark:hover:bg-tinta-800 dark:hover:text-tinta-100 inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition disabled:opacity-50"
          >
            <IconoSalir className="size-4.5" />
            {saliendo ? 'Saliendo…' : 'Cerrar sesión'}
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-6 px-5 py-10">
        <div className="surgir">
          <p className="text-marca-700 dark:text-marca-400 text-sm font-medium">
            Sesión iniciada
          </p>
          <h1 className="text-tinta-900 dark:text-tinta-50 mt-1 text-2xl font-semibold tracking-tight">
            Hola, {usuario.full_name}
          </h1>
          <p className="text-tinta-500 mt-1.5 text-[0.9375rem]">
            {usuario.is_platform_admin
              ? 'Estás administrando la plataforma.'
              : `Estás en ${usuario.organization}.`}
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Tarjeta titulo="Tus roles">
            {usuario.roles.length === 0 ? (
              <Vacio>Todavía no tenés ningún rol asignado.</Vacio>
            ) : (
              <ul className="flex flex-wrap gap-2">
                {usuario.roles.map((rol) => (
                  <li
                    key={rol.code}
                    className="bg-marca-50 text-marca-800 ring-marca-200 dark:bg-marca-950 dark:text-marca-200 dark:ring-marca-800 rounded-lg px-2.5 py-1 text-sm font-medium ring-1"
                  >
                    {rol.name}
                  </li>
                ))}
              </ul>
            )}
          </Tarjeta>

          <Tarjeta titulo="Tus permisos">
            {usuario.permissions.length === 0 ? (
              <Vacio>Sin permisos asignados.</Vacio>
            ) : (
              <ul className="space-y-1.5">
                {usuario.permissions.map((permiso) => (
                  <li
                    key={permiso}
                    className="text-tinta-600 dark:text-tinta-300 flex items-center gap-2 text-sm"
                  >
                    <IconoEscudo className="text-marca-500 size-4 shrink-0" />
                    <code className="cifras text-[0.8125rem]">{permiso}</code>
                  </li>
                ))}
              </ul>
            )}
          </Tarjeta>
        </div>

        <Tarjeta titulo="Tus datos">
          <dl className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2">
            <Dato termino="Correo" valor={usuario.email} />
            <Dato
              termino="Documento"
              valor={`${usuario.document_type} ${usuario.document_number}`}
            />
            <Dato termino="Centro médico" valor={usuario.organization ?? '—'} />
            <Dato
              termino="Nivel"
              valor={usuario.is_platform_admin ? 'Plataforma' : 'Organización'}
            />
          </dl>
        </Tarjeta>

        <div className="max-w-xs">
          <Boton onClick={alSalir} cargando={saliendo} textoCargando="Cerrando sesión…">
            Cerrar sesión
          </Boton>
        </div>
      </main>
    </div>
  )
}

function Tarjeta({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 rounded-2xl border bg-white p-5">
      <h2 className="text-tinta-400 mb-3 text-xs font-semibold tracking-wider uppercase">
        {titulo}
      </h2>
      {children}
    </section>
  )
}

function Dato({ termino, valor }: { termino: string; valor: string }) {
  return (
    <div>
      <dt className="text-tinta-400 text-xs">{termino}</dt>
      <dd className="text-tinta-700 dark:text-tinta-200 mt-0.5 font-medium">{valor}</dd>
    </div>
  )
}

function Vacio({ children }: { children: React.ReactNode }) {
  return <p className="text-tinta-400 text-sm italic">{children}</p>
}
