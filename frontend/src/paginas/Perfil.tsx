/**
 * US-05 — Mi perfil: datos de contacto y contraseña.
 *
 * Tres bloques, y la separación es la de la historia:
 *
 * 1. **Datos de contacto** —nombres, teléfono, correo—, lo único editable. Se
 *    manda sólo lo que cambió (punto f).
 * 2. **Tu cuenta** —documento, centro médico, rol, estado—, a la vista pero
 *    sin casillas. Cambiarlos es del administrador (punto d), y decirlo evita
 *    que alguien busque por toda la pantalla cómo hacerlo.
 * 3. **Contraseña**, acreditando la actual. No cierra esta sesión (punto c):
 *    el backend devuelve un par de tokens nuevo y la sesión lo guarda.
 */

import { useEffect, useState, type FormEvent, type ReactNode } from 'react'

import {
  actualizarPerfil,
  cambiarContrasena,
  obtenerPerfil,
  type DatosEditables,
  type Perfil as DatosPerfil,
} from '@/api/perfil'
import { ErrorApi } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { Boton } from '@/componentes/Boton'
import { Campo } from '@/componentes/Campo'
import { IconoCorreo, IconoLlave, IconoOjo, IconoOjoTachado } from '@/componentes/iconos'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'

const NOMBRE_DOCUMENTO: Record<string, string> = {
  CI: 'Cédula de identidad',
  PAS: 'Pasaporte',
  NIT: 'NIT',
  OTRO: 'Otro',
}

export function Perfil() {
  const { token } = useSesion()
  useTitulo('Mi perfil')

  const [perfil, setPerfil] = useState<DatosPerfil | null>(null)
  const [error, setError] = useState<ErrorApi | null>(null)

  useEffect(() => {
    const control = new AbortController()
    obtenerPerfil({ token }, control.signal)
      .then(setPerfil)
      .catch((fallo: unknown) => {
        if (fallo instanceof DOMException && fallo.name === 'AbortError') return
        setError(fallo instanceof ErrorApi ? fallo : null)
      })
    return () => control.abort()
    // Con cada renovación del token se vuelve a pedir, y no pisa lo que se
    // esté escribiendo: el formulario toma el perfil sólo al montarse.
  }, [token])

  return (
    <main className="mx-auto max-w-3xl space-y-6 px-5 py-10">
      <div className="surgir">
        <p className="text-marca-700 dark:text-marca-400 text-sm font-medium">
          Mi perfil
        </p>
        <h1 className="text-tinta-900 dark:text-tinta-50 mt-1 text-2xl font-semibold tracking-tight">
          {perfil?.full_name ?? 'Tus datos'}
        </h1>
        <p className="text-tinta-500 mt-1.5 text-[0.9375rem]">
          Mantén al día tus datos de contacto: son los que usa tu centro médico
          para avisarte de tus fichas.
        </p>
      </div>

      {error && <Aviso codigo={error.codigo} mensaje={error.message} />}

      {!perfil && !error && (
        <p className="text-tinta-500 text-[0.9375rem]">Cargando tu perfil…</p>
      )}

      {perfil && (
        <>
          <DatosDeContacto perfil={perfil} alGuardar={setPerfil} />
          <TuCuenta perfil={perfil} />
          <CambioDeContrasena />
        </>
      )}
    </main>
  )
}

// ---------------------------------------------------------------------------
//  1. Datos de contacto
// ---------------------------------------------------------------------------

type Formulario = Required<DatosEditables>

function DatosDeContacto({
  perfil,
  alGuardar,
}: {
  perfil: DatosPerfil
  alGuardar: (perfil: DatosPerfil) => void
}) {
  const { token, actualizar } = useSesion()

  const [datos, setDatos] = useState<Formulario>(() => desdePerfil(perfil))
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState<ErrorApi | null>(null)
  const [guardado, setGuardado] = useState(false)

  const original = desdePerfil(perfil)
  const cambios = Object.fromEntries(
    Object.entries(datos).filter(
      ([campo, valor]) => valor !== original[campo as keyof Formulario],
    ),
  ) as DatosEditables
  const hayCambios = Object.keys(cambios).length > 0

  const cambiar = (campo: keyof Formulario) => (valor: string) => {
    setDatos((previos) => ({ ...previos, [campo]: valor }))
    setGuardado(false)
  }

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault()
    if (!hayCambios) return
    setGuardando(true)
    setError(null)
    try {
      const nuevo = await actualizarPerfil(cambios, { token })
      alGuardar(nuevo)
      setDatos(desdePerfil(nuevo))
      // La barra lateral muestra el nombre desde la sesión: sin esto seguiría
      // diciendo el anterior hasta volver a entrar.
      actualizar({ usuario: { full_name: nuevo.full_name, email: nuevo.email } })
      setGuardado(true)
    } catch (fallo: unknown) {
      setError(fallo instanceof ErrorApi ? fallo : null)
    } finally {
      setGuardando(false)
    }
  }

  const errorDe = (campo: keyof Formulario) => error?.porCampo?.[campo]?.[0]

  return (
    <Tarjeta titulo="Datos de contacto">
      <form onSubmit={enviar} noValidate className="space-y-5">
        <div className="grid gap-5 sm:grid-cols-2">
          <Campo
            etiqueta="Nombres"
            name="first_name"
            autoComplete="given-name"
            required
            value={datos.first_name}
            onChange={(e) => cambiar('first_name')(e.target.value)}
            disabled={guardando}
            error={errorDe('first_name')}
          />
          <Campo
            etiqueta="Apellidos"
            name="last_name"
            autoComplete="family-name"
            required
            value={datos.last_name}
            onChange={(e) => cambiar('last_name')(e.target.value)}
            disabled={guardando}
            error={errorDe('last_name')}
          />
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <Campo
            etiqueta="Teléfono"
            name="phone"
            type="tel"
            autoComplete="tel"
            inputMode="tel"
            placeholder="70000000"
            value={datos.phone}
            onChange={(e) => cambiar('phone')(e.target.value)}
            disabled={guardando}
            error={errorDe('phone')}
          />
          <Campo
            etiqueta="Correo"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={datos.email}
            onChange={(e) => cambiar('email')(e.target.value)}
            disabled={guardando}
            icono={<IconoCorreo className="size-5" />}
            error={errorDe('email')}
            ayuda="Es el correo con el que inicias sesión."
          />
        </div>

        {error && !error.porCampo && (
          <Aviso codigo={error.codigo} mensaje={error.message} />
        )}
        {guardado && <Confirmacion>Tus datos se guardaron.</Confirmacion>}

        <div className="flex justify-end">
          <Boton
            type="submit"
            cargando={guardando}
            textoCargando="Guardando…"
            disabled={!hayCambios}
            className="sm:w-auto"
          >
            Guardar cambios
          </Boton>
        </div>
      </form>
    </Tarjeta>
  )
}

function desdePerfil(perfil: DatosPerfil): Formulario {
  return {
    first_name: perfil.first_name,
    last_name: perfil.last_name,
    phone: perfil.phone,
    email: perfil.email,
  }
}

// ---------------------------------------------------------------------------
//  2. Tu cuenta — lo que no se edita acá
// ---------------------------------------------------------------------------

function TuCuenta({ perfil }: { perfil: DatosPerfil }) {
  return (
    <Tarjeta titulo="Tu cuenta">
      <dl className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2">
        <Dato
          termino="Documento"
          valor={`${NOMBRE_DOCUMENTO[perfil.document_type] ?? perfil.document_type} ${perfil.document_number}`}
        />
        <Dato
          termino="Centro médico"
          valor={perfil.organization?.name ?? 'Plataforma'}
        />
        <Dato
          termino="Rol"
          valor={
            perfil.is_platform_admin
              ? 'Superadministrador de plataforma'
              : perfil.roles.map((rol) => rol.name).join(', ') || 'Sin rol asignado'
          }
        />
        <Dato termino="Estado" valor={perfil.is_active ? 'Activa' : 'Inactiva'} />
      </dl>
      <p className="text-tinta-500 mt-4 text-sm">
        Estos datos sólo los puede cambiar el administrador de tu centro médico.
      </p>
    </Tarjeta>
  )
}

// ---------------------------------------------------------------------------
//  3. Contraseña
// ---------------------------------------------------------------------------

function CambioDeContrasena() {
  const { token, actualizar } = useSesion()

  const [actual, setActual] = useState('')
  const [nueva, setNueva] = useState('')
  const [repetida, setRepetida] = useState('')
  const [verClave, setVerClave] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<ErrorApi | null>(null)
  const [cambiada, setCambiada] = useState<string | null>(null)

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault()
    setEnviando(true)
    setError(null)
    setCambiada(null)
    try {
      const respuesta = await cambiarContrasena({ actual, nueva, repetida }, { token })
      // Los DOS tokens: el backend mandó a la lista negra todos los refrescos
      // anteriores, incluido el de esta pestaña. Sin guardar el nuevo, la
      // sesión moriría sola a los 25 minutos, en la primera renovación.
      actualizar({ access: respuesta.access, refresh: respuesta.refresh })
      setActual('')
      setNueva('')
      setRepetida('')
      setCambiada(respuesta.detail)
    } catch (fallo: unknown) {
      setError(fallo instanceof ErrorApi ? fallo : null)
    } finally {
      setEnviando(false)
    }
  }

  const ojo = (
    <button
      type="button"
      onClick={() => setVerClave((v) => !v)}
      disabled={enviando}
      aria-label={verClave ? 'Ocultar las contraseñas' : 'Mostrar las contraseñas'}
      aria-pressed={verClave}
      className="text-tinta-400 hover:text-tinta-600 dark:hover:text-tinta-200 grid size-8 place-items-center rounded-lg transition disabled:opacity-50"
    >
      {verClave ? <IconoOjoTachado className="size-5" /> : <IconoOjo className="size-5" />}
    </button>
  )

  return (
    <Tarjeta titulo="Contraseña">
      <form onSubmit={enviar} noValidate className="space-y-5">
        <Campo
          etiqueta="Contraseña actual"
          type={verClave ? 'text' : 'password'}
          name="current_password"
          autoComplete="current-password"
          required
          value={actual}
          onChange={(e) => setActual(e.target.value)}
          disabled={enviando}
          icono={<IconoLlave className="size-5" />}
          accion={ojo}
          error={error?.porCampo?.current_password?.[0]}
        />

        <div className="grid gap-5 sm:grid-cols-2">
          <Campo
            etiqueta="Contraseña nueva"
            type={verClave ? 'text' : 'password'}
            name="password"
            autoComplete="new-password"
            required
            value={nueva}
            onChange={(e) => setNueva(e.target.value)}
            disabled={enviando}
            icono={<IconoLlave className="size-5" />}
            error={error?.porCampo?.password?.[0]}
            ayuda="Al menos 8 caracteres, que no sea sólo números ni se parezca a tu correo."
          />
          <Campo
            etiqueta="Repite la contraseña nueva"
            type={verClave ? 'text' : 'password'}
            name="password_confirmation"
            autoComplete="new-password"
            required
            value={repetida}
            onChange={(e) => setRepetida(e.target.value)}
            disabled={enviando}
            icono={<IconoLlave className="size-5" />}
            error={error?.porCampo?.password_confirmation?.[0]}
          />
        </div>

        {error && !error.porCampo && (
          <Aviso codigo={error.codigo} mensaje={error.message} />
        )}
        {cambiada && <Confirmacion>{cambiada}</Confirmacion>}

        <div className="flex justify-end">
          <Boton
            type="submit"
            cargando={enviando}
            textoCargando="Cambiando…"
            disabled={!actual || !nueva || !repetida}
            className="sm:w-auto"
          >
            Cambiar contraseña
          </Boton>
        </div>
      </form>
    </Tarjeta>
  )
}

// ---------------------------------------------------------------------------

function Tarjeta({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="surgir border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900/50 rounded-2xl border bg-white p-5 sm:p-6">
      <h2 className="text-tinta-400 mb-4 text-xs font-semibold tracking-wider uppercase">
        {titulo}
      </h2>
      {children}
    </section>
  )
}

function Dato({ termino, valor }: { termino: string; valor: string }) {
  return (
    <div>
      <dt className="text-tinta-400 text-xs">{termino}</dt>
      <dd className="text-tinta-700 dark:text-tinta-200 mt-0.5 font-medium">{valor}</dd>
    </div>
  )
}

function Confirmacion({ children }: { children: ReactNode }) {
  return (
    <div
      role="status"
      className="border-marca-200 bg-marca-50 text-marca-700 dark:border-marca-900 dark:bg-marca-950/40 dark:text-marca-300 rounded-xl border px-3.5 py-3 text-sm"
    >
      {children}
    </div>
  )
}
