/**
 * Los iconos, dibujados a mano en SVG.
 *
 * Sin librería de iconos: son ocho trazos y traer un paquete entero para eso
 * agrega un peso y una dependencia que después hay que mantener. Heredan
 * `currentColor`, así que toman el color del texto que los rodea y funcionan
 * igual en claro y en oscuro.
 */

type Props = { className?: string }

const base = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.75,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
}

export function IconoEdificio({ className }: Props) {
  return (
    <svg {...base} className={className}>
      <path d="M3 21h18" />
      <path d="M5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16" />
      <path d="M12 7v6M9 10h6" />
      <path d="M9 21v-3.5a3 3 0 0 1 6 0V21" />
    </svg>
  )
}

export function IconoCorreo({ className }: Props) {
  return (
    <svg {...base} className={className}>
      <rect x="2.5" y="4.5" width="19" height="15" rx="2.5" />
      <path d="m3.5 7 7.4 5.2a2 2 0 0 0 2.2 0L20.5 7" />
    </svg>
  )
}

export function IconoLlave({ className }: Props) {
  return (
    <svg {...base} className={className}>
      <circle cx="7.5" cy="15.5" r="4" />
      <path d="m10.4 12.6 8-8" />
      <path d="m15.5 7.5 2 2" />
      <path d="m18.4 4.6 2 2" />
    </svg>
  )
}

export function IconoOjo({ className }: Props) {
  return (
    <svg {...base} className={className}>
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

export function IconoOjoTachado({ className }: Props) {
  return (
    <svg {...base} className={className}>
      <path d="M3 3l18 18" />
      <path d="M10.6 6.1A9.6 9.6 0 0 1 12 6c6 0 9.5 6 9.5 6a17 17 0 0 1-3.2 3.9" />
      <path d="M6.3 8.1A17 17 0 0 0 2.5 12S6 18 12 18a9.3 9.3 0 0 0 3.6-.7" />
      <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
    </svg>
  )
}

export function IconoAlerta({ className }: Props) {
  return (
    <svg {...base} className={className}>
      <circle cx="12" cy="12" r="9.2" />
      <path d="M12 7.5v5.2" />
      <path d="M12 16.3h.01" />
    </svg>
  )
}

export function IconoCandado({ className }: Props) {
  return (
    <svg {...base} className={className}>
      <rect x="4.5" y="10.5" width="15" height="9.5" rx="2.5" />
      <path d="M8 10.5V7.8a4 4 0 0 1 8 0v2.7" />
      <path d="M12 14.3v2.2" />
    </svg>
  )
}

export function IconoSinConexion({ className }: Props) {
  return (
    <svg {...base} className={className}>
      <path d="M3 3l18 18" />
      <path d="M8.6 15.6a5 5 0 0 1 6.8 0" />
      <path d="M5.2 12.2a9.5 9.5 0 0 1 3.4-2.2" />
      <path d="M15.2 10a9.5 9.5 0 0 1 3.6 2.2" />
      <path d="M2 8.8A14 14 0 0 1 7 6" />
      <path d="M17 6a14 14 0 0 1 5 2.8" />
      <path d="M12 19h.01" />
    </svg>
  )
}

export function IconoEscudo({ className }: Props) {
  return (
    <svg {...base} className={className}>
      <path d="M12 2.8 4.5 5.8v5.6c0 4.4 3 8.4 7.5 9.8 4.5-1.4 7.5-5.4 7.5-9.8V5.8L12 2.8Z" />
      <path d="m9 12 2.2 2.2L15.3 10" />
    </svg>
  )
}

export function IconoPulso({ className }: Props) {
  return (
    <svg {...base} className={className}>
      <path d="M2.5 12h4l2-5.5 3.5 11 2.5-7 1.7 3h5.3" />
    </svg>
  )
}

export function IconoSalir({ className }: Props) {
  return (
    <svg {...base} className={className}>
      <path d="M14.5 8V6a2 2 0 0 0-2-2h-6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2v-2" />
      <path d="M10 12h11" />
      <path d="m18 9 3 3-3 3" />
    </svg>
  )
}
