import { useState, type FormEvent, useRef } from 'react'
import { Link } from 'react-router-dom'

import { registrarPaciente } from '@/api/registro'
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
  IconoEscudo,
} from '@/componentes/iconos'
import { useTitulo } from '@/rutas/useTitulo'

export function RegistroPaciente() {
  useTitulo('Registrarse como Paciente')

  const [organizacion, setOrganizacion] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [documentType, setDocumentType] = useState<'CI' | 'PAS' | 'NIT' | 'OTRO'>('CI')
  const [documentNumber, setDocumentNumber] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [phone, setPhone] = useState('')
  const [birthDate, setBirthDate] = useState('')
  const [sex, setSex] = useState<'M' | 'F' | 'X' | ''>('')

  const [verClave, setVerClave] = useState(false)
  const [verClaveConf, setVerClaveConf] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [exito, setExito] = useState(false)
  const [error, setError] = useState<ErrorApi | null>(null)

  const aborto = useRef<AbortController | null>(null)

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault()
    if (enviando) return

    if (password !== passwordConfirmation) {
      setError(
        new ErrorApi('Las contraseñas no coinciden.', 'desconocido', 400, {
          porCampo: { password_confirmation: ['Las contraseñas no coinciden.'] },
        }),
      )
      return
    }

    aborto.current?.abort()
    const control = new AbortController()
    aborto.current = control

    setEnviando(true)
    setError(null)

    try {
      await registrarPaciente(
        {
          organization: organizacion.trim(),
          email: email.trim(),
          password,
          password_confirmation: passwordConfirmation,
          document_type: documentType,
          document_number: documentNumber.trim(),
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          phone: phone.trim() || undefined,
          birth_date: birthDate || null,
          sex: sex || null,
        },
        control.signal,
      )
      setExito(true)
    } catch (fallo) {
      if (fallo instanceof DOMException && fallo.name === 'AbortError') return
      const apiError =
        fallo instanceof ErrorApi
          ? fallo
          : new ErrorApi('Ocurrió un error inesperado.', 'desconocido', 0)
      setError(apiError)
    } finally {
      setEnviando(false)
    }
  }

  if (exito) {
    return (
      <main className="grid min-h-dvh lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
        <PanelMarca organizacion={organizacion.trim() || undefined} />
        <section className="flex items-center justify-center px-5 py-10 sm:px-8 lg:px-12">
          <div className="surgir w-full max-w-[26rem] text-center space-y-6">
            <div className="mx-auto bg-marca-50 dark:bg-marca-950 text-marca-600 dark:text-marca-400 size-16 rounded-full flex items-center justify-center">
              <IconoEscudo className="size-8" />
            </div>
            <header>
              <h1 className="text-tinta-900 dark:text-tinta-50 text-2xl font-semibold tracking-tight">
                ¡Registro completado!
              </h1>
              <p className="text-tinta-500 dark:text-tinta-400 mt-2 text-[0.9375rem]">
                Tu cuenta de paciente ha sido creada exitosamente. Ya puedes iniciar sesión en la plataforma con tus credenciales.
              </p>
            </header>
            <Link
              to="/ingresar"
              className="bg-marca-600 hover:bg-marca-700 text-white w-full py-2.5 rounded-xl font-medium inline-block text-center transition"
            >
              Ir a iniciar sesión
            </Link>
          </div>
        </section>
      </main>
    )
  }

  return (
    <main className="grid min-h-dvh lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
      <PanelMarca organizacion={organizacion.trim() || undefined} />

      <section className="flex items-center justify-center px-5 py-10 sm:px-8 lg:px-12">
        <div className="surgir w-full max-w-[28rem] space-y-8">
          <header>
            <h1 className="text-tinta-900 dark:text-tinta-50 text-2xl font-semibold tracking-tight">
              Registrate como Paciente
            </h1>
            <p className="text-tinta-500 dark:text-tinta-400 mt-1.5 text-[0.9375rem]">
              Crea tu ficha demográfica y cuenta para acceder a la atención médica.
            </p>
          </header>

          <form onSubmit={enviar} noValidate className="space-y-4">
            <Campo
              etiqueta="Centro médico *"
              name="organization"
              autoComplete="off"
              spellCheck={false}
              placeholder="Ej: kolping"
              value={organizacion}
              onChange={(e) => setOrganizacion(e.target.value)}
              disabled={enviando}
              icono={<IconoEdificio className="size-5" />}
              error={error?.porCampo?.organization?.[0]}
              ayuda="Slug del centro médico en el que deseas registrarte."
              required
            />

            <div className="grid grid-cols-2 gap-4">
              <Campo
                etiqueta="Nombres *"
                name="first_name"
                autoComplete="given-name"
                placeholder="Juan"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                disabled={enviando}
                error={error?.porCampo?.first_name?.[0]}
                required
              />

              <Campo
                etiqueta="Apellidos *"
                name="last_name"
                autoComplete="family-name"
                placeholder="Pérez"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                disabled={enviando}
                error={error?.porCampo?.last_name?.[0]}
                required
              />
            </div>

            <div className="grid grid-cols-[1fr_2fr] gap-4">
              <div className="space-y-1.5">
                <label className="text-tinta-700 dark:text-tinta-300 block text-sm font-medium">
                  Tipo Doc. *
                </label>
                <select
                  value={documentType}
                  onChange={(e) => setDocumentType(e.target.value as any)}
                  disabled={enviando}
                  className="w-full rounded-xl border border-tinta-300 dark:border-tinta-700 bg-white dark:bg-tinta-900/60 dark:text-tinta-50 py-2.5 px-3 text-[0.9375rem] transition focus:border-marca-500 focus:ring-4 focus:ring-marca-500/25 focus:outline-none"
                >
                  <option value="CI">CI</option>
                  <option value="PAS">Pasaporte</option>
                  <option value="NIT">NIT</option>
                  <option value="OTRO">Otro</option>
                </select>
              </div>

              <Campo
                etiqueta="Nro. Documento *"
                name="document_number"
                placeholder="1234567"
                value={documentNumber}
                onChange={(e) => setDocumentNumber(e.target.value)}
                disabled={enviando}
                error={error?.porCampo?.document_number?.[0]}
                required
              />
            </div>

            <Campo
              etiqueta="Correo electrónico *"
              type="email"
              name="email"
              autoComplete="email"
              placeholder="ejemplo@correo.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={enviando}
              icono={<IconoCorreo className="size-5" />}
              error={error?.porCampo?.email?.[0]}
              required
            />

            <div className="grid grid-cols-2 gap-4">
              <Campo
                etiqueta="Contraseña *"
                type={verClave ? 'text' : 'password'}
                name="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={enviando}
                icono={<IconoLlave className="size-5" />}
                error={error?.porCampo?.password?.[0]}
                required
                accion={
                  <button
                    type="button"
                    onClick={() => setVerClave((v) => !v)}
                    disabled={enviando}
                    className="text-tinta-400 hover:text-tinta-600 dark:hover:text-tinta-200 grid size-8 place-items-center rounded-lg transition"
                  >
                    {verClave ? <IconoOjoTachado className="size-5" /> : <IconoOjo className="size-5" />}
                  </button>
                }
              />

              <Campo
                etiqueta="Confirmar *"
                type={verClaveConf ? 'text' : 'password'}
                name="password_confirmation"
                placeholder="••••••••"
                value={passwordConfirmation}
                onChange={(e) => setPasswordConfirmation(e.target.value)}
                disabled={enviando}
                icono={<IconoLlave className="size-5" />}
                error={error?.porCampo?.password_confirmation?.[0]}
                required
                accion={
                  <button
                    type="button"
                    onClick={() => setVerClaveConf((v) => !v)}
                    disabled={enviando}
                    className="text-tinta-400 hover:text-tinta-600 dark:hover:text-tinta-200 grid size-8 place-items-center rounded-lg transition"
                  >
                    {verClaveConf ? <IconoOjoTachado className="size-5" /> : <IconoOjo className="size-5" />}
                  </button>
                }
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Campo
                etiqueta="Teléfono"
                type="tel"
                name="phone"
                placeholder="70000000"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                disabled={enviando}
                error={error?.porCampo?.phone?.[0]}
              />

              <Campo
                etiqueta="F. Nacimiento"
                type="date"
                name="birth_date"
                value={birthDate}
                onChange={(e) => setBirthDate(e.target.value)}
                disabled={enviando}
                error={error?.porCampo?.birth_date?.[0]}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-tinta-700 dark:text-tinta-300 block text-sm font-medium">
                Sexo
              </label>
              <select
                value={sex}
                onChange={(e) => setSex(e.target.value as any)}
                disabled={enviando}
                className="w-full rounded-xl border border-tinta-300 dark:border-tinta-700 bg-white dark:bg-tinta-900/60 dark:text-tinta-50 py-2.5 px-3 text-[0.9375rem] transition focus:border-marca-500 focus:ring-4 focus:ring-marca-500/25 focus:outline-none"
              >
                <option value="">Seleccionar...</option>
                <option value="M">Masculino</option>
                <option value="F">Femenino</option>
                <option value="X">Otro</option>
              </select>
              {error?.porCampo?.sex && (
                <p className="text-alerta-600 dark:text-alerta-500 text-sm">
                  {error.porCampo.sex[0]}
                </p>
              )}
            </div>

            {error && !error.porCampo && (
              <Aviso codigo={error.codigo} mensaje={error.message} />
            )}

            <Boton type="submit" cargando={enviando} textoCargando="Registrando…">
              Registrarme
            </Boton>
          </form>

          <p className="text-tinta-500 dark:text-tinta-400 text-center text-sm">
            ¿Ya tienes cuenta?{' '}
            <Link to="/ingresar" className="text-marca-600 dark:text-marca-400 font-semibold hover:underline">
              Inicia sesión
            </Link>
          </p>
        </div>
      </section>
    </main>
  )
}
