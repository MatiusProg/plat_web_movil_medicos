/**
 * US-02 — Pantalla de inicio de sesión.
 *
 * Cómo se manejan los errores del backend, que es donde está casi todo el
 * trabajo de esta pantalla:
 *
 *   401 credenciales_invalidas    → cartel rojo, foco de vuelta en la contraseña
 *   423 cuenta_bloqueada          → cartel ámbar con cuenta regresiva en vivo,
 *                                   formulario deshabilitado hasta que venza
 *   403 cuenta_inactiva           → cartel rojo, sin reintentar
 *   400 organizacion_no_disponible→ error debajo del campo de organización
 *   0   sin_conexion              → el backend no está corriendo
 *
 * Se compara siempre contra `codigo`, nunca contra el texto del mensaje.
 */

import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useLocation, useNavigate, Link } from 'react-router-dom'

import { ErrorApi } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { Boton } from '@/componentes/Boton'
import { Campo } from '@/componentes/Campo'
import { PanelMarca } from '@/componentes/PanelMarca'
import {
  IconoCorreo,
  IconoEdificio,
  IconoLlave,
  IconoOjo,
  IconoOjoTachado,
} from '@/componentes/iconos'
import { useTitulo } from '@/rutas/useTitulo'
import { leerOrganizacion } from '@/sesion/almacenamiento'
import { useSesion } from '@/sesion/useSesion'

export function InicioSesion() {
  const { entrar, usuario } = useSesion()
  const navegar = useNavigate()
  const ubicacion = useLocation()
  useTitulo('Iniciar sesión')

  const [organizacion, setOrganizacion] = useState(leerOrganizacion)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [verClave, setVerClave] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<ErrorApi | null>(null)

  const campoClave = useRef<HTMLInputElement>(null)
  const aborto = useRef<AbortController | null>(null)

  // A dónde volver después de entrar. Si llegó acá porque una ruta protegida
  // lo rebotó, se lo devuelve a esa ruta y no al inicio.
  const destino =
    (ubicacion.state as { desde?: string } | null)?.desde ?? '/panel'

  // US-03 deja este mensaje al volver de cambiar la contraseña. Sin él, la
  // persona aterriza en el login sin ninguna señal de que el cambio funcionó.
  const avisoDeVuelta =
    (ubicacion.state as { aviso?: string } | null)?.aviso ?? null

  useEffect(() => {
    if (usuario) navegar(destino, { replace: true })
  }, [usuario, destino, navegar])

  // Cancelar la petición si la pantalla se desmonta a mitad de camino.
  useEffect(() => () => aborto.current?.abort(), [])

  const bloqueada = error?.codigo === 'cuenta_bloqueada'
  const inactiva = error?.codigo === 'cuenta_inactiva'
  const errorOrganizacion =
    error?.codigo === 'organizacion_no_disponible'
      ? (error.porCampo?.organization?.[0] ?? error.message)
      : undefined

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault()
    if (enviando || bloqueada) return

    aborto.current?.abort()
    const control = new AbortController()
    aborto.current = control

    setEnviando(true)
    setError(null)
    try {
      await entrar(
        { organizacion: organizacion.trim(), email: email.trim(), password },
        control.signal,
      )
      // La redirección la hace el efecto de arriba, en cuanto `usuario` cambia.
    } catch (fallo) {
      if (fallo instanceof DOMException && fallo.name === 'AbortError') return
      const apiError =
        fallo instanceof ErrorApi
          ? fallo
          : new ErrorApi('Ocurrió un error inesperado.', 'desconocido', 0)
      setError(apiError)
      setPassword('')
      // Devolver el foco al campo que hay que corregir ahorra un tab a quien
      // navega con teclado, y le dice a un lector de pantalla dónde está.
      if (apiError.codigo === 'credenciales_invalidas') {
        campoClave.current?.focus()
      }
    } finally {
      setEnviando(false)
    }
  }

  const formularioTrabado = enviando || bloqueada || inactiva

  return (
    <main className="grid min-h-dvh lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
      <PanelMarca organizacion={organizacion.trim() || undefined} />

      {/* ---------------- Formulario ---------------- */}
      <section className="flex items-center justify-center px-5 py-10 sm:px-8 lg:px-12">
        <div className="surgir w-full max-w-[26rem]">
          <header className="mb-8">
            <h1 className="text-tinta-900 dark:text-tinta-50 text-2xl font-semibold tracking-tight">
              Iniciá sesión
            </h1>
            <p className="text-tinta-500 dark:text-tinta-400 mt-1.5 text-[0.9375rem]">
              Ingresá con tus credenciales para acceder según tu rol.
            </p>
          </header>

          {avisoDeVuelta && (
            <p
              role="status"
              className="mb-6 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700 dark:border-emerald-500/40 dark:bg-emerald-500/10 dark:text-emerald-300"
            >
              {avisoDeVuelta}
            </p>
          )}

          <form onSubmit={enviar} noValidate className="space-y-5">
            <Campo
              etiqueta="Centro médico"
              name="organization"
              autoComplete="organization"
              spellCheck={false}
              placeholder="kolping"
              value={organizacion}
              onChange={(e) => setOrganizacion(e.target.value)}
              disabled={formularioTrabado}
              icono={<IconoEdificio className="size-5" />}
              error={errorOrganizacion}
              ayuda="Dejalo vacío sólo si administrás la plataforma."
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
              disabled={formularioTrabado}
              icono={<IconoCorreo className="size-5" />}
            />

            <Campo
              ref={campoClave}
              etiqueta="Contraseña"
              type={verClave ? 'text' : 'password'}
              name="password"
              autoComplete="current-password"
              required
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={formularioTrabado}
              icono={<IconoLlave className="size-5" />}
              accion={
                <button
                  type="button"
                  onClick={() => setVerClave((v) => !v)}
                  disabled={formularioTrabado}
                  aria-label={verClave ? 'Ocultar la contraseña' : 'Mostrar la contraseña'}
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

            {error && !errorOrganizacion && (
              <div className={error.codigo === 'credenciales_invalidas' ? 'temblar' : ''}>
                <Aviso
                  codigo={error.codigo}
                  mensaje={error.message}
                  bloqueadaHasta={error.bloqueadaHasta}
                  alVencer={() => setError(null)}
                />
              </div>
            )}

            <Boton type="submit" cargando={enviando} textoCargando="Verificando…" disabled={bloqueada || inactiva}>
              Entrar
            </Boton>
          </form>

          {/* US-03. El enlace va debajo del formulario y no arriba: se lo
              busca recién después de que la contraseña no funcionó. */}
          <p className="mt-5 text-center text-sm">
            <Link
              to="/recuperar"
              className="text-marca-600 dark:text-marca-400 font-semibold hover:underline"
            >
              ¿Olvidaste tu contraseña?
            </Link>
          </p>

          <p className="text-tinta-500 dark:text-tinta-400 mt-8 text-center text-sm">
            ¿No tenés una cuenta?{' '}
            <Link to="/registro" className="text-marca-600 dark:text-marca-400 font-semibold hover:underline">
              Registrate acá
            </Link>
          </p>

          <p className="text-tinta-400 mt-4 text-center text-xs">
            Tu contraseña se guarda cifrada y nunca viaja en texto plano.
          </p>
        </div>
      </section>
    </main>
  )
}
