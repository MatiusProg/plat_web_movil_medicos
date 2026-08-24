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
  return (
    <button
      disabled={disabled || cargando}
      aria-busy={cargando || undefined}
      className={[
        'relative inline-flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5',
        'text-[0.9375rem] font-semibold text-white',
        'bg-marca-600 hover:bg-marca-700 active:bg-marca-800',
        'shadow-marca-900/20 shadow-lg transition',
        'hover:shadow-marca-900/30 hover:-translate-y-px hover:shadow-xl',
        'active:translate-y-0 active:shadow-md',
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
      <span>{cargando ? textoCargando : children}</span>
    </button>
  )
}
