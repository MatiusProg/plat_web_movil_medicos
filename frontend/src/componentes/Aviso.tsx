/**
 * El cartel de error del formulario.
 *
 * Va con `role="alert"`, así que un lector de pantalla lo anuncia en cuanto
 * aparece. Sin eso, quien no ve la pantalla aprieta "Entrar", no pasa nada
 * visible para él y no tiene forma de enterarse de que hubo un error.
 *
 * El bloqueo se pinta en ámbar y no en rojo a propósito: no es un dato mal
 * escrito ni una cuenta comprometida, es una espera. Y lleva su cuenta
 * regresiva, porque "intentá más tarde" sin decir cuánto es la clase de
 * mensaje que hace que la gente llame a recepción.
 */

import { useEffect, useState } from 'react'

import type { CodigoError } from '@/api/tipos'
import { IconoAlerta, IconoCandado, IconoSinConexion } from './iconos'

interface Props {
  codigo: CodigoError
  mensaje: string
  /** ISO 8601. Sólo viene en `cuenta_bloqueada`. */
  bloqueadaHasta?: string
  /** Se llama cuando vence el bloqueo, para volver a habilitar el formulario. */
  alVencer?: () => void
}

export function Aviso({ codigo, mensaje, bloqueadaHasta, alVencer }: Props) {
  const bloqueo = codigo === 'cuenta_bloqueada'
  const sinRed = codigo === 'sin_conexion'

  const tono = bloqueo
    ? 'border-espera-200 bg-espera-50 text-espera-700 dark:border-espera-600/40 dark:bg-espera-600/10 dark:text-espera-200'
    : 'border-alerta-200 bg-alerta-50 text-alerta-700 dark:border-alerta-500/40 dark:bg-alerta-500/10 dark:text-alerta-200'

  const Icono = bloqueo ? IconoCandado : sinRed ? IconoSinConexion : IconoAlerta

  return (
    <div
      role="alert"
      className={`surgir flex gap-3 rounded-xl border px-3.5 py-3 text-sm ${tono}`}
    >
      <Icono className="mt-px size-5 shrink-0" />
      <div className="space-y-1">
        <p>{mensaje}</p>
        {bloqueo && bloqueadaHasta && (
          // La `key` remonta el contador si llega un vencimiento distinto. Sin
          // ella habría que resincronizar el estado desde un efecto, que es
          // justo lo que React desaconseja.
          <CuentaRegresiva
            key={bloqueadaHasta}
            hasta={bloqueadaHasta}
            alVencer={alVencer}
          />
        )}
        {sinRed && (
          <p className="opacity-80">
            Arrancalo con <code className="cifras">python manage.py runserver</code>.
          </p>
        )}
      </div>
    </div>
  )
}

function CuentaRegresiva({ hasta, alVencer }: { hasta: string; alVencer?: () => void }) {
  const [restante, setRestante] = useState(() => segundosHasta(hasta))

  useEffect(() => {
    const reloj = window.setInterval(() => {
      const quedan = segundosHasta(hasta)
      setRestante(quedan)
      if (quedan <= 0) {
        window.clearInterval(reloj)
        alVencer?.()
      }
    }, 1000)
    return () => window.clearInterval(reloj)
  }, [hasta, alVencer])

  if (restante <= 0) {
    return <p className="font-medium">Ya podés volver a intentar.</p>
  }

  const minutos = Math.floor(restante / 60)
  const segundos = restante % 60

  return (
    <p className="font-medium">
      Podés reintentar en{' '}
      <span className="cifras tabular-nums">
        {String(minutos).padStart(2, '0')}:{String(segundos).padStart(2, '0')}
      </span>
    </p>
  )
}

function segundosHasta(iso: string): number {
  const faltan = Math.ceil((new Date(iso).getTime() - Date.now()) / 1000)
  return Number.isFinite(faltan) ? Math.max(0, faltan) : 0
}
