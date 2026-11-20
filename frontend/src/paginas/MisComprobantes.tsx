/**
 * Mis comprobantes: pedirlos hablando o escribiendo.
 *
 * «Mis últimas 2 facturas», «los pagos de octubre», «mis fichas de
 * cardiología»: el paciente dice qué quiere y ve la lista con el **código QR**
 * de cada comprobante, que es el mismo de la ficha (`ModalComprobante`) y el
 * que lee recepción al llegar. También se baja en PDF con los QR.
 *
 * Dos pasos, y la voz no ejecuta sola: primero se muestra **qué entendió el
 * sistema** («Pagos con comprobante · últimos 2») y recién después aparece la
 * lista. Si no entendió, dice qué no pudo y no muestra nada: una lista de más
 * se leería como si fuera lo que se pidió.
 *
 * **Solo lo propio.** La pantalla nunca manda de quién son los datos: el
 * backend lo decide con la sesión, y son los del paciente y sus dependientes.
 * Por eso cada comprobante dice a quién pertenece.
 *
 * **Agrupar es solo cómo se muestra.** «Mis facturas de los últimos 3 meses
 * agrupadas por sucursal» trae los mismos comprobantes que sin agrupar,
 * repartidos en secciones que dicen cuántos tienen y cuánto suman.
 */

import { QRCodeSVG } from 'qrcode.react'
import { useEffect, useRef, useState } from 'react'

import { ETIQUETA_ESTADO_FICHA } from '@/api/fichas'
import {
  descargarComprobantesPdf, interpretarComprobantes, listarComprobantes,
  type Comprobante, type Consulta, type Grupo, type ListaDeComprobantes, type Propuesta,
} from '@/api/misComprobantes'
import { EntradaDeVoz } from '@/componentes/EntradaDeVoz'
import { ErrorCatalogo, mensajeError, PANEL, SECONDARY } from '@/paginas/catalogo_comun'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'

function fecha(iso: string): string {
  return new Date(iso).toLocaleString('es-BO', {
    day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function importe(c: Comprobante): string {
  const moneda = c.currency === 'BOB' ? 'Bs' : (c.currency ?? '')
  return `${moneda} ${Number(c.amount).toFixed(2)}`
}

function total(totales: Grupo['totals']): string {
  return totales
    .map((t) => `${t.currency === 'BOB' ? 'Bs' : t.currency} ${Number(t.amount).toFixed(2)}`)
    .join(' + ')
}

export function MisComprobantes() {
  const { token, usuario, puede } = useSesion()
  useTitulo('Mis comprobantes')

  const [propuesta, setPropuesta] = useState<Propuesta | null>(null)
  const [lista, setLista] = useState<ListaDeComprobantes | null>(null)
  const [consulta, setConsulta] = useState<Consulta | null>(null)
  const [buscando, setBuscando] = useState(false)
  const [descargando, setDescargando] = useState(false)
  const [error, setError] = useState('')
  const control = useRef<AbortController | null>(null)

  // Salir de la pantalla corta la consulta en curso.
  useEffect(() => () => control.current?.abort(), [])

  const esPaciente = Boolean(usuario?.roles.some((r) => r.code === 'patient'))
  if (!esPaciente || !puede('appointments.appointment.read')) {
    return (
      <main className="mx-auto max-w-5xl px-5 py-8 sm:py-10">
        <p className="text-sm text-tinta-500">Esta pantalla es para pacientes.</p>
      </main>
    )
  }

  const buscar = async (texto: string) => {
    control.current?.abort()
    const actual = new AbortController()
    control.current = actual
    setBuscando(true)
    setError('')
    setLista(null)
    setConsulta(null)
    try {
      const entendido = await interpretarComprobantes(texto, { token }, actual.signal)
      setPropuesta(entendido)
      if (!entendido.understood || !entendido.consulta) return
      const resultado = await listarComprobantes(entendido.consulta, { token }, actual.signal)
      setConsulta(entendido.consulta)
      setLista(resultado)
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') return
      setError(mensajeError(e))
    } finally {
      if (control.current === actual) setBuscando(false)
    }
  }

  const bajarPdf = async () => {
    if (!consulta) return
    setDescargando(true)
    setError('')
    try {
      await descargarComprobantesPdf(consulta, { token })
    } catch (e) {
      setError(mensajeError(e))
    } finally {
      setDescargando(false)
    }
  }

  return (
    <main className="mx-auto max-w-5xl space-y-6 px-5 py-8 sm:py-10">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-tinta-900 dark:text-tinta-50">
          Mis comprobantes
        </h1>
        <p className="mt-1.5 text-[1.0625rem] text-tinta-500">
          Pídelos hablando o escribiendo y verás el código QR de cada uno.
        </p>
      </div>

      <section className={PANEL} aria-labelledby="pedido-titulo">
        <h2 id="pedido-titulo" className="sr-only">Hacer un pedido</h2>
        <EntradaDeVoz
          etiqueta="¿Qué quieres ver?"
          placeholder="Mis últimas 2 facturas"
          alEnviar={(texto) => void buscar(texto)}
          ocupado={buscando}
        />
        <p className="mt-4 text-sm text-tinta-500">
          Por ejemplo: «mis últimas 2 facturas», «los pagos de octubre» o «mis fichas de
          cardiología». Aquí salen tus comprobantes y los de las personas a tu cargo.
        </p>
      </section>

      {error && <ErrorCatalogo mensaje={error} />}
      {propuesta && !buscando && <LoQueEntendio propuesta={propuesta} />}
      {lista && (
        <Resultados lista={lista} descargando={descargando} alDescargar={() => void bajarPdf()} />
      )}
    </main>
  )
}

// --------------------------------------------------------------------------
//  Lo que entendió el sistema
// --------------------------------------------------------------------------
function LoQueEntendio({ propuesta }: { propuesta: Propuesta }) {
  return (
    <section
      className="rounded-xl border border-tinta-200 p-4 text-sm dark:border-tinta-800"
      aria-live="polite"
    >
      {propuesta.understood ? (
        <p className="text-tinta-800 dark:text-tinta-100">Entendí: {propuesta.spoken_summary}</p>
      ) : (
        <p className="font-medium text-tinta-800 dark:text-tinta-100">
          No pude entender tu pedido.
        </p>
      )}
      {propuesta.unresolved.length > 0 && (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-tinta-500">
          {propuesta.unresolved.map((motivo) => (
            <li key={motivo}>{motivo}</li>
          ))}
        </ul>
      )}
    </section>
  )
}

// --------------------------------------------------------------------------
//  La lista
// --------------------------------------------------------------------------
function Resultados({
  lista,
  descargando,
  alDescargar,
}: {
  lista: ListaDeComprobantes
  descargando: boolean
  alDescargar: () => void
}) {
  if (lista.count === 0) {
    return (
      <p className={`${PANEL} text-sm text-tinta-500`} role="status">
        No encontré comprobantes con ese pedido.
      </p>
    )
  }

  return (
    <section aria-labelledby="resultados-titulo" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="resultados-titulo" className="font-semibold text-tinta-900 dark:text-tinta-100">
          {lista.count} {lista.count === 1 ? 'comprobante' : 'comprobantes'}
        </h2>
        <button type="button" className={SECONDARY} onClick={alDescargar} disabled={descargando}>
          {descargando ? 'Descargando…' : 'Descargar PDF'}
        </button>
      </div>

      {lista.truncated && (
        <p className="text-sm text-tinta-500">
          Hay más de los que se muestran. Pide menos, por ejemplo «mis últimas 5 facturas» o un
          mes.
        </p>
      )}

      {lista.groups.length > 0 ? (
        <div className="space-y-8">
          {lista.groups.map((grupo) => (
            <SeccionDeGrupo key={grupo.key} grupo={grupo} tipo={lista.tipo} />
          ))}
        </div>
      ) : (
        <ListaDeTarjetas items={lista.items} tipo={lista.tipo} />
      )}
    </section>
  )
}

function ListaDeTarjetas({
  items,
  tipo,
}: {
  items: Comprobante[]
  tipo: ListaDeComprobantes['tipo']
}) {
  return (
    <ul className="grid gap-4 sm:grid-cols-2">
      {items.map((item) => (
        <TarjetaDeComprobante key={item.id} item={item} tipo={tipo} />
      ))}
    </ul>
  )
}

/** Un grupo: su nombre, cuántos comprobantes tiene y cuánto suman. */
function SeccionDeGrupo({ grupo, tipo }: { grupo: Grupo; tipo: ListaDeComprobantes['tipo'] }) {
  const titulo = `grupo-${grupo.key}`
  return (
    <section aria-labelledby={titulo} className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-tinta-200 pb-2 dark:border-tinta-800">
        <h3 id={titulo} className="font-semibold text-tinta-900 dark:text-tinta-50">
          {grupo.label}
        </h3>
        <p className="text-sm text-tinta-500">
          {grupo.count} {grupo.count === 1 ? 'comprobante' : 'comprobantes'}
          {grupo.totals.length > 0 && ` · ${total(grupo.totals)}`}
        </p>
      </div>
      <ListaDeTarjetas items={grupo.items} tipo={tipo} />
    </section>
  )
}

function TarjetaDeComprobante({
  item,
  tipo,
}: {
  item: Comprobante
  tipo: ListaDeComprobantes['tipo']
}) {
  return (
    <li className={`${PANEL} flex gap-4`}>
      <div className="min-w-0 flex-1 space-y-1.5 text-sm">
        <p className="font-semibold text-tinta-900 dark:text-tinta-50">
          {tipo === 'pagos' ? `Pagado el ${fecha(item.date)}` : `Ficha del ${fecha(item.date)}`}
        </p>
        {tipo === 'pagos' && (
          <p className="text-tinta-500">Ficha del {fecha(item.starts_at)}</p>
        )}
        <p className="text-tinta-800 dark:text-tinta-100">
          {item.patient_name}
          {item.is_dependent && (
            <span className="ml-2 rounded-full bg-marca-50 px-2 py-0.5 text-xs font-medium text-marca-700 dark:bg-marca-950/40 dark:text-marca-300">
              Dependiente
            </span>
          )}
        </p>
        <p className="text-tinta-500">
          {item.practitioner_name}
          {item.specialties.length > 0 && ` · ${item.specialties.join(', ')}`}
        </p>
        <p className="text-tinta-500">{item.branch_name}</p>
        <p className="font-medium text-tinta-800 dark:text-tinta-100">
          {tipo === 'pagos' ? importe(item) : ETIQUETA_ESTADO_FICHA[item.status]}
        </p>
      </div>
      <div
        className="h-fit shrink-0 rounded-xl bg-white p-2"
        role="img"
        aria-label={`Código QR del comprobante de ${item.patient_name}, ${fecha(item.starts_at)}`}
      >
        <QRCodeSVG value={item.code} size={120} level="M" marginSize={1} />
      </div>
    </li>
  )
}
