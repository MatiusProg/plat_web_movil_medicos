/**
 * US-50 — La contabilidad: ingresos, devoluciones, comisión, honorarios,
 * gastos y utilidad.
 *
 *   GET  /api/reporting/finance/summary/     tarjetas, grupos y comparación
 *   GET  /api/reporting/finance/series/      los últimos 6 meses
 *   GET  /api/reporting/finance/export/      la tabla en CSV, Excel o PDF
 *   POST /api/reporting/finance/interpret/   de la frase a la cifra
 *   CRUD /api/reporting/finance/expenses/    los gastos
 *   GET/PUT /api/reporting/finance/settings/ la comisión de la pasarela
 *
 * Todo el cálculo es del backend: acá solo se muestra. Los montos llegan como
 * texto («150.50») y van **por moneda**, nunca mezclados. Es de los planes Pro
 * y Premium: sin la función responde 403 `plan_limit` (ver `esErrorDePlan`).
 */
import { descargarArchivo, pedir, type Contexto } from './cliente'

export type Agrupacion = 'sede' | 'medico' | 'especialidad' | 'dia' | 'semana' | 'mes' | 'trimestre'

export const AGRUPACIONES: { valor: Agrupacion; etiqueta: string }[] = [
  { valor: 'sede', etiqueta: 'Sede' },
  { valor: 'medico', etiqueta: 'Médico' },
  { valor: 'especialidad', etiqueta: 'Especialidad' },
  { valor: 'dia', etiqueta: 'Día' },
  { valor: 'semana', etiqueta: 'Semana' },
  { valor: 'mes', etiqueta: 'Mes' },
  { valor: 'trimestre', etiqueta: 'Trimestre (3 meses)' },
]

export interface Cifras {
  ingresos: string
  devoluciones: string
  neto: string
  comision: string
  honorarios: string
  gastos: string
  utilidad: string
  pagos: number
  ticket_promedio: string | null
}

export type Campo = 'ingresos' | 'devoluciones' | 'comision' | 'honorarios' | 'gastos' | 'utilidad'

export interface Grupo extends Cifras {
  key: string
  label: string
}

export interface Comparacion {
  previous_totals: Cifras
  /** Porcentaje como texto, o `null` si el período anterior estaba en cero. */
  change_percent: Record<Campo, string | null>
}

export interface PorMoneda {
  currency: string
  totals: Cifras
  groups: Grupo[]
  compare?: Comparacion
}

export interface Resumen {
  plataforma?: boolean
  range: { from: string; to: string; timezone: string }
  previous_range?: { from: string; to: string }
  group_by: Agrupacion | null
  commission_percent: string
  currencies: PorMoneda[]
}

export interface Serie {
  months: string[]
  currencies: { currency: string; months: (Pick<Cifras, 'ingresos' | 'devoluciones' | 'gastos' | 'utilidad'> & { month: string })[] }[]
}

export interface Filtros {
  desde: string
  hasta: string
  sucursal?: string
  profesional?: string
  agrupar?: Agrupacion | ''
  comparar?: boolean
}

function parametros(f: Filtros, extra: Record<string, string> = {}) {
  const q = new URLSearchParams({ from: f.desde, to: f.hasta, ...extra })
  if (f.sucursal) q.set('branch', f.sucursal)
  if (f.profesional) q.set('practitioner', f.profesional)
  if (f.agrupar) q.set('group', f.agrupar)
  if (f.comparar) q.set('compare', '1')
  return q
}

const RUTA = '/reporting/finance'

export const verResumen = (f: Filtros, contexto: Contexto, senal?: AbortSignal) =>
  pedir<Resumen>(`${RUTA}/summary/?${parametros(f)}`, { ...contexto, senal })

export const verSerie = (f: Pick<Filtros, 'desde' | 'hasta' | 'sucursal' | 'profesional'>, contexto: Contexto, senal?: AbortSignal) =>
  pedir<Serie>(`${RUTA}/series/?${parametros({ ...f, agrupar: '' })}`, { ...contexto, senal })

export type FormatoArchivo = 'csv' | 'xlsx' | 'pdf'

/** Baja la tabla. Devuelve el nombre con el que se guardó. */
export const descargarContabilidad = (f: Filtros, formato: FormatoArchivo, contexto: Contexto) =>
  descargarArchivo(`${RUTA}/export/?${parametros(f, { file: formato })}`, contexto, `contabilidad.${formato}`)

// ---- La voz --------------------------------------------------------------------------

export type Metrica = 'utilidad' | 'ingresos' | 'devoluciones' | 'honorarios' | 'comision' | 'gastos' | 'ticket_promedio'

export interface ConsultaDeVoz {
  metrica: Metrica
  /** AAAA-MM-DD */
  desde: string
  hasta: string
  agrupar: Agrupacion | null
  sede: string | null
  sede_nombre: string | null
  profesional: string | null
  profesional_nombre: string | null
  comparar: boolean
}

export interface RespuestaDeVoz {
  understood: boolean
  query: ConsultaDeVoz | null
  result: Resumen | null
  /** La respuesta en una frase, armada por el backend con sus propias cifras. */
  spoken_summary: string
  unresolved: string[]
  generated_by: 'gemini' | 'plantilla'
}

export const preguntarPorVoz = (texto: string, contexto: Contexto) =>
  pedir<RespuestaDeVoz>(`${RUTA}/interpret/`, { ...contexto, metodo: 'POST', cuerpo: { text: texto } })

// ---- Gastos ----------------------------------------------------------------------------

export type Categoria = 'insumos' | 'alquiler' | 'sueldos' | 'servicios' | 'otros'

export const CATEGORIAS: { valor: Categoria; etiqueta: string }[] = [
  { valor: 'insumos', etiqueta: 'Insumos' },
  { valor: 'alquiler', etiqueta: 'Alquiler' },
  { valor: 'sueldos', etiqueta: 'Sueldos' },
  { valor: 'servicios', etiqueta: 'Servicios' },
  { valor: 'otros', etiqueta: 'Otros' },
]

export interface Gasto {
  id: string
  branch: string | null
  branch_name: string | null
  category: Categoria
  category_label: string
  amount: string
  currency: string
  spent_on: string
  note: string
  created_at: string
}

export interface GastoNuevo {
  branch: string | null
  category: Categoria
  amount: string
  currency: string
  spent_on: string
  note: string
}

export const listarGastos = (
  f: Pick<Filtros, 'desde' | 'hasta' | 'sucursal'>,
  categoria: Categoria | '',
  contexto: Contexto,
  senal?: AbortSignal,
) => {
  const q = new URLSearchParams({ from: f.desde, to: f.hasta })
  if (f.sucursal) q.set('branch', f.sucursal)
  if (categoria) q.set('category', categoria)
  return pedir<Gasto[]>(`${RUTA}/expenses/?${q}`, { ...contexto, senal })
}

export const crearGasto = (gasto: GastoNuevo, contexto: Contexto) =>
  pedir<Gasto>(`${RUTA}/expenses/`, { ...contexto, metodo: 'POST', cuerpo: gasto })

export const editarGasto = (id: string, cambios: Partial<GastoNuevo>, contexto: Contexto) =>
  pedir<Gasto>(`${RUTA}/expenses/${id}/`, { ...contexto, metodo: 'PATCH', cuerpo: cambios })

export const borrarGasto = (id: string, contexto: Contexto) =>
  pedir<void>(`${RUTA}/expenses/${id}/`, { ...contexto, metodo: 'DELETE' })

// ---- Comisión de la pasarela -----------------------------------------------------------

export const verComision = (contexto: Contexto, senal?: AbortSignal) =>
  pedir<{ stripe_percent: string }>(`${RUTA}/settings/`, { ...contexto, senal })

export const guardarComision = (porcentaje: string, contexto: Contexto) =>
  pedir<{ stripe_percent: string }>(`${RUTA}/settings/`, {
    ...contexto, metodo: 'PUT', cuerpo: { stripe_percent: porcentaje },
  })
