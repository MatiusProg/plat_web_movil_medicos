import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { buscarPacientes, crearPaciente, type PacienteResumen, type PacienteGuardar } from '@/api/pacientes'
import { listarProfesionalesTodos, type ProfesionalTarjeta } from '@/api/catalogo'
import { disponibilidadConsolidada, type Espacio } from '@/api/disponibilidad'
import { realizarCheckIn, type Ficha } from '@/api/fichas'
import { reservarEnMostrador, cobrarEnMostrador } from '@/api/mostrador'
import { useSesion } from '@/sesion/useSesion'

const fechaLocal = (dias = 0) => {
  const d = new Date(); d.setDate(d.getDate() + dias)
  return [d.getFullYear(), String(d.getMonth()+1).padStart(2,'0'), String(d.getDate()).padStart(2,'0')].join('-')
}
// Campos legibles con los dos temas de MediAdmin.
const campoMostrador = 'rounded-lg border border-tinta-300 bg-white p-3 text-tinta-900 placeholder:text-tinta-500 focus:border-marca-500 focus:ring-2 focus:ring-marca-500/30 dark:border-tinta-700 dark:bg-tinta-900 dark:text-tinta-100 dark:placeholder:text-tinta-400'
const opcionMostrador = 'bg-white text-tinta-900 dark:bg-tinta-900 dark:text-tinta-100'
const errorTexto = (e: unknown) => e instanceof Error ? e.message : 'No se pudo completar la operación.'

export function Mostrador() {
  const { token, usuario, puede } = useSesion()
  const contexto = { token, organizacion: usuario?.organization ?? null }
  const [busqueda, setBusqueda] = useState('')
  const [alta, setAlta] = useState(false)
  const [nuevo, setNuevo] = useState<PacienteGuardar>({ document_type:'CI', document_number:'', first_name:'', last_name:'', birth_date:null, sex:'', phone:'' })
  const [pacientes, setPacientes] = useState<PacienteResumen[]>([])
  const [paciente, setPaciente] = useState('')
  const [profesionales, setProfesionales] = useState<ProfesionalTarjeta[]>([])
  const [profesional, setProfesional] = useState('')
  const [dia, setDia] = useState(fechaLocal())
  const [espacios, setEspacios] = useState<Espacio[]>([])
  const [espacio, setEspacio] = useState<Espacio | null>(null)
  const [ficha, setFicha] = useState<Ficha | null>(null)
  const [documento, setDocumento] = useState('')
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const permitido = puede('appointments.appointment.book_at_counter')
  useEffect(() => {
    if (!permitido) return
    listarProfesionalesTodos(contexto).then(setProfesionales).catch(e => setError(errorTexto(e)))
  }, [token, usuario?.organization, permitido])
  useEffect(() => {
    if (!permitido) return
    const control = new AbortController()
    buscarPacientes({ q: busqueda, status: 'active', pageSize: 100 }, contexto, control.signal)
      .then(r => setPacientes(r.results)).catch(e => { if (!control.signal.aborted) setError(errorTexto(e)) })
    return () => control.abort()
  }, [busqueda, token, usuario?.organization, permitido])
  useEffect(() => {
    setEspacios([]); setEspacio(null)
    if (!profesional || !dia) return
    const control = new AbortController()
    disponibilidadConsolidada({ practitioner: profesional, from: dia, to: dia }, contexto, control.signal)
      .then(r => setEspacios(r.days.flatMap(d => d.slots).filter(s => s.reservable)))
      .catch(e => { if (!control.signal.aborted) setError(errorTexto(e)) })
    return () => control.abort()
  }, [profesional, dia, token, usuario?.organization])
  const ejecutar = async (accion: () => Promise<void>) => {
    setError(''); setMensaje(''); setOcupado(true)
    try { await accion() } catch(e) { setError(errorTexto(e)) } finally { setOcupado(false) }
  }
  if (!permitido) return <main className="p-6"><h1 className="text-2xl font-bold">Mostrador</h1><p>No tenés permiso para reservar desde recepción.</p></main>
  const seleccionado = pacientes.find(p => p.id === paciente)
  return <main className="mx-auto max-w-5xl space-y-6 p-4 sm:p-8">
    <header><h1 className="text-3xl font-bold">Atención en mostrador</h1><p className="mt-2 opacity-70">Buscá al paciente, reservá un turno, cobrá en efectivo y registrá su llegada.</p></header>
    {error && <div role="alert" className="rounded-xl border border-red-400 p-4 text-red-600">{error}</div>}
    {mensaje && <div role="status" className="rounded-xl border border-green-400 p-4 text-green-700">{mensaje}</div>}
    <section className="space-y-3 rounded-2xl border p-5">
      <h2 className="text-xl font-semibold">1. Paciente</h2>
      <label className="block">Buscar por nombre o documento<input value={busqueda} onChange={e => setBusqueda(e.target.value)} className={`mt-1 w-full ${campoMostrador}`} placeholder="Nombre o CI" /></label>
      <select aria-label="Seleccionar paciente" value={paciente} onChange={e => { setPaciente(e.target.value); setFicha(null) }} className={`w-full ${campoMostrador}`}>
        <option className={opcionMostrador} value="">Seleccioná un paciente</option>{pacientes.map(p => <option className={opcionMostrador} key={p.id} value={p.id}>{p.full_name} — {p.document_number || 'Sin documento'}</option>)}
      </select>
      <button type="button" className="underline" onClick={() => setAlta(!alta)}> {alta ? 'Cancelar alta' : 'Registrar paciente nuevo sin salir de mostrador'} </button>
      {alta && <form className="grid gap-3 sm:grid-cols-2" onSubmit={e => {e.preventDefault();void ejecutar(async () => {const creado=await crearPaciente(nuevo,contexto);setPacientes(actual=>[creado,...actual]);setPaciente(creado.id);setAlta(false);setBusqueda('');setMensaje('Paciente registrado correctamente.')})}}>
        <input required aria-label="Nombres del paciente" placeholder="Nombres *" className={campoMostrador} value={nuevo.first_name} onChange={e=>setNuevo({...nuevo,first_name:e.target.value})}/>
        <input required aria-label="Apellidos del paciente" placeholder="Apellidos *" className={campoMostrador} value={nuevo.last_name} onChange={e=>setNuevo({...nuevo,last_name:e.target.value})}/>
        <input required aria-label="Documento del paciente" placeholder="Número de documento *" className={campoMostrador} value={nuevo.document_number ?? ''} onChange={e=>setNuevo({...nuevo,document_number:e.target.value})}/>
        <input aria-label="Teléfono del paciente" placeholder="Teléfono" className={campoMostrador} value={nuevo.phone} onChange={e=>setNuevo({...nuevo,phone:e.target.value})}/>
        <button disabled={ocupado || !puede('patients.patient.create')} className="rounded-xl bg-blue-700 px-5 py-3 font-semibold text-white disabled:opacity-40">Guardar paciente</button>
      </form>}
      <p className="text-sm">También podés usar <Link className="underline" to="/pacientes">Gestión de pacientes</Link> para editar o consultar detalles.</p>
    </section>
    <section className="space-y-3 rounded-2xl border p-5"><h2 className="text-xl font-semibold">2. Turno disponible</h2>
      <select aria-label="Profesional" value={profesional} onChange={e => setProfesional(e.target.value)} className={`w-full ${campoMostrador}`}><option className={opcionMostrador} value="">Seleccioná profesional</option>{profesionales.map(p => <option className={opcionMostrador} value={p.id} key={p.id}>{p.full_name}</option>)}</select>
      <input aria-label="Fecha" type="date" min={fechaLocal()} value={dia} onChange={e => setDia(e.target.value)} className={campoMostrador} />
      <div className="grid gap-2 sm:grid-cols-3">{espacios.map(s => <button key={s.schedule.id+s.start} type="button" onClick={() => setEspacio(s)} className={`rounded-lg border p-3 text-left ${espacio?.start===s.start && espacio?.schedule.id===s.schedule.id ? 'border-blue-500 ring-2 ring-blue-500' : ''}`}>{new Date(s.start).toLocaleTimeString('es-BO',{hour:'2-digit',minute:'2-digit'})} · {s.branch.name}</button>)}</div>
      {profesional && espacios.length===0 && <p>No hay turnos disponibles para esta fecha.</p>}
      <button disabled={!paciente || !espacio || ocupado || !!ficha} className="rounded-xl bg-blue-700 px-5 py-3 font-semibold text-white disabled:opacity-40" onClick={() => ejecutar(async () => { if (!espacio) return; const creada = await reservarEnMostrador({patient:paciente,practitioner:profesional,branch:espacio.branch.id,schedule:espacio.schedule.id,startsAt:espacio.start},contexto);setFicha(creada);setDocumento(seleccionado?.document_number ?? '');setMensaje('Ficha reservada. Registrá el cobro antes de 15 minutos.') })}>Reservar a nombre del paciente</button>
    </section>
    {ficha && <section className="space-y-3 rounded-2xl border p-5"><h2 className="text-xl font-semibold">3. Cobro en ventanilla</h2><p>{ficha.patient_name} · {ficha.practitioner_name}</p><p>Estado: {ficha.status}</p><p className="text-2xl font-bold">{ficha.fee.amount} {ficha.fee.currency}</p>
      <p className="text-sm">El importe lo determina el servidor. Verificá que recibiste el efectivo antes de confirmar.</p>
      <button disabled={ocupado || ficha.status !== 'pending_payment' || !puede('payments.payment.register_cash')} onClick={() => ejecutar(async () => { const cobro=await cobrarEnMostrador(ficha.id,contexto);setFicha(cobro.appointment);setMensaje(`Cobrado: ${cobro.amount} ${cobro.currency}. Ficha confirmada.`) })} className="rounded-xl bg-green-700 px-5 py-3 font-semibold text-white disabled:opacity-40">Confirmar cobro en efectivo</button>
      {ficha.status === 'confirmed' && <div className="space-y-3 border-t pt-4"><h2 className="text-xl font-semibold">4. Check-in por documento</h2><input aria-label="Número de documento" value={documento} onChange={e => setDocumento(e.target.value)} className={`w-full ${campoMostrador}`} placeholder="Número de documento" /><button disabled={!documento.trim() || ocupado} className="rounded-xl bg-blue-700 px-5 py-3 font-semibold text-white disabled:opacity-40" onClick={() => ejecutar(async () => { await realizarCheckIn({document_number:documento.trim()},contexto);setFicha({...ficha,status:'attended'});setMensaje('Check-in realizado correctamente.') })}>Registrar llegada sin QR</button></div>}
      <button type="button" className="block underline" onClick={() => {setFicha(null);setEspacio(null);setMensaje('')}}>Atender otro paciente</button>
    </section>}
  </main>
}
