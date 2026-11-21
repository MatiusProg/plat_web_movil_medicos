/**
 * El centro médico del login y del registro, en una lista desplegable.
 *
 * La lista viene del backend (`/accounts/centers/`): sólo las organizaciones
 * activas, así que se actualiza sola con las altas y las bajas. En el login
 * suma «Administración de la plataforma» para el superadministrador, que
 * entra sin organización (slug vacío).
 *
 * `valor`: `null` es «todavía no eligió»; `''` es la plataforma; si no, el
 * slug. Si la lista no se puede traer (sin conexión, backend caído), vuelve
 * el campo de texto de siempre para escribir el slug: el login nunca queda
 * bloqueado por esto.
 */
import { useEffect, useId, useState } from 'react'
import { listarCentros, type Centro } from '@/api/centros'
import { Campo } from './Campo'
import { IconoEdificio } from './iconos'

const PLATAFORMA = '__plataforma__'

interface Props {
  valor: string | null
  onCambio: (slug: string | null, nombre?: string) => void
  conPlataforma?: boolean
  disabled?: boolean
  error?: string
  ayuda?: string
  etiqueta?: string
}

export function SelectorCentro({ valor, onCambio, conPlataforma = false, disabled, error, ayuda, etiqueta = 'Centro médico' }: Props) {
  const id = useId()
  const [centros, setCentros] = useState<Centro[] | null>(null)
  const [sinLista, setSinLista] = useState(false)

  useEffect(() => {
    const c = new AbortController()
    listarCentros(c.signal)
      .then(setCentros)
      .catch(e => { if (!(e instanceof DOMException && e.name === 'AbortError')) setSinLista(true) })
    return () => c.abort()
  }, [])

  // El último centro usado puede haberse dado de baja: entonces no queda
  // elegido nada, en vez de mandar un slug que el login va a rechazar.
  // Si sigue activo, se avisa su nombre, para mostrarlo en vez del slug.
  useEffect(() => {
    if (!centros || !valor) return
    const centro = centros.find(c => c.slug === valor)
    onCambio(centro ? valor : null, centro?.name)
  }, [centros]) // eslint-disable-line react-hooks/exhaustive-deps -- sólo al llegar la lista

  if (sinLista) return <Campo etiqueta={etiqueta} name="organization" autoComplete="organization" spellCheck={false}
    placeholder="kolping" value={valor ?? ''} onChange={e => onCambio(e.target.value)} disabled={disabled}
    icono={<IconoEdificio className="size-5" />} error={error}
    ayuda={conPlataforma ? 'No pudimos cargar la lista: escribí el código del centro. Vacío sólo si administrás la plataforma.' : 'No pudimos cargar la lista: escribí el código del centro.'} />

  const seleccion = valor === null ? '' : valor === '' ? PLATAFORMA : valor
  const idAyuda = `${id}-ayuda`, idError = `${id}-error`
  return <div className="space-y-1.5">
    <label htmlFor={id} className="block text-sm font-medium text-tinta-700 dark:text-tinta-300">{etiqueta}</label>
    <div className="relative">
      <span className="pointer-events-none absolute inset-y-0 left-0 flex w-11 items-center justify-center text-tinta-400" aria-hidden="true">
        <IconoEdificio className="size-5" />
      </span>
      <select id={id} name="organization" value={seleccion} disabled={disabled || !centros}
        aria-invalid={error ? true : undefined}
        aria-describedby={[error ? idError : null, ayuda ? idAyuda : null].filter(Boolean).join(' ') || undefined}
        onChange={e => {
          const v = e.target.value
          if (v === PLATAFORMA) onCambio('')
          else onCambio(v || null, centros?.find(c => c.slug === v)?.name)
        }}
        className={[
          'w-full appearance-none rounded-xl border bg-white py-2.5 pl-11 pr-11 text-[1.0625rem] transition',
          'dark:bg-tinta-900/60 dark:text-tinta-50',
          seleccion ? 'text-tinta-900' : 'text-tinta-400 dark:text-tinta-400',
          error ? 'border-alerta-500 focus:border-alerta-500 focus:ring-alerta-500/25'
            : 'border-tinta-300 focus:border-marca-500 focus:ring-marca-500/25 dark:border-tinta-700',
          'focus:ring-4 focus:outline-none',
          'disabled:cursor-not-allowed disabled:bg-tinta-100 disabled:text-tinta-500 dark:disabled:bg-tinta-900',
        ].join(' ')}>
        <option value="" disabled>{centros ? 'Elegí tu centro médico' : 'Cargando centros…'}</option>
        {centros?.map(c => <option key={c.slug} value={c.slug}>{c.name}</option>)}
        {conPlataforma && <option value={PLATAFORMA}>Administración de la plataforma</option>}
      </select>
      <span className="pointer-events-none absolute inset-y-0 right-0 flex w-11 items-center justify-center text-tinta-400" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="size-5"><path d="m6 9 6 6 6-6" /></svg>
      </span>
    </div>
    {error && <p id={idError} className="text-sm text-alerta-600 dark:text-alerta-500">{error}</p>}
    {ayuda && !error && <p id={idAyuda} className="text-sm text-tinta-500">{ayuda}</p>}
  </div>
}
