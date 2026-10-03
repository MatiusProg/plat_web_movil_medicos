/**
 * Los planes de suscripción de la plataforma. Sólo la ve el superadministrador.
 *
 * Cada tarjeta muestra lo que el plan permite con las mismas palabras que usa
 * el resto del sistema: los topes que hace cumplir `tenancy/plans.py` y las
 * funciones que se encienden o no. Crear y editar se hace con `ModalPlan`.
 */

import { useEffect, useMemo, useState } from 'react'

import {
  actualizarPlan,
  crearPlan,
  listarPlanes,
  type DatosPlan,
  type PlanSuscripcion,
} from '@/api/suscripciones'
import { Boton } from '@/componentes/Boton'
import { ModalPlan, type DatosFormularioPlan } from '@/componentes/ModalPlan'
import { useTitulo } from '@/rutas/useTitulo'

import { ErrorCatalogo, IconoCatalogo, PANEL, SECONDARY, mensajeError } from './catalogo_comun'

type Filtro = 'todos' | 'activos' | 'inactivos'

/** Las funciones que un plan puede incluir, en el orden en que se muestran. */
const FUNCIONES: { clave: string; etiqueta: string }[] = [
  { clave: 'ai_chatbot', etiqueta: 'Asistente de orientación' },
  { clave: 'noshow_prediction', etiqueta: 'Predicción de inasistencia' },
  { clave: 'ai_summaries', etiqueta: 'Resúmenes con IA' },
  { clave: 'report_export', etiqueta: 'Exportar reportes' },
  { clave: 'online_payment', etiqueta: 'Pago en línea' },
]

const incluye = (plan: PlanSuscripcion, clave: string) => plan.features?.[clave] === true

function tope(valor: number | null) {
  return valor === null ? 'Sin límite' : valor.toLocaleString('es-BO')
}

function almacenamiento(mb: number | null) {
  if (mb === null) return 'Sin límite'
  return mb >= 1024 ? `${(mb / 1024).toLocaleString('es-BO', { maximumFractionDigits: 1 })} GB` : `${mb} MB`
}

function precio(plan: PlanSuscripcion) {
  const moneda = plan.currency === 'BOB' ? 'Bs' : plan.currency
  const monto = Number(plan.monthly_price).toLocaleString('es-BO', { maximumFractionDigits: 2 })
  return `${moneda} ${monto}`
}

const texto = (n: number | null) => (n === null ? '' : String(n))

function aFormulario(plan: PlanSuscripcion): DatosFormularioPlan {
  return {
    id: plan.id,
    name: plan.name,
    code: plan.code,
    description: plan.description ?? '',
    price: plan.monthly_price,
    currency: plan.currency,
    maxUsers: texto(plan.max_users),
    maxBranches: texto(plan.max_branches),
    maxPractitioners: texto(plan.max_practitioners),
    maxAppointmentsMonth: texto(plan.max_appointments_month),
    maxAiQueriesMonth: texto(plan.max_ai_queries_month),
    storageMb: texto(plan.storage_mb),
    chatbot: incluye(plan, 'ai_chatbot'),
    noShowPrediction: incluye(plan, 'noshow_prediction'),
    aiSummaries: incluye(plan, 'ai_summaries'),
    reportExport: incluye(plan, 'report_export'),
    onlinePayment: incluye(plan, 'online_payment'),
    active: plan.is_active,
  }
}

const numero = (v: string) => (v.trim() ? Number(v) : null)

function aDatos(f: DatosFormularioPlan): DatosPlan {
  return {
    code: f.code.trim(),
    name: f.name.trim(),
    description: f.description.trim(),
    monthly_price: f.price,
    currency: f.currency,
    max_users: numero(f.maxUsers),
    max_branches: numero(f.maxBranches),
    max_practitioners: numero(f.maxPractitioners),
    max_appointments_month: numero(f.maxAppointmentsMonth),
    max_ai_queries_month: numero(f.maxAiQueriesMonth),
    storage_mb: numero(f.storageMb),
    features: {
      ai_chatbot: f.chatbot,
      noshow_prediction: f.noShowPrediction,
      ai_summaries: f.aiSummaries,
      report_export: f.reportExport,
      online_payment: f.onlinePayment,
    },
    is_active: f.active,
  }
}

export function Planes() {
  useTitulo('Planes de suscripción')
  const [planes, setPlanes] = useState<PlanSuscripcion[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [filtro, setFiltro] = useState<Filtro>('todos')
  const [modal, setModal] = useState<{ modo: 'crear' | 'editar'; plan: PlanSuscripcion | null } | null>(null)
  const [guardando, setGuardando] = useState(false)

  useEffect(() => {
    let vigente = true
    listarPlanes()
      .then(r => { if (vigente) setPlanes(r.results) })
      .catch(e => { if (vigente) setError(mensajeError(e)) })
    return () => { vigente = false }
  }, [])

  const visibles = useMemo(() => (planes ?? [])
    .filter(p => filtro === 'todos' || (filtro === 'activos') === p.is_active)
    .sort((a, b) => Number(a.monthly_price) - Number(b.monthly_price)), [planes, filtro])

  const inactivos = (planes ?? []).filter(p => !p.is_active).length

  async function guardar(formulario: DatosFormularioPlan) {
    if (!modal) return
    setGuardando(true)
    setError(null)
    try {
      const datos = aDatos(formulario)
      if (modal.modo === 'editar' && modal.plan) {
        const actualizado = await actualizarPlan(modal.plan.id, datos)
        setPlanes(ps => (ps ?? []).map(p => (p.id === actualizado.id ? actualizado : p)))
      } else {
        const nuevo = await crearPlan(datos)
        setPlanes(ps => [...(ps ?? []), nuevo])
      }
      setModal(null)
    } catch (e) {
      setError(mensajeError(e))
    } finally {
      setGuardando(false)
    }
  }

  return <main className="mx-auto max-w-6xl space-y-6 px-5 py-8 sm:py-10">
    <div className="surgir flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-marca-700 dark:text-marca-400">Plataforma</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-tinta-900 dark:text-tinta-50">Planes de suscripción</h1>
        <p className="mt-1.5 max-w-2xl text-[0.9375rem] text-tinta-500">
          Lo que cada plan permite. Los topes se hacen cumplir en todo el sistema: un centro no puede pasarse de ellos.
        </p>
      </div>
      <Boton type="button" className="w-auto" onClick={() => setModal({ modo: 'crear', plan: null })}>
        <IconoCatalogo nombre="plus" className="size-4" />Nuevo plan
      </Boton>
    </div>

    {error && <ErrorCatalogo mensaje={error} />}

    {planes && inactivos > 0 && (
      <div role="group" aria-label="Filtrar planes" className="inline-flex rounded-lg border border-tinta-200 p-1 dark:border-tinta-800">
        {([['todos', 'Todos'], ['activos', 'Activos'], ['inactivos', 'Inactivos']] as const).map(([valor, etiqueta]) =>
          <button key={valor} type="button" aria-pressed={filtro === valor} onClick={() => setFiltro(valor)}
            className={['rounded-md px-3 py-1.5 text-sm font-medium transition',
              filtro === valor ? 'bg-tinta-100 text-tinta-900 dark:bg-tinta-800 dark:text-tinta-50' : 'text-tinta-500 hover:text-tinta-800 dark:hover:text-tinta-200'].join(' ')}>
            {etiqueta}
          </button>)}
      </div>
    )}

    {planes === null && !error && <p className="text-sm text-tinta-500">Cargando planes…</p>}

    {planes && planes.length === 0 && (
      <div className={`${PANEL} text-center`}>
        <p className="font-semibold text-tinta-900 dark:text-tinta-50">Todavía no hay planes.</p>
        <p className="mt-1 text-sm text-tinta-500">Crea el primero para poder asignarlo a las organizaciones.</p>
      </div>
    )}

    {planes && planes.length > 0 && visibles.length === 0 && (
      <p className="text-sm text-tinta-500">No hay planes {filtro === 'activos' ? 'activos' : 'inactivos'}.</p>
    )}

    <section className="grid gap-5 lg:grid-cols-3">
      {visibles.map(plan => <TarjetaPlan key={plan.id} plan={plan} onEditar={() => setModal({ modo: 'editar', plan })} />)}
    </section>

    <ModalPlan
      abierto={modal !== null}
      modo={modal?.modo ?? 'crear'}
      inicial={modal?.plan ? aFormulario(modal.plan) : null}
      guardando={guardando}
      onCerrar={() => { if (!guardando) setModal(null) }}
      onGuardar={guardar}
    />
  </main>
}

function TarjetaPlan({ plan, onEditar }: { plan: PlanSuscripcion; onEditar: () => void }) {
  const conAsistente = incluye(plan, 'ai_chatbot')
  const topes: [string, string][] = [
    ['Personal', tope(plan.max_users)],
    ['Sucursales', tope(plan.max_branches)],
    ['Profesionales', tope(plan.max_practitioners)],
    ['Fichas al mes', tope(plan.max_appointments_month)],
    ['Consultas al asistente al mes', conAsistente ? tope(plan.max_ai_queries_month) : 'No incluye'],
    ['Almacenamiento', almacenamiento(plan.storage_mb)],
  ]

  return <article className={`${PANEL} flex flex-col ${plan.is_active ? '' : 'opacity-75'}`}>
    <div className="flex items-start justify-between gap-3">
      <h2 className="text-lg font-semibold text-tinta-900 dark:text-tinta-50">{plan.name}</h2>
      <span className={['inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
        plan.is_active ? 'bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-300' : 'bg-tinta-100 text-tinta-500 dark:bg-tinta-800'].join(' ')}>
        {plan.is_active ? 'Activo' : 'Inactivo'}
      </span>
    </div>
    {plan.description && <p className="mt-1 text-sm leading-6 text-tinta-500">{plan.description}</p>}

    <p className="mt-4 flex items-baseline gap-1.5">
      <span className="text-3xl font-semibold tracking-tight text-tinta-900 tabular-nums dark:text-tinta-50">{precio(plan)}</span>
      <span className="text-sm text-tinta-500">al mes</span>
    </p>

    <dl className="mt-5 divide-y divide-tinta-100 border-y border-tinta-100 text-sm dark:divide-tinta-800 dark:border-tinta-800">
      {topes.map(([etiqueta, valor]) =>
        <div key={etiqueta} className="flex items-center justify-between gap-3 py-2">
          <dt className="text-tinta-500">{etiqueta}</dt>
          <dd className={['font-medium tabular-nums', valor === 'No incluye' ? 'text-tinta-400' : 'text-tinta-800 dark:text-tinta-100'].join(' ')}>{valor}</dd>
        </div>)}
    </dl>

    <ul className="mt-4 flex-1 space-y-2 text-sm">
      {FUNCIONES.map(f => {
        const si = incluye(plan, f.clave)
        return <li key={f.clave} className={['flex items-center gap-2.5', si ? 'text-tinta-700 dark:text-tinta-200' : 'text-tinta-400'].join(' ')}>
          {si
            ? <IconoCatalogo nombre="check" className="size-4 shrink-0 text-marca-600 dark:text-marca-400" />
            : <IconoCatalogo nombre="close" className="size-4 shrink-0" />}
          <span>{f.etiqueta}<span className="sr-only">{si ? ': incluido' : ': no incluido'}</span></span>
        </li>
      })}
    </ul>

    <button type="button" onClick={onEditar} className={`${SECONDARY} mt-6 w-full`}>
      <IconoCatalogo nombre="edit" className="size-4" />Editar plan
    </button>
  </article>
}
