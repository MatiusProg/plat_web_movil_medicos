/**
 * US-03 — Elegir la contraseña nueva (puntos e, f, g y h).
 *
 * El token y el slug llegan en la URL, tal como los puso el correo:
 *
 *     /restablecer?token=<token>&organization=<slug>
 *
 * **El enlace se comprueba al abrir la pantalla**, antes de mostrar el
 * formulario. Es lo que evita que alguien escriba una contraseña nueva dos
 * veces para recién entonces enterarse de que el enlace venció. Los tres
 * motivos —vencido, ya usado, inválido— se distinguen y cada uno dice qué
 * hacer, que es el punto (h) de la historia.
 *
 * Al terminar, el backend cierra todas las sesiones abiertas del usuario
 * (punto f), así que la pantalla manda a iniciar sesión de nuevo y no intenta
 * dejar a nadie adentro.
 */

import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { confirmarRecuperacion, verificarEnlace } from '@/api/recuperacion'
import { ErrorApi } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { Boton } from '@/componentes/Boton'
import { Campo } from '@/componentes/Campo'
import { PanelMarca } from '@/componentes/PanelMarca'
import {
  IconoLlave,
  IconoOjo,
  IconoOjoTachado,
} from '@/componentes/iconos'
import { useTitulo } from '@/rutas/useTitulo'

export function RestablecerContrasena() {
  const [parametros] = useSearchParams()
  const navegar = useNavigate()
  useTitulo('Elegir una contraseña nueva')

  const token = parametros.get('token') ?? ''
  const organizacion = parametros.get('organization') ?? ''

  // Que falte una de las dos partes se sabe con sólo mirar la URL: no hace
  // falta preguntarle al backend, ni pasar por un estado "comprobando" que
  // nunca va a resolverse.
  const enlaceIncompleto = !token || !organizacion

  const [comprobando, setComprobando] = useState(!enlaceIncompleto)
  const [correo, setCorreo] = useState<string | null>(null)
  const [errorEnlace, setErrorEnlace] = useState<ErrorApi | null>(null)

  const [password, setPassword] = useState('')
  const [confirmacion, setConfirmacion] = useState('')
  const [verClave, setVerClave] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<ErrorApi | null>(null)

  const aborto = useRef<AbortController | null>(null)
  useEffect(() => () => aborto.current?.abort(), [])

  // Comprobación del enlace al entrar.
  useEffect(() => {
    if (!token || !organizacion) return

    const control = new AbortController()

    verificarEnlace(organizacion, token, control.signal)
      .then((respuesta) => {
        setCorreo(respuesta.email)
        setComprobando(false)
      })
      .catch((e: unknown) => {
        if (e instanceof DOMException && e.name === 'AbortError') return
        setErrorEnlace(e instanceof ErrorApi ? e : null)
        setComprobando(false)
      })

    return () => control.abort()
  }, [token, organizacion])

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault()
    setEnviando(true)
    setError(null)

    aborto.current?.abort()
    const control = new AbortController()
    aborto.current = control

    try {
      await confirmarRecuperacion(
        organizacion,
        token,
        password,
        confirmacion,
        control.signal,
      )
      // Todas las sesiones quedaron cerradas, así que el único camino
      // razonable es volver a entrar — ahora con la contraseña nueva.
      navegar('/ingresar', {
        replace: true,
        state: { aviso: 'Tu contraseña se cambió. Entrá con la nueva.' },
      })
    } catch (e: unknown) {
      if (e instanceof DOMException && e.name === 'AbortError') return
      const fallo = e instanceof ErrorApi ? e : null
      // Si lo que caducó es el enlace, no tiene sentido dejar el formulario:
      // por más que escriba bien la contraseña, no va a poder guardarla.
      if (fallo && ENLACE_ROTO.has(fallo.codigo)) setErrorEnlace(fallo)
      else setError(fallo)
    } finally {
      setEnviando(false)
    }
  }

  // Un enlace a medias y uno que el backend rechazó se muestran igual: en los
  // dos casos lo único que se puede hacer es pedir otro.
  const enlaceRoto =
    errorEnlace ?? (enlaceIncompleto ? ENLACE_INCOMPLETO : null)

  return (
    <main className="grid min-h-dvh lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
      <PanelMarca organizacion={organizacion || undefined} />

      <section className="flex items-center justify-center px-5 py-10 sm:px-8 lg:px-12">
        <div className="surgir w-full max-w-[26rem]">
          {comprobando ? (
            <p className="text-tinta-500 text-center text-[0.9375rem]">
              Comprobando el enlace…
            </p>
          ) : enlaceRoto ? (
            <EnlaceRoto error={enlaceRoto} />
          ) : (
            <>
              <header className="mb-8">
                <h1 className="text-tinta-900 dark:text-tinta-50 text-2xl font-semibold tracking-tight">
                  Elegí una contraseña nueva
                </h1>
                <p className="text-tinta-500 dark:text-tinta-400 mt-1.5 text-[0.9375rem]">
                  Para la cuenta <strong>{correo}</strong>. Al guardarla se
                  cierran todas las sesiones que tengas abiertas.
                </p>
              </header>

              <form onSubmit={enviar} noValidate className="space-y-5">
                <Campo
                  etiqueta="Contraseña nueva"
                  type={verClave ? 'text' : 'password'}
                  name="password"
                  autoComplete="new-password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={enviando}
                  icono={<IconoLlave className="size-5" />}
                  error={error?.porCampo?.password?.[0]}
                  ayuda="Al menos 8 caracteres. Que no sea sólo números ni una
                         contraseña habitual, y que no se parezca a tu correo."
                  accion={
                    <button
                      type="button"
                      onClick={() => setVerClave((v) => !v)}
                      disabled={enviando}
                      aria-label={
                        verClave ? 'Ocultar la contraseña' : 'Mostrar la contraseña'
                      }
                      aria-pressed={verClave}
                      className="text-tinta-400 hover:text-tinta-600 dark:hover:text-tinta-200 grid size-8 place-items-center rounded-lg transition disabled:opacity-50"
                    >
                      {verClave ? (
                        <IconoOjoTachado className="size-5" />
                      ) : (
                        <IconoOjo className="size-5" />
                      )}
                    </button>
                  }
                />

                <Campo
                  etiqueta="Repetí la contraseña"
                  type={verClave ? 'text' : 'password'}
                  name="password_confirmation"
                  autoComplete="new-password"
                  required
                  placeholder="••••••••"
                  value={confirmacion}
                  onChange={(e) => setConfirmacion(e.target.value)}
                  disabled={enviando}
                  icono={<IconoLlave className="size-5" />}
                  error={error?.porCampo?.password_confirmation?.[0]}
                />

                {error && !error.porCampo && (
                  <Aviso codigo={error.codigo} mensaje={error.message} />
                )}

                <Boton type="submit" cargando={enviando} textoCargando="Guardando…">
                  Guardar y volver a entrar
                </Boton>
              </form>
            </>
          )}
        </div>
      </section>
    </main>
  )
}

/** Los códigos que dejan el formulario sin sentido: el enlace ya no sirve. */
const ENLACE_ROTO = new Set(['enlace_invalido', 'enlace_usado', 'enlace_vencido'])

/** Falta el token o el slug en la URL. Se detecta sin preguntarle al backend. */
const ENLACE_INCOMPLETO = new ErrorApi(
  'El enlace está incompleto. Copialo entero desde el correo, o pedí uno nuevo.',
  'enlace_invalido',
  400,
)

function EnlaceRoto({ error }: { error: ErrorApi }) {
  return (
    <div className="text-center">
      <Aviso codigo={error.codigo} mensaje={error.message} />

      <p className="text-tinta-500 dark:text-tinta-400 mt-6 text-[0.9375rem]">
        Los enlaces duran 30 minutos y sirven una sola vez. Pedí uno nuevo y
        usalo apenas te llegue.
      </p>

      <Link
        to="/recuperar"
        className="bg-marca-600 hover:bg-marca-700 focus-visible:outline-marca-600 mt-6 inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-[0.9375rem] font-semibold text-white transition focus-visible:outline-2 focus-visible:outline-offset-2"
      >
        Pedir un enlace nuevo
      </Link>

      <p className="text-tinta-500 dark:text-tinta-400 mt-8 text-sm">
        <Link
          to="/ingresar"
          className="text-marca-600 dark:text-marca-400 font-semibold hover:underline"
        >
          Volver a iniciar sesión
        </Link>
      </p>
    </div>
  )
}
