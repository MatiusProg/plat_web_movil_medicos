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

/**
 * Las gráficas de evolución: un signo (o la presión, que son dos líneas) a lo
 * largo de las atenciones firmadas. La franja es la de referencia de un
 * adulto; donde hay alerta, su borde es el mismo umbral que marca «Alta» o
 * «Baja». La glucosa no lleva franja: depende de si estaba en ayunas.
 */
export type IdSerie = 'presion' | 'heart_rate' | 'temperature' | 'spo2' | 'glucose' | 'weight_kg' | 'bmi'
type CampoSerie = CampoSigno | 'bmi'
export interface Serie {
  id: IdSerie
  etiqueta: string
  unidad: string
  lineas: { campo: CampoSerie; etiqueta: string; franja?: [number, number] }[]
}

export const SERIES: Serie[] = [
  { id: 'presion', etiqueta: 'Presión arterial', unidad: 'mmHg', lineas: [
    { campo: 'systolic', etiqueta: 'Sistólica', franja: [90, 140] },
    { campo: 'diastolic', etiqueta: 'Diastólica', franja: [60, 90] },
  ] },
  { id: 'heart_rate', etiqueta: 'Frecuencia cardíaca', unidad: 'lpm', lineas: [{ campo: 'heart_rate', etiqueta: 'Frecuencia', franja: [60, 100] }] },
  { id: 'temperature', etiqueta: 'Temperatura', unidad: '°C', lineas: [{ campo: 'temperature', etiqueta: 'Temperatura', franja: [36, 38] }] },
  { id: 'spo2', etiqueta: 'Saturación O₂', unidad: '%', lineas: [{ campo: 'spo2', etiqueta: 'Saturación', franja: [92, 100] }] },
  { id: 'glucose', etiqueta: 'Glucosa', unidad: 'mg/dL', lineas: [{ campo: 'glucose', etiqueta: 'Glucosa' }] },
  { id: 'weight_kg', etiqueta: 'Peso', unidad: 'kg', lineas: [{ campo: 'weight_kg', etiqueta: 'Peso' }] },
  { id: 'bmi', etiqueta: 'IMC', unidad: '', lineas: [{ campo: 'bmi', etiqueta: 'IMC', franja: [18.5, 25] }] },
]

/** Lo mínimo de una atención que necesitan las gráficas. */
export interface ConSignos {
  id: string
  appointment_starts_at: string
  vital_signs: SignosVitales | null
  amendments: { section: string }[]
}

export interface Punto {
  encuentro: string
  fecha: string
  /** Un valor por línea de la serie; `null` si esa vez no se tomó. */
  valores: (number | null)[]
  /** El médico corrigió los signos de esa atención con una enmienda. */
  enmendado: boolean
}

/** Las atenciones con algún valor de la serie, de la más vieja a la más nueva. */
export function puntosDe(serie: Serie, encuentros: ConSignos[]): Punto[] {
  return encuentros
    .filter(e => e.vital_signs && serie.lineas.some(l => e.vital_signs![l.campo] != null))
    .map(e => ({
      encuentro: e.id,
      fecha: e.appointment_starts_at,
      valores: serie.lineas.map(l => e.vital_signs![l.campo]),
      enmendado: e.amendments.some(a => a.section === 'vital_signs'),
    }))
    .sort((a, b) => a.fecha.localeCompare(b.fecha))
}

/** La última medición: la atención más nueva que tiene signos. */
export function ultimaMedicion<T extends ConSignos>(encuentros: T[]): T | null {
  return [...encuentros].filter(e => e.vital_signs)
    .sort((a, b) => b.appointment_starts_at.localeCompare(a.appointment_starts_at))[0] ?? null
}

const num = (v: number) => v.toLocaleString('es-BO', { maximumFractionDigits: 1 })

/** «PA 120/80 · FC 72 · T 36,5 °C · SpO₂ 98 % · IMC 24,1», con lo anormal aparte. */
export function filaCompacta(s: SignosVitales): { texto: string; alerta?: string }[] {
  const partes: { texto: string; alerta?: string }[] = []
  if (s.systolic != null || s.diastolic != null)
    partes.push({ texto: `PA ${s.systolic ?? '—'}/${s.diastolic ?? '—'}`, alerta: s.alerts.blood_pressure })
  if (s.heart_rate != null) partes.push({ texto: `FC ${s.heart_rate}` })
  if (s.temperature != null) partes.push({ texto: `T ${num(s.temperature)} °C`, alerta: s.alerts.temperature })
  if (s.spo2 != null) partes.push({ texto: `SpO₂ ${s.spo2} %`, alerta: s.alerts.spo2 })
  if (s.glucose != null) partes.push({ texto: `Glu ${s.glucose} mg/dL` })
  if (s.weight_kg != null) partes.push({ texto: `Peso ${num(s.weight_kg)} kg` })
  if (s.height_cm != null) partes.push({ texto: `Talla ${num(s.height_cm)} cm` })
  if (s.bmi != null) partes.push({ texto: `IMC ${num(s.bmi)}` })
  return partes
}
