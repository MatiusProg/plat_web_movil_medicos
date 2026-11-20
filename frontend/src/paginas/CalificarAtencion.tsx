/**
 * US-48 — «¿Cómo te atendieron?»: las estrellas debajo de cada atención
 * firmada en *Mi historia clínica*.
 *
 * Sin calificar: cinco estrellas que se tocan y un comentario opcional. Ya
 * calificada: «Calificaste con ★★★★☆» y «Cambiar» mientras queden días; pasado
 * el plazo, sólo lo que se calificó. Las reglas (1 a 5, 500 caracteres, 7
 * días) las vuelve a revisar el backend.
 */
import { useState } from 'react'
import { calificar, MAX_COMENTARIO, type Calificacion } from '@/api/calificaciones'
import { Boton } from '@/componentes/Boton'
import { useSesion } from '@/sesion/useSesion'
import { INPUT, SECONDARY, mensajeError } from './catalogo_comun'

const ETIQUETAS = ['Muy mala', 'Mala', 'Regular', 'Buena', 'Muy buena']

/** ★★★★☆, para leer de un vistazo. */
export const estrellasEnTexto = (n: number) => '★'.repeat(n) + '☆'.repeat(5 - n)

function Estrellas({ valor, onElegir }: { valor: number; onElegir: (n: number) => void }) {
  const [encima, setEncima] = useState(0)
  const mostrada = encima || valor
  return <div role="radiogroup" aria-label="Estrellas" className="flex gap-1" onMouseLeave={() => setEncima(0)}>
    {[1, 2, 3, 4, 5].map(n =>
      <button key={n} type="button" role="radio" aria-checked={valor === n}
        aria-label={`${n} ${n === 1 ? 'estrella' : 'estrellas'}: ${ETIQUETAS[n - 1]}`}
        onMouseEnter={() => setEncima(n)} onClick={() => onElegir(n)}
        className={`text-3xl leading-none transition-transform motion-safe:hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marca-500 rounded ${
          n <= mostrada ? 'text-amber-400' : 'text-tinta-300 dark:text-tinta-600'}`}>
        ★
      </button>)}
    {mostrada > 0 && <span className="ml-2 self-center text-sm text-tinta-500">{ETIQUETAS[mostrada - 1]}</span>}
  </div>
}

export function CalificarAtencion({ encuentroId, inicial }: { encuentroId: string; inicial: Calificacion | null }) {
  const { token } = useSesion()
  const [guardada, setGuardada] = useState<Calificacion | null>(inicial)
  const [editando, setEditando] = useState(inicial === null)
  const [estrellas, setEstrellas] = useState(inicial?.stars ?? 0)
  const [comentario, setComentario] = useState(inicial?.comment ?? '')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function enviar(e: React.FormEvent) {
    e.preventDefault()
    if (!estrellas) return
    setEnviando(true)
    setError(null)
    try {
      const { rating } = await calificar(encuentroId, guardada === null,
        { stars: estrellas, comment: comentario.trim() }, { token })
      setGuardada(rating)
      setEditando(false)
    } catch (err) {
      setError(mensajeError(err))
    } finally {
      setEnviando(false)
    }
  }

  if (guardada && !editando) {
    const hasta = new Date(guardada.editable_until).toLocaleDateString('es-BO', { day: 'numeric', month: 'long' })
    return <section aria-label="Tu calificación" className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl bg-tinta-50 px-4 py-3 text-sm dark:bg-tinta-800/50">
      <span className="text-tinta-700 dark:text-tinta-200">
        Calificaste con <span className="text-amber-500" aria-label={`${guardada.stars} de 5 estrellas`}>{estrellasEnTexto(guardada.stars)}</span>
      </span>
      {guardada.comment && <span className="w-full text-tinta-500">«{guardada.comment}»</span>}
      {guardada.editable
        ? <button type="button" className="font-medium text-marca-700 hover:underline dark:text-marca-400"
          onClick={() => { setEstrellas(guardada.stars); setComentario(guardada.comment); setEditando(true) }}>
          Cambiar <span className="font-normal text-tinta-500">(hasta el {hasta})</span></button>
        : <span className="text-xs text-tinta-500">Ya no se puede cambiar.</span>}
    </section>
  }

  return <form onSubmit={enviar} aria-label="Califica esta atención"
    className="mt-3 space-y-3 rounded-xl border border-tinta-200 px-4 py-3 dark:border-tinta-700">
    <p className="text-sm font-semibold text-tinta-800 dark:text-tinta-100">¿Cómo te atendieron?</p>
    <Estrellas valor={estrellas} onElegir={setEstrellas} />
    {estrellas > 0 && <>
      <label className="block text-sm">
        <span className="text-tinta-600 dark:text-tinta-300">Comentario (opcional)</span>
        <textarea className={`${INPUT} mt-1 min-h-20`} maxLength={MAX_COMENTARIO} value={comentario}
          onChange={e => setComentario(e.target.value)} placeholder="¿Qué te gustó o qué se puede mejorar?" />
        <span className="mt-1 block text-right text-xs tabular-nums text-tinta-500">{comentario.length}/{MAX_COMENTARIO}</span>
      </label>
      <p className="text-xs text-tinta-500">Tu médico ve su promedio, pero no quién lo calificó. Puedes cambiarla durante 7 días.</p>
    </>}
    {error && <p role="alert" className="text-sm text-alerta-600">{error}</p>}
    <div className="flex gap-2">
      <Boton type="submit" className="w-auto" cargando={enviando} textoCargando="Guardando…" disabled={!estrellas}>
        {guardada ? 'Guardar cambio' : 'Enviar calificación'}</Boton>
      {guardada && <button type="button" className={SECONDARY} onClick={() => setEditando(false)}>Cancelar</button>}
    </div>
  </form>
}
