/**
 * Botón con estado de carga.
 *
 * Mientras carga queda deshabilitado y conserva su ancho: si el texto se
 * reemplazara por un spinner a secas, el botón encogería y el layout saltaría
 * justo en el momento en que la persona está mirándolo.
 */

import type { ButtonHTMLAttributes, ReactNode } from 'react'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  cargando?: boolean
  /** Qué decir mientras carga. Lo anuncia el lector de pantalla. */
  textoCargando?: string
  children: ReactNode
}

export function Boton({
  cargando = false,
  textoCargando = 'Procesando…',
  children,
  className = '',
  disabled,
  ...resto
}: Props) {
  // Ancho completo por defecto, salvo que quien lo usa diga otro. No alcanza
  // con agregar `w-auto` al final: con `w-full` y `w-auto` juntas gana la que
  // Tailwind declara después en su CSS, que es `w-full`.
  const ancho = /(^|\s)w-/.test(className) ? '' : 'w-full'
  return (
    <button
      disabled={disabled || cargando}
      aria-busy={cargando || undefined}
      className={[
        'relative inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5',
        ancho,
        'text-sm font-semibold text-white',
        'bg-marca-600 hover:bg-marca-700 active:bg-marca-800',
        'shadow-sm transition-colors',
        'disabled:pointer-events-none disabled:opacity-60',
        'focus-visible:outline-marca-500 focus-visible:outline-2 focus-visible:outline-offset-2',
        className,
      ].join(' ')}
      {...resto}
    >
      {cargando && (
        <svg
          className="size-4 animate-spin"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="3"
          />
          <path
            className="opacity-90"
            fill="currentColor"
            d="M12 2a10 10 0 0 1 10 10h-3a7 7 0 0 0-7-7V2Z"
          />
        </svg>
      )}
      {/* inline-flex: el ícono y el texto en la misma línea. Con un span
          común, el ícono (que es un bloque) empujaba el texto abajo. */}
      <span className="inline-flex items-center gap-2">{cargando ? textoCargando : children}</span>
    </button>
  )
}
