/**
 * US-43 — Registrar una organización cliente (RF-W-01).
 *
 * El alta hace mucho más que crear una fila: en la misma transacción el
 * backend crea la organización, su suscripción, le copia adentro las plantillas
 * de rol del sistema y le genera el primer usuario administrador. Por eso el
 * formulario pide también los datos de esa persona: sin ella, la organización
 * nace sin nadie que pueda entrar.
 *
 * La contraseña temporal vuelve **una sola vez** en la respuesta. La pantalla
 * la muestra y avisa de eso; no hay forma de volver a consultarla.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import {
  crearOrganizacion,
  listarPlanes,
  type OrganizacionCreada,
  type Plan,
} from '@/api/organizaciones'
import { ErrorApi } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { Boton } from '@/componentes/Boton'
import { Cabecera } from '@/componentes/Cabecera'
import { Campo } from '@/componentes/Campo'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'

/** Lo que el backend valida y acá se adelanta, para no gastar un viaje. */
const FORMATO_SLUG = /^[a-z0-9]([a-z0-9-]{1,38}[a-z0-9])$/

export function AltaOrganizacion() {
  const { usuario, token } = useSesion()
  const navegar = useNavigate()
  const [planes, setPlanes] = useState<Plan[]>([])
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<ErrorApi | null>(null)
  const [creada, setCreada] = useState<OrganizacionCreada | null>(null)
  const control = useRef<AbortController | null>(null)
  useTitulo('Registrar organización')

  useEffect(() => {
    const señal = new AbortController()
    listarPlanes({ token }, señal.signal)
      .then((pagina) => setPlanes(pagina.results))
      .catch(() => setPlanes([]))
    return () => señal.abort()
  }, [token])

  // Si la persona se va a mitad del envío, la petición se cancela.
  useEffect(() => () => control.current?.abort(), [])

  const enviar = useCallback(
    async (evento: React.FormEvent<HTMLFormElement>) => {
      evento.preventDefault()
      const formulario = new FormData(evento.currentTarget)
      const texto = (clave: string) => String(formulario.get(clave) ?? '').trim()

      setError(null)
      setEnviando(true)
      control.current = new AbortController()

      try {
        const resultado = await crearOrganizacion(
          {
            slug: texto('slug'),
            name: texto('name'),
            legal_name: texto('legal_name'),
            tax_id: texto('tax_id'),
            contact_email: texto('contact_email'),
            contact_phone: texto('contact_phone'),
            address: texto('address'),
            city: texto('city'),
            plan_code: texto('plan_code'),
            admin: {
              email: texto('admin_email'),
              first_name: texto('admin_first_name'),
              last_name: texto('admin_last_name'),
              document_number: texto('admin_document_number'),
              phone: texto('admin_phone'),
            },
          },
          { token },
          control.current.signal,
        )
        setCreada(resultado)
      } catch (e: unknown) {
        if (e instanceof DOMException && e.name === 'AbortError') return
        setError(e instanceof ErrorApi ? e : null)
      } finally {
        setEnviando(false)
      }
    },
    [token],
  )

  if (!usuario) return null

  if (!usuario.is_platform_admin) {
    return (
      <div className="bg-tinta-50 dark:bg-tinta-950 min-h-dvh">
        <Cabecera />
        <main className="mx-auto max-w-4xl px-5 py-10">
          <p className="text-tinta-500 text-[0.9375rem]">
            Registrar organizaciones es del Superadministrador de Plataforma.
          </p>
        </main>
      </div>
    )
  }

  if (creada) {
    return (
      <div className="bg-tinta-50 dark:bg-tinta-950 min-h-dvh">
        <Cabecera />
        <main className="mx-auto max-w-2xl px-5 py-10">
          <Credenciales creada={creada} alTerminar={() => navegar('/organizaciones')} />
        </main>
      </div>
    )
  }

  return (
    <div className="bg-tinta-50 dark:bg-tinta-950 min-h-dvh">
      <Cabecera />

      <main className="mx-auto max-w-2xl space-y-6 px-5 py-10">
        <div className="surgir">
          <Link
            to="/organizaciones"
            className="text-tinta-500 hover:text-tinta-800 dark:hover:text-tinta-200 text-sm font-medium"
          >
            ← Organizaciones
          </Link>
          <h1 className="text-tinta-900 dark:text-tinta-50 mt-2 text-2xl font-semibold tracking-tight">
            Registrar organización
          </h1>
          <p className="text-tinta-500 mt-1.5 text-[0.9375rem]">
            Queda operativa al instante: con su plan, sus roles y su primer
            administrador.
          </p>
        </div>

        {error && (
          <Aviso
            codigo={error.codigo}
            mensaje={
              error.porCampo
                ? 'Revisá los datos marcados más abajo.'
                : error.message
            }
          />
        )}

        <form onSubmit={enviar} noValidate className="space-y-6">
          <Bloque titulo="El centro médico">
            <Campo
              etiqueta="Nombre comercial"
              name="name"
              required
              maxLength={120}
              autoComplete="organization"
              error={primerError(error, 'name')}
            />
            <Campo
              etiqueta="Razón social"
              name="legal_name"
              required
              maxLength={160}
              error={primerError(error, 'legal_name')}
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <Campo
                etiqueta="Identificador"
                name="slug"
                required
                maxLength={40}
                pattern={FORMATO_SLUG.source}
                ayuda="Lo que se escribe al iniciar sesión. Minúsculas, números y guiones."
                error={primerError(error, 'slug')}
              />
              <Campo
                etiqueta="NIT"
                name="tax_id"
                required
                maxLength={20}
                error={primerError(error, 'tax_id')}
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Campo
                etiqueta="Correo de contacto"
                name="contact_email"
                type="email"
                required
                maxLength={254}
                error={primerError(error, 'contact_email')}
              />
              <Campo
                etiqueta="Teléfono"
                name="contact_phone"
                maxLength={30}
                error={primerError(error, 'contact_phone')}
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Campo etiqueta="Dirección" name="address" maxLength={200} />
              <Campo etiqueta="Ciudad" name="city" maxLength={80} />
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="plan_code"
                className="text-tinta-700 dark:text-tinta-300 block text-sm font-medium"
              >
                Plan de suscripción
              </label>
              <select
                id="plan_code"
                name="plan_code"
                required
                defaultValue=""
                className="border-tinta-300 dark:border-tinta-700 dark:bg-tinta-900 text-tinta-900 dark:text-tinta-50 focus:border-marca-500 focus:ring-marca-500/30 w-full rounded-xl border bg-white px-3.5 py-2.5 text-[0.9375rem] transition focus:ring-4 focus:outline-none"
              >
                <option value="" disabled>
                  {planes.length === 0 ? 'Cargando planes…' : 'Elegí un plan'}
                </option>
                {planes.map((plan) => (
                  <option key={plan.id} value={plan.code}>
                    {plan.name} — {plan.monthly_price} {plan.currency}/mes
                  </option>
                ))}
              </select>
              {primerError(error, 'plan_code') && (
                <p className="text-sm text-red-600 dark:text-red-400">
                  {primerError(error, 'plan_code')}
                </p>
              )}
            </div>
          </Bloque>

          <Bloque
            titulo="Su administrador"
            nota="Recibe una contraseña temporal que se muestra una sola vez."
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <Campo
                etiqueta="Nombres"
                name="admin_first_name"
                required
                maxLength={80}
                error={primerError(error, 'admin')}
              />
              <Campo
                etiqueta="Apellidos"
                name="admin_last_name"
                required
                maxLength={80}
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Campo
                etiqueta="Correo"
                name="admin_email"
                type="email"
                required
                maxLength={254}
              />
              <Campo
                etiqueta="Documento"
                name="admin_document_number"
                required
                maxLength={20}
              />
            </div>
            <Campo etiqueta="Teléfono" name="admin_phone" maxLength={30} />
          </Bloque>

          <Boton
            type="submit"
            cargando={enviando}
            textoCargando="Registrando…"
            className="bg-marca-600 hover:bg-marca-700"
          >
            Registrar organización
          </Boton>
        </form>
      </main>
    </div>
  )
}

function Bloque({
  titulo,
  nota,
  children,
}: {
  titulo: string
  nota?: string
  children: React.ReactNode
}) {
  return (
    <section className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 space-y-4 rounded-2xl border bg-white px-5 py-5">
      <div>
        <h2 className="text-tinta-800 dark:text-tinta-100 font-semibold">{titulo}</h2>
        {nota && <p className="text-tinta-500 mt-0.5 text-sm">{nota}</p>}
      </div>
      {children}
    </section>
  )
}

/**
 * La pantalla de después del alta.
 *
 * Existe porque la contraseña temporal no se puede volver a consultar: si el
 * formulario simplemente volviera al listado, el dato se perdería para
 * siempre y la organización quedaría inaccesible para su dueño.
 */
function Credenciales({
  creada,
  alTerminar,
}: {
  creada: OrganizacionCreada
  alTerminar: () => void
}) {
  const [copiado, setCopiado] = useState(false)

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(
        `Organización: ${creada.slug}\nCorreo: ${creada.admin.email}\n` +
          `Contraseña temporal: ${creada.admin.temporary_password}`,
      )
      setCopiado(true)
    } catch {
      // Sin permiso de portapapeles queda el texto en pantalla para copiar a mano.
      setCopiado(false)
    }
  }

  return (
    <div className="surgir space-y-5">
      <div>
        <p className="text-marca-700 dark:text-marca-400 text-sm font-medium">
          Organización registrada
        </p>
        <h1 className="text-tinta-900 dark:text-tinta-50 mt-1 text-2xl font-semibold tracking-tight">
          {creada.name}
        </h1>
        <p className="text-tinta-500 mt-1.5 text-[0.9375rem]">
          Ya tiene su plan {creada.current_plan?.name}, sus roles y su
          administrador.
        </p>
      </div>

      <div className="rounded-2xl border border-amber-300 bg-amber-50 px-5 py-4 dark:border-amber-800 dark:bg-amber-950/40">
        <p className="font-semibold text-amber-900 dark:text-amber-200">
          Copiá la contraseña ahora
        </p>
        <p className="mt-1 text-sm text-amber-800 dark:text-amber-300">
          Se muestra una sola vez. No queda guardada en ningún lado y no hay
          forma de volver a consultarla: si se pierde, hay que restablecerla.
        </p>

        <dl className="mt-4 space-y-2 text-sm">
          <Dato termino="Organización" valor={creada.slug} />
          <Dato termino="Correo" valor={creada.admin.email} />
          <Dato termino="Contraseña temporal" valor={creada.admin.temporary_password} />
        </dl>

        <button
          type="button"
          onClick={copiar}
          className="mt-4 rounded-lg bg-amber-200 px-3 py-1.5 text-sm font-semibold text-amber-900 transition hover:bg-amber-300 dark:bg-amber-900 dark:text-amber-100 dark:hover:bg-amber-800"
        >
          {copiado ? 'Copiado' : 'Copiar los tres datos'}
        </button>
      </div>

      <Boton
        type="button"
        onClick={alTerminar}
        className="bg-marca-600 hover:bg-marca-700"
      >
        Ya la copié, volver al listado
      </Boton>
    </div>
  )
}

function Dato({ termino, valor }: { termino: string; valor: string }) {
  return (
    <div className="flex flex-wrap items-baseline gap-x-2">
      <dt className="text-amber-800 dark:text-amber-400">{termino}:</dt>
      <dd className="font-mono font-semibold text-amber-950 dark:text-amber-100">
        {valor}
      </dd>
    </div>
  )
}

/** El primer mensaje que el backend devolvió para ese campo, si lo hubo. */
function primerError(error: ErrorApi | null, campo: string): string | undefined {
  return error?.porCampo?.[campo]?.[0]
}
