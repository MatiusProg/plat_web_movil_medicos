/**
 * US-53 — Signos vitales de la atención.
 *
 * Se cargan con el borrador, en el mismo «Guardar», y se firman con él. Lo
 * **imposible** (60 °C, 3 m) no se deja guardar: es un error de tipeo. Lo
 * **anormal** (39 °C, 150/95) se guarda y se marca, porque existe y el médico
 * tiene que poder anotarlo. La base aplica los mismos límites
 * (`VITAL_LIMITS`); acá se repiten para avisar antes de mandar.
 */
import { SIGNOS, type CampoSigno, type SignosVitales } from '@/api/atencion'
import { INPUT } from './catalogo_comun'
import { calcular, leerSignos, type TextosSignos } from './signos_vitales'

const ALERTA_DE: Partial<Record<CampoSigno, keyof SignosVitales['alerts']>> = {
  systolic: 'blood_pressure', diastolic: 'blood_pressure', temperature: 'temperature', spo2: 'spo2',
}

function Marca({ texto }: { texto: string }) {
  return <span className="rounded-full bg-alerta-50 px-2 py-0.5 text-xs font-semibold text-alerta-700 dark:bg-alerta-500/10 dark:text-alerta-200">{texto}</span>
}

function Imc({ bmi }: { bmi: number | null }) {
  if (bmi == null) return null
  return <p className="text-sm text-tinta-600 dark:text-tinta-300">IMC <strong className="text-tinta-900 dark:text-tinta-50">{bmi.toLocaleString('es-BO')}</strong></p>
}

/** El editor, dentro del formulario del borrador. */
export function EditorSignos({ textos, onCambio }: { textos: TextosSignos; onCambio: (t: TextosSignos) => void }) {
  const { datos, errores } = leerSignos(textos)
  const { bmi, alerts } = calcular(datos)
  return <fieldset className="space-y-3">
    <legend className="text-sm font-medium text-tinta-700 dark:text-tinta-300">Signos vitales <span className="font-normal text-tinta-500">(opcionales)</span></legend>
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {SIGNOS.map(s => {
        const error = errores[s.campo]
        const alerta = ALERTA_DE[s.campo] && !error && datos?.[s.campo] != null ? alerts[ALERTA_DE[s.campo]!] : undefined
        return <label key={s.campo} className="block space-y-1 text-sm">
          <span className="flex items-center gap-2 text-tinta-600 dark:text-tinta-300">{s.etiqueta}{alerta && <Marca texto={alerta} />}</span>
          <span className="relative block">
            <input className={`${INPUT} pr-14`} inputMode={s.decimales ? 'decimal' : 'numeric'} value={textos[s.campo]}
              aria-invalid={!!error} aria-describedby={error ? `error-${s.campo}` : undefined}
              onChange={e => onCambio({ ...textos, [s.campo]: e.target.value })} />
            <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-tinta-500">{s.unidad}</span>
          </span>
          {error && <span id={`error-${s.campo}`} className="block text-xs text-alerta-600">{error}</span>}
        </label>
      })}
    </div>
    <Imc bmi={bmi} />
  </fieldset>
}

/** Lo firmado, en la atención y en el historial. */
export function VerSignos({ signos }: { signos: SignosVitales | null }) {
  if (!signos) return null
  const presion = signos.systolic != null || signos.diastolic != null
  const filas: { etiqueta: string; valor: string; alerta?: string }[] = [
    ...(presion ? [{ etiqueta: 'Presión arterial', valor: `${signos.systolic ?? '—'}/${signos.diastolic ?? '—'} mmHg`, alerta: signos.alerts.blood_pressure }] : []),
    ...SIGNOS.filter(s => !['systolic', 'diastolic'].includes(s.campo) && signos[s.campo] != null).map(s => ({
      etiqueta: s.etiqueta,
      valor: `${signos[s.campo]!.toLocaleString('es-BO')} ${s.unidad}`,
      alerta: ALERTA_DE[s.campo] ? signos.alerts[ALERTA_DE[s.campo]!] : undefined,
    })),
  ]
  return <div className="space-y-2">
    <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
      {filas.map(f => <div key={f.etiqueta} className="flex flex-wrap items-center justify-between gap-2 border-b border-tinta-100 py-1 dark:border-tinta-800">
        <dt className="text-tinta-500">{f.etiqueta}</dt>
        <dd className="flex items-center gap-2 font-medium text-tinta-900 dark:text-tinta-50">{f.valor}{f.alerta && <Marca texto={f.alerta} />}</dd>
      </div>)}
    </dl>
    <Imc bmi={signos.bmi} />
  </div>
}
