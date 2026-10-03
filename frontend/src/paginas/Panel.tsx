/**
 * El panel de inicio: lo que cada persona necesita al empezar el día.
 *
 * Los bloques salen de `/api/platform/my-panel/`, que sólo devuelve lo que el
 * rol puede ver: administración ve el uso del plan, recepción el día del
 * centro, el médico su agenda y el paciente sus próximas fichas. El
 * superadministrador ve la salud de la plataforma (`/api/platform/dashboard/`).
 *
 * Nada de códigos internos: hasta el 03/10/26 esta pantalla mostraba la lista
 * cruda de permisos (`catalog.branch.create`…), que no le dice nada a nadie.
 */
import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { pedir } from '@/api/cliente'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'
import { ErrorCatalogo, PANEL, SECONDARY, mensajeError } from './catalogo_comun'

interface FichaPanel {
  id: string
  hora: string
  status: string
  status_display: string
  branch: string
  practitioner: string
  patient?: string
  starts_at: string
  encounter?: { id: string; status: 'draft' | 'signed' } | null
}

interface DatosPanel {
  plataforma?: boolean
  fecha?: string
  organizacion?: string
  plan?: {
    code: string
    name: string
    uso: { etiqueta: string; usados: number; tope: number | null }[]
    incluye: { asistente: boolean; exportar_reportes: boolean }
  }
  hoy?: { total: number; atendidas: number; por_atender: number; canceladas: number; proximas: FichaPanel[] }
  asistencia?: { atendidas: number; ausentes: number; canceladas: number }
  mi_agenda?: { fichas: FichaPanel[]; sin_firmar: number }
  mis_fichas?: FichaPanel[]
  incluye?: { asistente: boolean; exportar_reportes: boolean }
}

interface DatosPlataforma {
  organizations: { total: number; active: number; suspended: number; inactive: number }
  by_plan: { plan_code: string; plan_name: string; count: number }[]
  alerts: { pending: number; critical_pending: number }
}

const fechaLarga = (iso: string) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString('es-BO', { weekday: 'long', day: 'numeric', month: 'long' })

const fechaFicha = (iso: string) =>
  new Date(iso).toLocaleString('es-BO', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })

function Bloque({ titulo, accion, children }: { titulo: string; accion?: ReactNode; children: ReactNode }) {
  return <section className={PANEL} aria-label={titulo}>
    <div className="mb-4 flex items-center justify-between gap-3">
      <h2 className="font-semibold text-tinta-900 dark:text-tinta-100">{titulo}</h2>
      {accion}
    </div>
    {children}
  </section>
}

function Cifra({ valor, etiqueta, tono = 'normal' }: { valor: number | string; etiqueta: string; tono?: 'normal' | 'marca' | 'espera' | 'alerta' }) {
  const color = { normal: 'text-tinta-900 dark:text-tinta-50', marca: 'text-marca-700 dark:text-marca-300', espera: 'text-espera-700 dark:text-espera-200', alerta: 'text-alerta-700 dark:text-alerta-500' }[tono]
  return <div>
    <p className={`text-3xl font-semibold tabular-nums ${color}`}>{valor}</p>
    <p className="mt-1 text-sm text-tinta-500">{etiqueta}</p>
  </div>
}

/** Una barra de uso contra el tope del plan. Ámbar desde el 80 %, rojo al llegar. */
function Uso({ etiqueta, usados, tope }: { etiqueta: string; usados: number; tope: number | null }) {
  const porcentaje = tope ? Math.min(100, Math.round((usados / tope) * 100)) : 0
  const color = !tope ? 'bg-marca-500' : porcentaje >= 100 ? 'bg-alerta-600' : porcentaje >= 80 ? 'bg-espera-600' : 'bg-marca-500'
  return <div>
    <div className="flex items-baseline justify-between gap-3 text-sm">
      <span className="text-tinta-700 dark:text-tinta-300">{etiqueta}</span>
      <span className="tabular-nums text-tinta-500">{usados}{tope !== null ? ` de ${tope}` : ' · sin límite'}</span>
    </div>
    <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-tinta-100 dark:bg-tinta-800" role="progressbar"
      aria-label={etiqueta} aria-valuenow={usados} aria-valuemin={0} aria-valuemax={tope ?? undefined}>
      <div className={`h-full rounded-full ${color}`} style={{ width: tope ? `${porcentaje}%` : '100%', opacity: tope ? 1 : 0.25 }} />
    </div>
  </div>
}

function ListaFichas({ fichas, vacio, accion }: { fichas: FichaPanel[]; vacio: string; accion?: (f: FichaPanel) => ReactNode }) {
  if (fichas.length === 0) return <p className="text-sm text-tinta-500">{vacio}</p>
  return <ul className="divide-y divide-tinta-200 dark:divide-tinta-800">{fichas.map(f =>
    <li key={f.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-3">
      <span className="w-14 shrink-0 font-semibold tabular-nums text-tinta-900 dark:text-tinta-100">{f.hora}</span>
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-tinta-900 dark:text-tinta-100">{f.patient ?? f.practitioner}</p>
        <p className="truncate text-sm text-tinta-500">{f.patient ? `${f.practitioner} · ` : ''}{f.branch}</p>
      </div>
      {accion ? accion(f) : <span className="text-xs text-tinta-500">{f.status_display}</span>}
    </li>)}</ul>
}

function PanelPlataforma({ token }: { token: string | null }) {
  const [datos, setDatos] = useState<DatosPlataforma | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    const c = new AbortController()
    pedir<DatosPlataforma>('/platform/dashboard/', { token, senal: c.signal }).then(setDatos)
      .catch(e => { if (!(e instanceof DOMException)) setError(mensajeError(e)) })
    return () => c.abort()
  }, [token])
  if (error) return <ErrorCatalogo mensaje={error} />
  if (!datos) return <p role="status" className="text-sm text-tinta-500">Cargando…</p>
  const totalPlan = Math.max(1, datos.by_plan.reduce((s, p) => s + p.count, 0))
  return <div className="grid gap-5 lg:grid-cols-3">
    <Bloque titulo="Organizaciones" accion={<Link to="/organizaciones" className="text-sm font-medium text-marca-700 hover:underline dark:text-marca-400">Ver todas</Link>}>
      <div className="grid grid-cols-2 gap-4">
        <Cifra valor={datos.organizations.active} etiqueta="Activas" tono="marca" />
        <Cifra valor={datos.organizations.suspended + datos.organizations.inactive} etiqueta="Suspendidas o inactivas" />
      </div>
    </Bloque>
    <Bloque titulo="Suscripciones por plan" accion={<Link to="/suscripciones" className="text-sm font-medium text-marca-700 hover:underline dark:text-marca-400">Administrar</Link>}>
      <div className="space-y-3">{datos.by_plan.map(p =>
        <Uso key={p.plan_code} etiqueta={p.plan_name} usados={p.count} tope={totalPlan} />)}</div>
    </Bloque>
    <Bloque titulo="Alertas de aislamiento">
      <div className="grid grid-cols-2 gap-4">
        <Cifra valor={datos.alerts.pending} etiqueta="Pendientes" tono={datos.alerts.pending ? 'espera' : 'normal'} />
        <Cifra valor={datos.alerts.critical_pending} etiqueta="Críticas" tono={datos.alerts.critical_pending ? 'alerta' : 'normal'} />
      </div>
      <p className="mt-4 text-sm text-tinta-500">{datos.alerts.pending ? 'Hay accesos cruzados para revisar.' : 'Ningún acceso cruzado pendiente.'}</p>
    </Bloque>
  </div>
}

export function Panel() {
  const { usuario, token, puede } = useSesion()
  useTitulo('Panel')
  const [datos, setDatos] = useState<DatosPanel | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!usuario || usuario.is_platform_admin) return
    const c = new AbortController()
    pedir<DatosPanel>('/platform/my-panel/', { token, senal: c.signal }).then(setDatos)
      .catch(e => { if (!(e instanceof DOMException)) setError(mensajeError(e)) })
    return () => c.abort()
  }, [token, usuario])

  if (!usuario) return null
  const nombre = usuario.full_name.split(' ')[0]

  // Accesos rápidos: sólo lo que el rol puede hacer, con el mismo permiso
  // que pide la barra lateral para esa pantalla.
  const accesos = [
    { a: '/atencion', texto: 'Atención del día', ok: puede('encounters.encounter.read') },
    { a: '/buscar-profesionales', texto: 'Reservar una ficha', ok: puede('appointments.appointment.create') },
    { a: '/mis-fichas', texto: 'Mis fichas', ok: puede('appointments.appointment.read') },
    { a: '/asistente', texto: 'Consultar al asistente', ok: puede('assistant.suggest.use') && datos?.incluye?.asistente === true },
    { a: '/usuarios', texto: 'Usuarios', ok: puede('users.user.read') },
    { a: '/respaldos', texto: 'Copias de seguridad', ok: puede('backups.backup.create') },
    { a: '/agendas', texto: 'Agendas', ok: puede('scheduling.schedule.read') },
  ].filter(x => x.ok).slice(0, 4)

  return <main className="mx-auto max-w-6xl space-y-6 px-5 py-8 sm:py-10">
    <div className="surgir flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-tinta-900 dark:text-tinta-50">Hola, {nombre}</h1>
        <p className="mt-1.5 text-[0.9375rem] text-tinta-500 first-letter:uppercase">
          {usuario.is_platform_admin ? 'Así está la plataforma hoy.' : datos?.fecha ? `${fechaLarga(datos.fecha)} · ${datos.organizacion}` : ' '}
        </p>
      </div>
      {accesos.length > 0 && <div className="flex flex-wrap gap-2">{accesos.map(x =>
        <Link key={x.a} to={x.a} className={SECONDARY}>{x.texto}</Link>)}</div>}
    </div>

    {usuario.is_platform_admin ? <PanelPlataforma token={token} /> : <>
      {error && <ErrorCatalogo mensaje={error} />}
      {!datos && !error && <p role="status" className="text-sm text-tinta-500">Cargando tu panel…</p>}
      {datos && <div className="grid gap-5 lg:grid-cols-3">

        {datos.mi_agenda && <div className="lg:col-span-2">
          <Bloque titulo="Tu agenda de hoy" accion={<Link to="/atencion" className="text-sm font-medium text-marca-700 hover:underline dark:text-marca-400">Ir a la atención</Link>}>
            {datos.mi_agenda.sin_firmar > 0 && <p className="mb-3 rounded-lg bg-espera-50 px-3 py-2 text-sm text-espera-700 dark:bg-espera-600/10 dark:text-espera-200">
              Tienes {datos.mi_agenda.sin_firmar} {datos.mi_agenda.sin_firmar === 1 ? 'atención sin firmar' : 'atenciones sin firmar'}.</p>}
            <ListaFichas fichas={datos.mi_agenda.fichas} vacio="No tienes fichas hoy."
              accion={f => <Link to={f.encounter ? `/atencion/${f.encounter.id}` : '/atencion'} className="text-sm font-medium text-marca-700 hover:underline dark:text-marca-400">
                {!f.encounter ? 'Atender' : f.encounter.status === 'signed' ? 'Firmada' : 'Continuar'}</Link>} />
          </Bloque>
        </div>}

        {datos.hoy && <div className="lg:col-span-2">
          <Bloque titulo="Hoy en el centro">
            <div className="grid grid-cols-3 gap-4 border-b border-tinta-200 pb-5 dark:border-tinta-800">
              <Cifra valor={datos.hoy.total} etiqueta="Fichas" />
              <Cifra valor={datos.hoy.por_atender} etiqueta="Por atender" tono="marca" />
              <Cifra valor={datos.hoy.atendidas} etiqueta="Atendidas" />
            </div>
            <h3 className="mt-4 text-sm font-medium text-tinta-700 dark:text-tinta-300">Próximas</h3>
            <ListaFichas fichas={datos.hoy.proximas} vacio="No quedan fichas por atender hoy." />
          </Bloque>
        </div>}

        {datos.asistencia && (() => {
          const a = datos.asistencia, total = a.atendidas + a.ausentes + a.canceladas
          const pct = (n: number) => total ? Math.round((n / total) * 100) : 0
          return <Bloque titulo="Asistencia, últimos 30 días">
            {total === 0 ? <p className="text-sm text-tinta-500">Todavía no hay fichas pasadas.</p> : <>
              <Cifra valor={`${pct(a.ausentes)} %`} etiqueta="de ausentismo" tono={pct(a.ausentes) >= 15 ? 'espera' : 'normal'} />
              <div className="mt-4 flex h-2 overflow-hidden rounded-full" aria-hidden="true">
                <div className="bg-marca-500" style={{ width: `${pct(a.atendidas)}%` }} />
                <div className="bg-espera-600" style={{ width: `${pct(a.ausentes)}%` }} />
                <div className="bg-tinta-300 dark:bg-tinta-600" style={{ width: `${pct(a.canceladas)}%` }} />
              </div>
              <dl className="mt-3 space-y-1 text-sm">
                {[['Atendidas', a.atendidas, 'bg-marca-500'], ['Ausentes', a.ausentes, 'bg-espera-600'], ['Canceladas', a.canceladas, 'bg-tinta-300 dark:bg-tinta-600']].map(([t, n, c]) =>
                  <div key={t as string} className="flex items-center gap-2"><span className={`size-2 rounded-full ${c}`} /><dt className="flex-1 text-tinta-600 dark:text-tinta-300">{t}</dt><dd className="tabular-nums text-tinta-900 dark:text-tinta-100">{n}</dd></div>)}
              </dl>
            </>}
          </Bloque>
        })()}

        {datos.plan && <Bloque titulo={`Plan ${datos.plan.name}`}>
          <div className="space-y-4">{datos.plan.uso.map(u => <Uso key={u.etiqueta} {...u} />)}</div>
          <p className="mt-4 text-sm text-tinta-500">
            {!datos.plan.incluye.asistente || !datos.plan.incluye.exportar_reportes
              ? `Tu plan no incluye ${[!datos.plan.incluye.asistente && 'el asistente', !datos.plan.incluye.exportar_reportes && 'exportar reportes'].filter(Boolean).join(' ni ')}.`
              : 'Tu plan incluye el asistente y la exportación de reportes.'}
          </p>
        </Bloque>}

        {datos.mis_fichas && <div className="lg:col-span-2">
          <Bloque titulo="Tus próximas fichas" accion={<Link to="/mis-fichas" className="text-sm font-medium text-marca-700 hover:underline dark:text-marca-400">Ver todas</Link>}>
            {datos.mis_fichas.length === 0
              ? <div className="text-sm text-tinta-500">No tienes fichas reservadas. <Link to="/buscar-profesionales" className="font-medium text-marca-700 hover:underline dark:text-marca-400">Reserva una</Link>.</div>
              : <ul className="space-y-3">{datos.mis_fichas.map(f =>
                <li key={f.id} className="rounded-xl border border-tinta-200 p-4 dark:border-tinta-800">
                  <p className="font-medium text-tinta-900 first-letter:uppercase dark:text-tinta-100">{fechaFicha(f.starts_at)}</p>
                  <p className="mt-0.5 text-sm text-tinta-500">{f.practitioner} · {f.branch}{f.patient ? ` · para ${f.patient}` : ''}</p>
                  <p className="mt-2 text-xs text-tinta-500">{f.status_display}</p>
                </li>)}</ul>}
          </Bloque>
        </div>}

      </div>}
    </>}
  </main>
}
