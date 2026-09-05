/**
 * US-03 — Pedir el enlace para restablecer la contraseña (punto a).
 *
 * **Lo importante de esta pantalla es lo que NO hace:** no dice si el correo
 * existe. El backend responde siempre lo mismo, y acá se muestra ese mismo
 * mensaje sin intentar adivinar nada. Si la pantalla distinguiera —"no
 * encontramos esa cuenta"— serviría para averiguar quién es paciente de qué
 * centro médico sin necesidad de entrar.
 *
 * Lo único que sí se informa es que el centro médico no exista: el slug no es
 * un secreto —hace falta conocerlo para poder entrar— y callarlo dejaría a
 * quien se equivocó esperando un correo que nunca va a llegar.
 */

import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { solicitarRecuperacion } from '@/api/recuperacion'
import { ErrorApi } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { Boton } from '@/componentes/Boton'
import { Campo } from '@/componentes/Campo'
import { PanelMarca } from '@/componentes/PanelMarca'
import { IconoCorreo, IconoEdificio } from '@/componentes/iconos'
import { useTitulo } from '@/rutas/useTitulo'
import { leerOrganizacion } from '@/sesion/almacenamiento'

export function RecuperarAcceso() {
  useTitulo('Recuperar el acceso')

  const [organizacion, setOrganizacion] = useState(leerOrganizacion)
  const [email, setEmail] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<ErrorApi | null>(null)
  const [enviado, setEnviado] = useState<string | null>(null)

  const aborto = useRef<AbortController | null>(null)
  useEffect(() => () => aborto.current?.abort(), [])

  const errorOrganizacion =
    error?.codigo === 'organizacion_no_disponible'
      ? (error.porCampo?.organization?.[0] ?? error.message)
      : undefined

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault()
    setEnviando(true)
    setError(null)

    aborto.current?.abort()
    const control = new AbortController()
    aborto.current = control

    try {
      const respuesta = await solicitarRecuperacion(
        { organization: organizacion.trim(), email: email.trim() },
        control.signal,
      )
      setEnviado(respuesta.detail)
    } catch (e: unknown) {
      if (e instanceof DOMException && e.name === 'AbortError') return
      setError(e instanceof ErrorApi ? e : null)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="grid min-h-dvh lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
      <PanelMarca organizacion={organizacion.trim() || undefined} />

      <section className="flex items-center justify-center px-5 py-10 sm:px-8 lg:px-12">
        <div className="surgir w-full max-w-[26rem]">
          {enviado ? (
            <Confirmacion mensaje={enviado} />
          ) : (
            <>
              <header className="mb-8">
                <h1 className="text-tinta-900 dark:text-tinta-50 text-2xl font-semibold tracking-tight">
                  Recuperá tu acceso
                </h1>
                <p className="text-tinta-500 dark:text-tinta-400 mt-1.5 text-[0.9375rem]">
                  Te mandamos un enlace por correo para que elijas una
                  contraseña nueva. Dura 30 minutos y sirve una sola vez.
                </p>
              </header>

              <form onSubmit={enviar} noValidate className="space-y-5">
                <Campo
                  etiqueta="Centro médico"
                  name="organization"
                  autoComplete="organization"
                  spellCheck={false}
                  required
                  placeholder="kolping"
                  value={organizacion}
                  onChange={(e) => setOrganizacion(e.target.value)}
                  disabled={enviando}
                  icono={<IconoEdificio className="size-5" />}
                  error={errorOrganizacion}
                  ayuda="El mismo con el que entrás: tu correo puede estar
                         registrado en más de un centro médico."
                />

                <Campo
                  etiqueta="Correo electrónico"
                  type="email"
                  name="email"
                  autoComplete="username"
                  inputMode="email"
                  spellCheck={false}
                  required
                  placeholder="nombre@centromedico.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={enviando}
                  icono={<IconoCorreo className="size-5" />}
                />

                {error && !errorOrganizacion && (
                  <Aviso codigo={error.codigo} mensaje={error.message} />
                )}

                <Boton type="submit" cargando={enviando} textoCargando="Enviando…">
                  Enviarme el enlace
                </Boton>
              </form>
            </>
          )}

          <p className="text-tinta-500 dark:text-tinta-400 mt-8 text-center text-sm">
            ¿Te acordaste?{' '}
            <Link
              to="/ingresar"
              className="text-marca-600 dark:text-marca-400 font-semibold hover:underline"
            >
              Volvé a iniciar sesión
            </Link>
          </p>
        </div>
      </section>
    </main>
  )
}

/**
 * El mismo mensaje se muestre o no se haya encontrado la cuenta.
 *
 * Reemplaza al formulario en vez de aparecer debajo: si el formulario siguiera
 * ahí, la reacción natural es volver a probar con otro correo, que es
 * exactamente el tanteo que esta pantalla no debe facilitar.
 */
function Confirmacion({ mensaje }: { mensaje: string }) {
  return (
    <div className="text-center">
      <span className="bg-marca-50 text-marca-700 dark:bg-marca-950 dark:text-marca-400 mx-auto grid size-12 place-items-center rounded-2xl">
        <IconoCorreo className="size-6" />
      </span>

      <h1 className="text-tinta-900 dark:text-tinta-50 mt-4 text-2xl font-semibold tracking-tight">
        Revisá tu correo
      </h1>

      <p className="text-tinta-500 dark:text-tinta-400 mt-2 text-[0.9375rem]">
        {mensaje}
      </p>

      <p className="text-tinta-400 mt-6 text-sm">
        El enlace vence en 30 minutos. Si no llega, revisá el correo no deseado
        antes de pedir otro: pedir uno nuevo invalida el anterior.
      </p>
    </div>
  )
}
