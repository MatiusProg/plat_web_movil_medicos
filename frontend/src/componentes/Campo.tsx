/**
 * Campo de formulario con etiqueta, icono, error y ayuda.
 *
 * Todo campo tiene un `<label>` real asociado por `htmlFor`, no un placeholder
 * haciendo de etiqueta: el placeholder desaparece al escribir, y quien usa
 * lector de pantalla o vuelve al formulario a medio llenar se queda sin saber
 * qué iba en cada casilla.
 */

import { useId, type InputHTMLAttributes, type ReactNode, type Ref } from 'react'

interface Props extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id'> {
  etiqueta: string
  error?: string
  ayuda?: ReactNode
  icono?: ReactNode
  /** Se dibuja pegado al borde derecho: el ojo de mostrar contraseña. */
  accion?: ReactNode
  /** Desde React 19 `ref` viaja como una prop más, sin `forwardRef`. */
  ref?: Ref<HTMLInputElement>
}

export function Campo({
  etiqueta,
  error,
  ayuda,
  icono,
  accion,
  className = '',
  ref,
  ...resto
}: Props) {
  const id = useId()
  const idAyuda = `${id}-ayuda`
  const idError = `${id}-error`

  return (
    <div className="space-y-1.5">
      <label
        htmlFor={id}
        className="text-tinta-700 dark:text-tinta-300 block text-sm font-medium"
      >
        {etiqueta}
      </label>

      <div className="relative">
        {icono && (
          <span
            className="text-tinta-400 pointer-events-none absolute inset-y-0 left-0 flex w-11 items-center justify-center"
            aria-hidden="true"
          >
            {icono}
          </span>
        )}

        <input
          id={id}
          ref={ref}
          aria-invalid={error ? true : undefined}
          aria-describedby={
            [error ? idError : null, ayuda ? idAyuda : null].filter(Boolean).join(' ') ||
            undefined
          }
          className={[
            'w-full rounded-xl border bg-white py-2.5 text-[0.9375rem] transition',
            'placeholder:text-tinta-400',
            'dark:bg-tinta-900/60 dark:text-tinta-50',
            icono ? 'pl-11' : 'pl-3.5',
            accion ? 'pr-11' : 'pr-3.5',
            error
              ? 'border-alerta-500 focus:border-alerta-500 focus:ring-alerta-500/25'
              : 'border-tinta-300 dark:border-tinta-700 focus:border-marca-500 focus:ring-marca-500/25',
            'focus:ring-4 focus:outline-none',
            'disabled:bg-tinta-100 disabled:text-tinta-500 dark:disabled:bg-tinta-900 disabled:cursor-not-allowed',
            className,
          ].join(' ')}
          {...resto}
        />

        {accion && (
          <span className="absolute inset-y-0 right-0 flex w-11 items-center justify-center">
            {accion}
          </span>
        )}
      </div>

      {error && (
        <p id={idError} className="text-alerta-600 dark:text-alerta-500 text-sm">
          {error}
        </p>
      )}
      {ayuda && !error && (
        <p id={idAyuda} className="text-tinta-500 text-sm">
          {ayuda}
        </p>
      )}
    </div>
  )
}
