/**
 * La barra superior, compartida por todas las pantallas con sesión.
 *
 * Estaba escrita dentro de `Panel`; se extrajo al agregar la segunda pantalla,
 * porque si no la aplicación tendría dos cabeceras distintas y la navegación
 * viviría en una sola.
 *
 * **Cada historia agrega su enlace en `ENLACES`.** Es el único archivo del
 * frontend que varias historias comparten, así que conviene que cada una toque
 * su línea y no la de al lado — la misma regla que `urls.py` en el backend.
 */

import { NavLink } from 'react-router-dom'
import { useState } from 'react'

import { IconoPulso, IconoSalir } from '@/componentes/iconos'
import type { UsuarioSesion } from '@/api/tipos'
import { useSesion } from '@/sesion/useSesion'

interface Enlace {
  a: string
  texto: string
  /** Quién lo ve. Devuelve `true` si el enlace corresponde a esta persona. */
  visible: (usuario: UsuarioSesion) => boolean
}

const ENLACES: Enlace[] = [
  { a: '/panel', texto: 'Panel', visible: () => true },
  // ---------- US-43 (Luis Mateo): alta de organizaciones ------------------
  // Mira `is_platform_admin` y no `puede(...)`: los permisos del
  // superadministrador llegan vacíos. El porqué está en `sesion/contexto.ts`.
  {
    a: '/organizaciones',
    texto: 'Organizaciones',
    visible: (usuario) => usuario.is_platform_admin,
  },
]

export function Cabecera() {
  const { usuario, salir } = useSesion()
  const [saliendo, setSaliendo] = useState(false)

  if (!usuario) return null

  const alSalir = async () => {
    setSaliendo(true)
    await salir()
  }

  return (
    <header className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 border-b bg-white">
      <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-5 py-3.5">
        <div className="flex items-center gap-2.5">
          <span className="bg-marca-600 grid size-8 place-items-center rounded-lg text-white">
            <IconoPulso className="size-4.5" />
          </span>
          <span className="text-tinta-800 dark:text-tinta-100 text-[0.9375rem] font-semibold">
            Centro Médico
          </span>
        </div>

        <nav className="order-3 flex items-center gap-1 sm:order-none">
          {ENLACES.filter((enlace) => enlace.visible(usuario)).map((enlace) => (
            <NavLink
              key={enlace.a}
              to={enlace.a}
              className={({ isActive }) =>
                [
                  'rounded-lg px-3 py-1.5 text-sm font-medium transition',
                  isActive
                    ? 'bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-400'
                    : 'text-tinta-600 hover:bg-tinta-100 hover:text-tinta-900 dark:text-tinta-400 dark:hover:bg-tinta-800 dark:hover:text-tinta-100',
                ].join(' ')
              }
            >
              {enlace.texto}
            </NavLink>
          ))}
        </nav>

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
  )
}
