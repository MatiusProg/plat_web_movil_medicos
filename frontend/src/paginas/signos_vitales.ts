/** US-53 — Leer, validar y calcular los signos vitales (ver `SignosVitales.tsx`). */
import { SIGNOS, type CampoSigno, type DatosSignos, type SignosVitales } from '@/api/atencion'

export type TextosSignos = Record<CampoSigno, string>

export const SIN_SIGNOS: TextosSignos = Object.fromEntries(SIGNOS.map(s => [s.campo, ''])) as TextosSignos

export const aTextos = (signos: SignosVitales | null): TextosSignos =>
  signos ? Object.fromEntries(SIGNOS.map(s => [s.campo, signos[s.campo] == null ? '' : String(signos[s.campo])])) as TextosSignos
    : SIN_SIGNOS

export const mismosSignos = (a: TextosSignos, b: TextosSignos) =>
  SIGNOS.every(s => a[s.campo].trim() === b[s.campo].trim())

/** Lee lo escrito: los números (con coma o punto) y los errores por campo. */
export function leerSignos(textos: TextosSignos): { datos: DatosSignos | null; errores: Partial<Record<CampoSigno, string>> } {
  const datos: DatosSignos = {}
  const errores: Partial<Record<CampoSigno, string>> = {}
  for (const s of SIGNOS) {
    const texto = textos[s.campo].trim().replace(',', '.')
    if (!texto) { datos[s.campo] = null; continue }
    const valor = Number(texto)
    if (!/^\d+(\.\d+)?$/.test(texto) || Number.isNaN(valor)) { errores[s.campo] = 'Escribe un número.'; continue }
    if (!s.decimales && !Number.isInteger(valor)) { errores[s.campo] = 'Sin decimales.'; continue }
    if (s.decimales && !/^\d+(\.\d)?$/.test(texto)) { errores[s.campo] = 'Con un decimal como máximo.'; continue }
    if (valor < s.min) { errores[s.campo] = `El mínimo posible es ${s.min}.`; continue }
    if (valor > s.max) { errores[s.campo] = `El máximo posible es ${s.max}.`; continue }
    datos[s.campo] = valor
  }
  const { systolic, diastolic } = datos
  if (systolic != null && diastolic != null && systolic <= diastolic && !errores.diastolic)
    errores.diastolic = 'Tiene que ser menor que la sistólica.'
  const vacio = SIGNOS.every(s => datos[s.campo] == null)
  return { datos: vacio ? null : datos, errores }
}

/** Lo mismo que `VitalSigns.alerts` y `bmi` del backend, para verlo al escribir. */
export function calcular(d: DatosSignos | null): Pick<SignosVitales, 'bmi' | 'alerts'> {
  const alerts: SignosVitales['alerts'] = {}
  if (!d) return { bmi: null, alerts }
  if ((d.systolic ?? 0) >= 140 || (d.diastolic ?? 0) >= 90) alerts.blood_pressure = 'Alta'
  if (d.spo2 != null && d.spo2 < 92) alerts.spo2 = 'Baja'
  if (d.temperature != null && d.temperature >= 38) alerts.temperature = 'Alta'
  const bmi = d.weight_kg != null && d.height_cm != null
    ? Math.round((d.weight_kg / (d.height_cm / 100) ** 2) * 10) / 10 : null
  return { bmi, alerts }
}
