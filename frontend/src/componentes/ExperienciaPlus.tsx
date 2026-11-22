import { useEffect, useState } from 'react'
import type { Ficha } from '@/api/fichas'
import { leerPreconsulta, guardarPreconsulta } from '@/api/preconsulta'
import { useSesion } from '@/sesion/useSesion'

/** US-51: experiencia complementaria SIN recargos ni prioridad clínica. */
export function ExperienciaPlus({ ficha, cerrar }: { ficha: Ficha; cerrar: () => void }) {
  const { token } = useSesion()
  const [reason, setReason] = useState('')
  const [questions, setQuestions] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const editable = ficha.status === 'confirmed' && new Date(ficha.starts_at).getTime() > Date.now()
  useEffect(() => {
    let alive = true
    leerPreconsulta(ficha.id, { token }).then(data => {
      if (alive) { setReason(data.reason); setQuestions(data.questions) }
    }).catch(() => { if (alive) setMessage('No se pudo cargar la preconsulta.') })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [ficha.id, token])
  const guardar = async () => {
    setSaving(true); setMessage('')
    try {
      await guardarPreconsulta(ficha.id, { reason, questions }, { token })
      setMessage('Preconsulta guardada correctamente.')
    } catch { setMessage('No se pudo guardar. Verifica la conexión o el estado de la ficha.') }
    finally { setSaving(false) }
  }
  const calendario = () => {
    const utc = (date: string) => new Date(date).toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')
    const esc = (s: string) => s.replace(/\\/g, '\\\\').replace(/,/g, '\\,').replace(/;/g, '\\;').replace(/\n/g, '\\n')
    const ics = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Plataforma Medica//US51//ES', 'BEGIN:VEVENT', `UID:${ficha.id}@fichas`, `DTSTAMP:${utc(new Date().toISOString())}`, `DTSTART:${utc(ficha.starts_at)}`, `DTEND:${utc(ficha.ends_at)}`, `SUMMARY:${esc('Consulta médica - ' + ficha.practitioner_name)}`, `LOCATION:${esc(ficha.branch_name)}`, 'END:VEVENT', 'END:VCALENDAR'].join('\r\n')
    const url = URL.createObjectURL(new Blob([ics], { type: 'text/calendar;charset=utf-8' }))
    const a = document.createElement('a'); a.href = url; a.download = 'mi-cita.ics'; a.click()
    URL.revokeObjectURL(url)
  }
  return <div role="dialog" aria-modal="true" aria-label="Tu experiencia de compra" className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
    <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-5 text-gray-900 dark:bg-gray-900 dark:text-white">
      <div className="flex justify-between gap-4"><h2 className="text-xl font-semibold">Tu ficha, más que un comprobante</h2><button type="button" onClick={cerrar} aria-label="Cerrar">✕</button></div>
      <p className="mt-2 text-sm">{ficha.patient_name} · {ficha.practitioner_name} · {ficha.branch_name}</p>
      <p className="mt-1 text-sm">{new Date(ficha.starts_at).toLocaleString('es-BO')}</p>
      <button type="button" className="mt-3 rounded-lg border px-3 py-2" onClick={calendario}>Agregar al calendario</button>
      <h3 className="mt-5 font-semibold">Antes de tu cita</h3>
      <p className="text-sm">Lleva tu identificación y sigue únicamente las instrucciones comunicadas por tu centro médico. Si tienes dudas sobre preparación, consulta con el profesional.</p>
      <h3 className="mt-4 font-semibold">Preconsulta opcional</h3>
      {loading ? <p>Cargando…</p> : <div className="mt-2 space-y-3">
        <label className="block text-sm">Motivo de la consulta<textarea className="mt-1 w-full rounded-lg border bg-transparent p-2" maxLength={1200} rows={3} value={reason} onChange={e => setReason(e.target.value)} disabled={!editable}/></label>
        <label className="block text-sm">Preguntas para conversar con tu médico<textarea className="mt-1 w-full rounded-lg border bg-transparent p-2" maxLength={1200} rows={3} value={questions} onChange={e => setQuestions(e.target.value)} disabled={!editable}/></label>
        {editable && <button type="button" className="rounded-lg bg-blue-700 px-4 py-2 text-white disabled:opacity-50" onClick={guardar} disabled={saving}>{saving ? 'Guardando…' : 'Guardar preconsulta'}</button>}
        {message && <p role="status" className="text-sm">{message}</p>}
      </div>}
      <p className="mt-4 text-xs">Este formulario no sustituye una evaluación médica. No compartas información que no quieras registrar.</p>
    </div>
  </div>
}
