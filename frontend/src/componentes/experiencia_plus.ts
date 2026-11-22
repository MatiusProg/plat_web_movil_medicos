/** US-51 — La cuenta regresiva de la ficha («Faltan 2 días…»). */

const DIA = 24 * 60 * 60 * 1000

/** Medianoche local del día de `fecha`, para contar días de calendario y no de 24 h. */
const dia = (fecha: Date) => new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate()).getTime()

/**
 * «Es hoy a las 10:00», «Es mañana a las 10:00», «Faltan 3 días»… o `null`
 * si la ficha ya pasó: no tiene sentido contar hacia atrás.
 */
export function cuentaRegresiva(inicio: string, ahora: Date = new Date()): string | null {
  const turno = new Date(inicio)
  if (turno.getTime() <= ahora.getTime()) return null
  const hora = turno.toLocaleTimeString('es-BO', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
  const dias = Math.round((dia(turno) - dia(ahora)) / DIA)
  if (dias === 0) return `Es hoy a las ${hora}`
  if (dias === 1) return `Es mañana a las ${hora}`
  return `Faltan ${dias} días`
}
