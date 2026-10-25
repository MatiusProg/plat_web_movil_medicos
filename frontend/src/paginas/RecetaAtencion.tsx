/**
 * US-26 y US-27 — La receta y las órdenes de una atención.
 *
 * `PanelReceta` va dentro de la atención (`Atencion.tsx`): mientras es
 * borrador el médico agrega y quita; firmada, sólo se lee y se baja en PDF, y
 * las correcciones van como enmienda. `RecetaDeLaAtencion` es la versión de
 * lectura que usa la línea de tiempo (`Historial` y `MiHistoria`): el
 * paciente ve qué le recetaron y baja la receta.
 *
 * Los antecedentes de US-08 no se repiten acá: `Atencion.tsx` ya los muestra
 * arriba de todo, a la vista mientras se receta.
 */
import { useState, type FormEvent } from 'react'
import {
  TIPOS_DE_ORDEN, agregarMedicamento, agregarOrden, descargarReceta, quitarMedicamento, quitarOrden,
  type DatosMedicamento, type DatosOrden, type Encuentro,
} from '@/api/atencion'
import { Boton } from '@/componentes/Boton'
import { useSesion } from '@/sesion/useSesion'
import { DANGER, ErrorCatalogo, INPUT, PANEL, SECONDARY, mensajeError } from './catalogo_comun'

const fechaHora = (iso: string) => new Date(iso).toLocaleString('es-BO', { dateStyle: 'medium', timeStyle: 'short', hourCycle: 'h23' })
const MEDICAMENTO_VACIO: DatosMedicamento = { medication: '', dose: '', frequency: '', duration: '', instructions: '' }
const ORDEN_VACIA: DatosOrden = { kind: 'laboratory', description: '', notes: '' }

const tieneReceta = (e: Encuentro) => e.prescription_items.length > 0 || e.orders.length > 0

/** El botón de descarga, con su propio error: una receta que no baja no rompe la página. */
function BotonDescargar({ encuentro }: { encuentro: Encuentro }) {
  const { token } = useSesion()
  const [bajando, setBajando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bajar = async () => {
    setBajando(true); setError(null)
    try { await descargarReceta(encuentro.id, { token }) }
    catch (e) { setError(mensajeError(e)) }
    finally { setBajando(false) }
  }
  return <div className="flex flex-col items-end gap-1">
    <button type="button" className={SECONDARY} disabled={bajando} onClick={() => void bajar()}>
      {bajando ? 'Generando…' : 'Descargar receta (PDF)'}
    </button>
    {error && <p role="alert" className="text-xs text-alerta-600">{error}</p>}
  </div>
}

/** Las dos listas, sólo lectura. `quitar` aparece mientras es borrador. */
function Listas({ encuentro, quitar }: {
  encuentro: Encuentro
  quitar?: { medicamento: (id: string) => void; orden: (id: string) => void; ocupado: boolean }
}) {
  return <div className="space-y-4 text-sm">
    {encuentro.prescription_items.length > 0 && <div>
      <h3 className="font-medium text-tinta-700 dark:text-tinta-300">Medicamentos</h3>
      <ul className="mt-1.5 divide-y divide-tinta-100 dark:divide-tinta-800">{encuentro.prescription_items.map(m => <li key={m.id} className="flex flex-wrap items-start justify-between gap-2 py-2">
        <div>
          <p className="font-medium text-tinta-900 dark:text-tinta-50">{m.medication}</p>
          <p className="text-tinta-600 dark:text-tinta-300">{m.dose} · {m.frequency} · {m.duration}</p>
          {m.instructions && <p className="text-tinta-500">{m.instructions}</p>}
        </div>
        {quitar && <button type="button" className={DANGER} disabled={quitar.ocupado} onClick={() => quitar.medicamento(m.id)} aria-label={`Quitar ${m.medication}`}>Quitar</button>}
      </li>)}</ul>
    </div>}
    {encuentro.orders.length > 0 && <div>
      <h3 className="font-medium text-tinta-700 dark:text-tinta-300">Órdenes</h3>
      <ul className="mt-1.5 divide-y divide-tinta-100 dark:divide-tinta-800">{encuentro.orders.map(o => <li key={o.id} className="flex flex-wrap items-start justify-between gap-2 py-2">
        <div>
          <p className="text-tinta-900 dark:text-tinta-50"><span className="mr-2 rounded-md bg-tinta-100 px-1.5 py-0.5 text-xs font-medium text-tinta-600 dark:bg-tinta-800 dark:text-tinta-300">{o.kind_display}</span>{o.description}</p>
          {o.notes && <p className="text-tinta-500">{o.notes}</p>}
        </div>
        {quitar && <button type="button" className={DANGER} disabled={quitar.ocupado} onClick={() => quitar.orden(o.id)} aria-label={`Quitar ${o.description}`}>Quitar</button>}
      </li>)}</ul>
    </div>}
    {encuentro.amendments.filter(a => a.section === 'prescription' || a.section === 'orders').map(a => <div key={a.id} className="ml-3 border-l-2 border-marca-400 pl-3">
      <p className="text-xs text-tinta-500">Enmienda a {a.section_display.toLowerCase()} de {a.author_name} · {fechaHora(a.created_at)}</p>
      <p className="whitespace-pre-wrap text-tinta-800 dark:text-tinta-100">{a.text}</p>
    </div>)}
  </div>
}

/** US-26 — Emitir la receta y las órdenes desde la atención. */
export function PanelReceta({ encuentro, onCambio }: { encuentro: Encuentro; onCambio: (e: Encuentro) => void }) {
  const { token } = useSesion()
  const [medicamento, setMedicamento] = useState<DatosMedicamento>(MEDICAMENTO_VACIO)
  const [orden, setOrden] = useState<DatosOrden>(ORDEN_VACIA)
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const firmado = encuentro.status === 'signed'

  const ejecutar = async (accion: () => Promise<Encuentro>, despues?: () => void) => {
    setOcupado(true); setError(null)
    try { onCambio(await accion()); despues?.() }
    catch (e) { setError(mensajeError(e)) }
    finally { setOcupado(false) }
  }

  const medicamentoCompleto = medicamento.medication.trim() && medicamento.dose.trim() && medicamento.frequency.trim() && medicamento.duration.trim()
  const enviarMedicamento = (e: FormEvent) => {
    e.preventDefault()
    if (!medicamentoCompleto || ocupado) return
    void ejecutar(() => agregarMedicamento(encuentro.id, medicamento, { token }), () => setMedicamento(MEDICAMENTO_VACIO))
  }
  const enviarOrden = (e: FormEvent) => {
    e.preventDefault()
    if (!orden.description.trim() || ocupado) return
    void ejecutar(() => agregarOrden(encuentro.id, orden, { token }), () => setOrden({ ...ORDEN_VACIA, kind: orden.kind }))
  }

  const campo = (clave: keyof DatosMedicamento, etiqueta: string, ayuda: string, obligatorio = true, max = 80) =>
    <label className="block space-y-1 text-sm">
      <span className="font-medium text-tinta-700 dark:text-tinta-300">{etiqueta}{obligatorio && <span className="text-alerta-600"> *</span>}</span>
      <input className={INPUT} value={medicamento[clave]} maxLength={max} placeholder={ayuda}
        onChange={e => setMedicamento({ ...medicamento, [clave]: e.target.value })} />
    </label>

  return <section className={`${PANEL} space-y-5`} aria-labelledby="receta-titulo">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 id="receta-titulo" className="font-semibold text-tinta-900 dark:text-tinta-100">Receta y órdenes</h2>
        <p className="mt-1 text-sm text-tinta-500">{firmado
          ? 'Quedaron firmadas con la atención. Para corregirlas, agrega una enmienda.'
          : 'Se firman junto con la atención. Hasta entonces puedes agregar y quitar.'}</p>
      </div>
      {firmado && tieneReceta(encuentro) && <BotonDescargar encuentro={encuentro} />}
    </div>
    {error && <ErrorCatalogo mensaje={error} />}

    {tieneReceta(encuentro)
      ? <Listas encuentro={encuentro} quitar={firmado ? undefined : {
        ocupado,
        medicamento: id => void ejecutar(() => quitarMedicamento(encuentro.id, id, { token })),
        orden: id => void ejecutar(() => quitarOrden(encuentro.id, id, { token })),
      }} />
      : <p className="text-sm text-tinta-500">{firmado ? 'Esta atención no tiene receta ni órdenes.' : 'Todavía no hay medicamentos ni órdenes.'}</p>}

    {!firmado && <>
      <form onSubmit={enviarMedicamento} className="space-y-3 border-t border-tinta-200 pt-4 dark:border-tinta-800">
        <h3 className="text-sm font-semibold text-tinta-800 dark:text-tinta-200">Agregar un medicamento</h3>
        {campo('medication', 'Medicamento', 'Nombre, concentración y forma', true, 200)}
        <div className="grid gap-3 sm:grid-cols-3">
          {campo('dose', 'Dosis', '1 comprimido')}
          {campo('frequency', 'Frecuencia', 'cada 8 horas')}
          {campo('duration', 'Duración', '7 días')}
        </div>
        {campo('instructions', 'Indicaciones de toma', 'Después de las comidas', false, 300)}
        <div className="flex justify-end"><Boton type="submit" className="w-auto" cargando={ocupado} disabled={!medicamentoCompleto}>Agregar medicamento</Boton></div>
      </form>

      <form onSubmit={enviarOrden} className="space-y-3 border-t border-tinta-200 pt-4 dark:border-tinta-800">
        <h3 className="text-sm font-semibold text-tinta-800 dark:text-tinta-200">Agregar una orden</h3>
        <div className="grid gap-3 sm:grid-cols-[12rem_1fr]">
          <label className="block space-y-1 text-sm"><span className="font-medium text-tinta-700 dark:text-tinta-300">Tipo</span>
            <select className={INPUT} value={orden.kind} onChange={e => setOrden({ ...orden, kind: e.target.value as DatosOrden['kind'] })}>
              {TIPOS_DE_ORDEN.map(t => <option key={t.valor} value={t.valor}>{t.etiqueta}</option>)}
            </select></label>
          <label className="block space-y-1 text-sm"><span className="font-medium text-tinta-700 dark:text-tinta-300">Estudio<span className="text-alerta-600"> *</span></span>
            <input className={INPUT} value={orden.description} maxLength={300} placeholder="Hemograma completo" onChange={e => setOrden({ ...orden, description: e.target.value })} /></label>
        </div>
        <label className="block space-y-1 text-sm"><span className="font-medium text-tinta-700 dark:text-tinta-300">Observaciones</span>
          <input className={INPUT} value={orden.notes} maxLength={300} placeholder="En ayunas" onChange={e => setOrden({ ...orden, notes: e.target.value })} /></label>
        <div className="flex justify-end"><Boton type="submit" className="w-auto" cargando={ocupado} disabled={!orden.description.trim()}>Agregar orden</Boton></div>
      </form>
    </>}
  </section>
}

/** US-27 — La receta de una atención firmada, para leer y bajar desde el historial. */
export function RecetaDeLaAtencion({ encuentro }: { encuentro: Encuentro }) {
  if (!tieneReceta(encuentro)) return null
  return <div className="mt-4 space-y-3 border-t border-tinta-200 pt-3 dark:border-tinta-800">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h3 className="text-sm font-semibold text-tinta-800 dark:text-tinta-200">Receta y órdenes</h3>
      <BotonDescargar encuentro={encuentro} />
    </div>
    <Listas encuentro={encuentro} />
  </div>
}
