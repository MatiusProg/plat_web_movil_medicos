
/**
 * La navegación de las pantallas con sesión.
 *
 * **Cada historia agrega su entrada en `items`.** Es el archivo que más
 * historias comparten del frontend, así que cada una toca su bloque y no la
 * línea de al lado — la misma regla que `urls.py` en el backend.
 *
 * La barra no decide si se ve plegada o abierta: eso lo lleva
 * `ArmazonPlataforma`, que es quien también corre el contenido. Acá sólo se
 * dibuja según lo que llega por props.
 *
 * **Tres detalles que no son estéticos:**
 *
 * - La lista de opciones tiene su propio `overflow-y-auto`. Sin eso, cada
 *   entrada nueva empujaba el bloque de perfil hacia abajo hasta sacarlo de la
 *   pantalla, y un administrador con todos los permisos no llegaba a ver su
 *   propio botón de cerrar sesión.
 * - Plegada, cada opción conserva su `title`: un icono sin nombre no dice nada,
 *   y en un panel de administración médica adivinar no es una opción.
 * - El estado activo se marca con una barrita de color además del fondo, para
 *   que se distinga sin depender sólo del color.
 */

import { useEffect, useRef, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'

import {
    IconoEdificio,
    IconoEscudo,
    IconoPulso,
    IconoSalir,
} from '@/componentes/iconos'

import { pedir } from '@/api/cliente'
import { useSesion } from '@/sesion/useSesion'
import { guardarTema, leerTema, type Tema } from '@/tema/tema'


type ItemMenu = {
    etiqueta: string
    ruta: string
    icono:
        | 'panel'
        | 'organizaciones'
        | 'planes'
        | 'suscripciones'
        | 'roles'
        | 'usuarios'
        | 'bitacora'
        | 'agendas'
        | 'catalogo'
        | 'asistente'
        | 'perfil'
        | 'calendario'
        | 'reloj'
        | 'buscar'
        | 'ficha'
        | 'estetoscopio'
        | 'servicio'
        | 'respaldo'
        | 'historia'
    /**
     * Quién ve la entrada.
     *
     * `'plataforma'` es del Superadministrador y se decide por
     * `is_platform_admin`, no por permisos: su lista de permisos llega vacía
     * porque `user_roles` está protegida por RLS y sus filas irían con
     * `organization_id` NULL. Cualquier otro valor es un código de permiso y
     * se consulta con `puede`. Sin `requiere`, la entrada la ve todo el mundo.
     *
     * `'paciente'` es para lo que sólo tiene sentido si la persona es
     * paciente del centro: el médico también tiene `encounters.history.read`,
     * pero "mi historia" de alguien que no es paciente estaría vacía.
     *
     * Esconder una entrada no autoriza nada: la puerta real la pone el
     * backend en cada endpoint.
     */
    requiere?: 'plataforma' | 'paciente' | string
    /** El grupo del menú: ordena las opciones por lo que la persona va a hacer. */
    seccion: Seccion
    /**
     * La función del plan que la opción necesita (`features` del plan). Si el
     * plan del centro no la incluye, la opción no se ofrece: la puerta real la
     * pone el backend (tenancy/plans.py); esto evita un botón que diga que no.
     */
    requierePlan?: string
}

type Seccion = 'General' | 'Atención' | 'Catálogo' | 'Organización' | 'Plataforma'

/** El orden en que se muestran los grupos. */
const SECCIONES: Seccion[] = ['General', 'Atención', 'Catálogo', 'Organización', 'Plataforma']


const items: ItemMenu[] = [
    {
        etiqueta: 'Panel',
        ruta: '/panel',
        seccion: 'General',
        icono: 'panel',
    },
    {
        etiqueta: 'Organizaciones',
        ruta: '/organizaciones',
        seccion: 'Plataforma',
        icono: 'organizaciones',
        requiere: 'plataforma',
    },
    {
        etiqueta: 'Planes',
        ruta: '/planes',
        seccion: 'Plataforma',
        icono: 'planes',
        requiere: 'plataforma',
    },
    {
        etiqueta: 'Suscripciones',
        ruta: '/suscripciones',
        seccion: 'Plataforma',
        icono: 'suscripciones',
        requiere: 'plataforma',
    },

    // US-04 — administración de la organización.
    {
        etiqueta: 'Roles y permisos',
        ruta: '/roles',
        seccion: 'Organización',
        icono: 'roles',
        requiere: 'users.role.read',
    },
    {
        etiqueta: 'Usuarios',
        ruta: '/usuarios',
        seccion: 'Organización',
        icono: 'usuarios',
        requiere: 'users.user.read',
    },

    // US-06 — bitácora de auditoría.
    {
        etiqueta: 'Bitácora',
        ruta: '/bitacora',
        seccion: 'Organización',
        icono: 'bitacora',
        requiere: 'audit.log.read',
    },
    // Característica general 6 — la frecuencia depende del plan.
    {
        etiqueta: 'Copias de seguridad',
        ruta: '/respaldos',
        seccion: 'Organización',
        icono: 'respaldo',
        requiere: 'backups.backup.create',
    },

    // US-11 — administración de sucursales.
    {
        etiqueta: 'Sucursales',
        ruta: '/sucursales',
        seccion: 'Catálogo',
        icono: 'organizaciones',
        requiere: 'catalog.branch.read',
    },

    // US-12: administracion del catalogo medico.
    {
        etiqueta: 'Especialidades',
        ruta: '/especialidades',
        seccion: 'Catálogo',
        icono: 'estetoscopio',
        requiere: 'catalog.specialty.read',
    },
    {
        etiqueta: 'Profesionales',
        ruta: '/profesionales',
        seccion: 'Catálogo',
        icono: 'usuarios',
        requiere: 'catalog.professional.read',
    },
    // US-32 — precio y preparación, el corpus administrativo del asistente.
    {
        etiqueta: 'Servicios',
        ruta: '/servicios',
        seccion: 'Catálogo',
        icono: 'servicio',
        requiere: 'catalog.service.read',
    },
    // US-09 / US-10 — consulta y gestión de pacientes.
    {
        etiqueta: 'Pacientes',
        ruta: '/pacientes',
        seccion: 'Atención',
        icono: 'usuarios',
        requiere: 'patients.patient.read',
    },

    // US-22 — check-in en recepción.
    {
        etiqueta: 'Check-in',
        ruta: '/check-in',
        seccion: 'Atención',
        icono: 'ficha',
        requiere: 'appointments.appointment.read',
    },

    // US-24 — la agenda del profesional para registrar la atención.
    {
        etiqueta: 'Atención',
        ruta: '/atencion',
        seccion: 'Atención',
        icono: 'estetoscopio',
        requiere: 'encounters.encounter.read',
    },

    // US-13 a US-16 — agendas y catálogo.
    {
        etiqueta: 'Agendas',
        ruta: '/agendas',
        seccion: 'Atención',
        icono: 'calendario',
        requiere: 'scheduling.schedule.read',
    },
    {
        etiqueta: 'Disponibilidad',
        ruta: '/disponibilidad',
        seccion: 'Atención',
        icono: 'reloj',
        requiere: 'scheduling.slot.read',
    },
    {
        etiqueta: 'Buscar profesionales',
        ruta: '/buscar-profesionales',
        seccion: 'Atención',
        icono: 'buscar',
        requiere: 'catalog.professional.read',
    },

    // US-17 / US-20 — reserva, cancelación y reprogramación de fichas.
    {
        etiqueta: 'Mis fichas',
        ruta: '/mis-fichas',
        seccion: 'Atención',
        icono: 'ficha',
        requiere: 'appointments.appointment.read',
    },

    // US-25 — la historia clínica, vista por el propio paciente.
    {
        etiqueta: 'Mi historia clínica',
        ruta: '/mi-historia',
        seccion: 'Atención',
        icono: 'historia',
        requiere: 'paciente',
    },

    // US-31 / US-34 — asistente de orientación.
    {
        etiqueta: 'Asistente',
        ruta: '/asistente',
        requierePlan: 'ai_chatbot',
        seccion: 'General',
        icono: 'asistente',
        requiere: 'assistant.suggest.use',
    },

    // US-05 — edición de perfil. Sin `requiere`: todo el que entra tiene uno.
    {
        etiqueta: 'Mi perfil',
        ruta: '/perfil',
        seccion: 'General',
        icono: 'perfil',
    },
]


interface Props {
    /** Sólo a partir de `md`: en móvil la barra es un cajón, no una franja. */
    plegada: boolean
    alternarPlegada: () => void
    abiertaEnMovil: boolean
    cerrarEnMovil: () => void
}


/** "Laura Gómez" → "LG". Para el avatar del pie. */
function iniciales(nombre: string) {
    const partes = nombre.trim().split(/\s+/).filter(Boolean)
    return ((partes[0]?.[0] ?? '') + (partes[1]?.[0] ?? '')).toUpperCase() || '·'
}


export function BarraPlataforma({
    plegada,
    alternarPlegada,
    abiertaEnMovil,
    cerrarEnMovil,
}: Props) {
    const { usuario, salir, puede, token } = useSesion()
    const navigate = useNavigate()

    // Qué incluye el plan del centro, para no ofrecer lo que no tiene.
    // Mientras carga (o si falla) se muestra todo: el backend igual corta.
    const [funciones, setFunciones] = useState<Record<string, unknown> | null>(null)
    useEffect(() => {
        if (!token || usuario?.is_platform_admin) return
        const control = new AbortController()
        pedir<{ features: Record<string, unknown> }>('/platform/my-plan/', { token, senal: control.signal })
            .then((plan) => setFunciones(plan.features))
            .catch(() => {})
        return () => control.abort()
    }, [token, usuario?.is_platform_admin])
    // La etiqueta flotante de la barra plegada. Va en una capa fija y no al
    // lado de cada opción: la lista tiene scroll propio y recortaría todo lo
    // que sobresale hacia el costado.
    const [flotante, setFlotante] = useState<{ texto: string; top: number } | null>(null)
    const mostrar = (texto: string) => (evento: React.MouseEvent | React.FocusEvent) => {
        if (!plegada) return
        const caja = (evento.currentTarget as HTMLElement).getBoundingClientRect()
        setFlotante({ texto, top: caja.top + caja.height / 2 })
    }
    const ocultar = () => setFlotante(null)

    const visibles = items.filter((item) => {
        if (item.requierePlan && funciones && funciones[item.requierePlan] === false) return false
        if (!item.requiere) return true
        if (item.requiere === 'plataforma') return Boolean(usuario?.is_platform_admin)
        if (item.requiere === 'paciente') {
            return Boolean(usuario?.roles?.some((r) => r.code === 'patient')) && puede('encounters.history.read')
        }
        return puede(item.requiere)
    })

    // Los grupos que tienen al menos una opción visible, en su orden.
    const grupos = SECCIONES
        .map((seccion) => ({ seccion, opciones: visibles.filter((i) => i.seccion === seccion) }))
        .filter((g) => g.opciones.length > 0)

    const cerrarSesion = async () => {
        await salir()
        navigate('/ingresar')
    }

    // Plegada sólo aplica de `md` para arriba. Dentro del cajón de móvil las
    // etiquetas se ven siempre: ahí sobra el ancho.
    const soloAncha = plegada ? 'md:hidden' : ''
    const nombre = usuario?.full_name || 'Superadministrador'
    const rol = usuario?.is_platform_admin
        ? 'Administración de la plataforma'
        : usuario?.roles?.[0]?.name ?? 'Usuario'

    return (
        <aside
            className={[
                'group/barra fixed inset-y-0 left-0 z-40 flex h-dvh flex-col bg-tinta-900 text-tinta-300',
                'transition-[width,transform] duration-200 ease-out',
                'w-64',
                plegada ? 'md:w-[4.25rem]' : 'md:w-64',
                abiertaEnMovil ? 'translate-x-0' : '-translate-x-full',
                'md:translate-x-0',
            ].join(' ')}
        >
            {/* Marca, centro médico y el botón de la barra, como en los
                asistentes de chat: a la derecha de la marca cuando está
                abierta; plegada, el logo se convierte en ese botón al pasar el
                mouse. Ctrl+B hace lo mismo. */}
            <div className={['group/cabecera flex h-16 shrink-0 items-center gap-3 px-4', plegada ? 'md:justify-center md:px-0' : ''].join(' ')}>
                <div className={['grid size-9 shrink-0 place-items-center rounded-xl bg-marca-500 text-tinta-950', plegada ? 'md:group-hover/cabecera:hidden' : ''].join(' ')}>
                    <IconoEscudo className="size-5" />
                </div>
                {plegada && (
                    <button
                        type="button"
                        onClick={alternarPlegada}
                        aria-label="Abrir la barra lateral (Ctrl+B)"
                        title="Abrir la barra lateral (Ctrl+B)"
                        className="hidden size-9 place-items-center rounded-lg text-tinta-300 hover:bg-tinta-800 hover:text-white focus-visible:grid md:group-hover/cabecera:grid"
                    >
                        <IconoBarra />
                    </button>
                )}
                <div className={`min-w-0 flex-1 leading-tight ${soloAncha}`}>
                    <p className="text-[0.9375rem] font-semibold text-white">MediAdmin</p>
                    <p className="truncate text-xs text-tinta-400">
                        {usuario?.is_platform_admin ? 'Plataforma' : usuario?.organization}
                    </p>
                </div>
                {!plegada && (
                    <button
                        type="button"
                        onClick={alternarPlegada}
                        aria-label="Cerrar la barra lateral (Ctrl+B)"
                        title="Cerrar la barra lateral (Ctrl+B)"
                        className="hidden size-8 shrink-0 place-items-center rounded-lg text-tinta-400 transition hover:bg-tinta-800 hover:text-white md:grid"
                    >
                        <IconoBarra />
                    </button>
                )}
                <button
                    type="button"
                    onClick={cerrarEnMovil}
                    aria-label="Cerrar el menú"
                    className="ml-auto grid size-9 shrink-0 place-items-center rounded-lg text-tinta-400 hover:bg-tinta-800 hover:text-white md:hidden"
                >
                    <IconoCerrar />
                </button>
            </div>

            {/* Opciones, agrupadas. Scroll vertical propio y nunca horizontal. */}
            <nav className="barra-scroll flex min-h-0 flex-1 flex-col gap-5 overflow-x-hidden overflow-y-auto px-3 pt-2 pb-4" aria-label="Menú principal">
                {grupos.map(({ seccion, opciones }) => (
                    <div key={seccion} role="group" aria-labelledby={`seccion-${seccion}`}>
                        <p
                            id={`seccion-${seccion}`}
                            className={['mb-1 px-2.5 text-xs font-medium text-tinta-500', plegada ? 'md:sr-only' : ''].join(' ')}
                        >
                            {seccion}
                        </p>
                        {plegada && <div className="mx-auto mb-1 hidden h-px w-6 bg-tinta-800 md:block" aria-hidden="true" />}
                        <ul className="flex flex-col gap-0.5">
                            {opciones.map((item) => (
                                <li key={item.ruta} className="relative">
                                    <NavLink
                                        to={item.ruta}
                                        onClick={cerrarEnMovil}
                                        onMouseEnter={mostrar(item.etiqueta)}
                                        onMouseLeave={ocultar}
                                        onFocus={mostrar(item.etiqueta)}
                                        onBlur={ocultar}
                                        aria-label={plegada ? item.etiqueta : undefined}
                                        className={({ isActive }) => [
                                            'relative flex h-9 items-center gap-3 rounded-lg px-2.5 text-sm transition-colors',
                                            plegada ? 'md:justify-center md:px-0' : '',
                                            isActive
                                                ? 'bg-marca-500/15 font-medium text-white'
                                                : 'text-tinta-400 hover:bg-tinta-800 hover:text-tinta-100',
                                        ].join(' ')}
                                    >
                                        {({ isActive }) => (
                                            <>
                                                {isActive && <span className="absolute inset-y-2 left-0 w-0.5 rounded-full bg-marca-400" aria-hidden="true" />}
                                                <span className={isActive ? 'text-marca-300' : ''}>
                                                    <IconoMenu tipo={item.icono} />
                                                </span>
                                                <span className={`whitespace-nowrap ${soloAncha}`}>{item.etiqueta}</span>
                                            </>
                                        )}
                                    </NavLink>
                                </li>
                            ))}
                        </ul>
                    </div>
                ))}
            </nav>

            {plegada && flotante && (
                <span
                    role="tooltip"
                    style={{ top: flotante.top }}
                    className="pointer-events-none fixed left-[4.75rem] z-50 hidden -translate-y-1/2 rounded-md bg-tinta-950 px-2.5 py-1.5 text-xs font-medium whitespace-nowrap text-white shadow-lg ring-1 ring-tinta-800 md:block"
                >
                    {flotante.texto}
                </span>
            )}

            {/* Quién está adentro, el tema y cómo salir. */}
            <div className={['relative flex shrink-0 items-center gap-2 border-t border-tinta-800 p-3', plegada ? 'md:flex-col' : ''].join(' ')}>
                <div className="grid size-9 shrink-0 place-items-center rounded-full bg-tinta-800 text-xs font-semibold text-marca-300" title={plegada ? `${nombre} · ${rol}` : undefined}>
                    {iniciales(nombre)}
                </div>
                <div className={`min-w-0 flex-1 leading-tight ${soloAncha}`}>
                    <p className="truncate text-sm font-medium text-white">{nombre}</p>
                    <p className="truncate text-xs text-tinta-400">{rol}</p>
                </div>
                <SelectorTema />
                <button
                    type="button"
                    onClick={cerrarSesion}
                    aria-label="Cerrar sesión"
                    title="Cerrar sesión"
                    className="grid size-9 shrink-0 place-items-center rounded-lg text-tinta-400 transition hover:bg-tinta-800 hover:text-white"
                >
                    <IconoSalir className="size-[18px]" />
                </button>
            </div>
        </aside>
    )
}


/**
 * Claro, oscuro o como el sistema: un botón con el ícono del tema elegido que
 * abre un menú chico hacia arriba. La elección la guarda src/tema/tema.ts.
 */
function SelectorTema() {
    const [tema, setTema] = useState<Tema>(leerTema)
    const [abierto, setAbierto] = useState(false)
    const caja = useRef<HTMLDivElement>(null)

    useEffect(() => {
        if (!abierto) return
        const fuera = (e: MouseEvent) => { if (!caja.current?.contains(e.target as Node)) setAbierto(false) }
        const escape = (e: KeyboardEvent) => { if (e.key === 'Escape') setAbierto(false) }
        window.addEventListener('mousedown', fuera)
        window.addEventListener('keydown', escape)
        return () => { window.removeEventListener('mousedown', fuera); window.removeEventListener('keydown', escape) }
    }, [abierto])

    const elegir = (nuevo: Tema) => { guardarTema(nuevo); setTema(nuevo); setAbierto(false) }
    const opciones: { valor: Tema; etiqueta: string }[] = [
        { valor: 'claro', etiqueta: 'Claro' },
        { valor: 'oscuro', etiqueta: 'Oscuro' },
        { valor: 'sistema', etiqueta: 'Como el sistema' },
    ]

    return (
        <div ref={caja} className="relative">
            <button
                type="button"
                onClick={() => setAbierto((a) => !a)}
                aria-label="Cambiar el tema"
                aria-haspopup="menu"
                aria-expanded={abierto}
                title="Tema"
                className="grid size-9 shrink-0 place-items-center rounded-lg text-tinta-400 transition hover:bg-tinta-800 hover:text-white"
            >
                <IconoTema tema={tema} />
            </button>
            {abierto && (
                <div role="menu" className="absolute bottom-full left-0 z-50 mb-2 w-48 rounded-xl bg-tinta-950 p-1 shadow-xl ring-1 ring-tinta-800">
                    {opciones.map((o) => (
                        <button
                            key={o.valor}
                            type="button"
                            role="menuitemradio"
                            aria-checked={tema === o.valor}
                            onClick={() => elegir(o.valor)}
                            className={['flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm',
                                tema === o.valor ? 'bg-tinta-800 text-white' : 'text-tinta-300 hover:bg-tinta-800 hover:text-white'].join(' ')}
                        >
                            <IconoTema tema={o.valor} />
                            <span className="flex-1">{o.etiqueta}</span>
                            {tema === o.valor && <span className="text-marca-300" aria-hidden="true">✓</span>}
                        </button>
                    ))}
                </div>
            )}
        </div>
    )
}


function IconoTema({ tema }: { tema: Tema }) {
    const comun = { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8,
        strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, className: 'size-[18px]', 'aria-hidden': true }
    if (tema === 'claro') return (
        <svg {...comun}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>
    )
    if (tema === 'oscuro') return (
        <svg {...comun}><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" /></svg>
    )
    return (
        <svg {...comun}><rect x="3" y="4" width="18" height="12" rx="2" /><path d="M8 20h8M12 16v4" /></svg>
    )
}


/** El ícono de la barra lateral: un panel con su columna izquierda. */
function IconoBarra() {
    return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" className="size-[18px]" aria-hidden="true">
            <rect x="3" y="4" width="18" height="16" rx="2.5" />
            <path d="M9.5 4v16" />
        </svg>
    )
}


function IconoCerrar() {
    return (
        <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            className="size-5"
            aria-hidden="true"
        >
            <path d="M6 6l12 12" />
            <path d="M18 6L6 18" />
        </svg>
    )
}


function IconoMenu({
                       tipo,
                   }: {
    tipo: ItemMenu['icono']
}) {
    if (
        tipo === 'panel'
    ) {
        return (
            <IconoPulso className="size-[18px]" />
        )
    }


    if (
        tipo === 'organizaciones'
    ) {
        return (
            <IconoEdificio className="size-[18px]" />
        )
    }


    if (
        tipo === 'roles'
    ) {
        return (
            <IconoEscudo className="size-[18px]" />
        )
    }


    if (
        tipo === 'usuarios'
    ) {
        return (
            <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                className="h-[18px] w-[18px]"
                aria-hidden="true"
            >
                <circle
                    cx="9"
                    cy="8"
                    r="3.2"
                />

                <path d="M3.5 19a5.5 5.5 0 0 1 11 0" />

                <path d="M16 6.2a3 3 0 0 1 0 5.6" />

                <path d="M17.5 14.2a5 5 0 0 1 3 4.8" />
            </svg>
        )
    }


    if (
        tipo === 'bitacora'
    ) {
        return (
            <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                className="h-[18px] w-[18px]"
                aria-hidden="true"
            >
                <path d="M5 4.5h11a2 2 0 0 1 2 2V20H7a2 2 0 0 1-2-2V4.5Z" />

                <path d="M5 4.5A1.5 1.5 0 0 1 6.5 3H18" />

                <path d="M9 9h6" />

                <path d="M9 13h4" />
            </svg>
        )
    }


    if (
        tipo === 'asistente'
    ) {
        return (
            <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinejoin="round"
                className="h-[18px] w-[18px]"
                aria-hidden="true"
            >
                <path d="M4 5h16v10H9l-5 4V5Z" />

                <path d="M8 9h8M8 12h5" />
            </svg>
        )
    }


    if (
        tipo === 'perfil'
    ) {
        return (
            <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                className="h-[18px] w-[18px]"
                aria-hidden="true"
            >
                <circle
                    cx="12"
                    cy="8"
                    r="3.5"
                />

                <path d="M5 20a7 7 0 0 1 14 0" />
            </svg>
        )
    }


    if (
        tipo === 'planes'
    ) {
        return (
            <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                className="h-[18px] w-[18px]"
                aria-hidden="true"
            >
                <path d="M4 7h16M4 12h10M4 17h7" />
                <circle
                    cx="18"
                    cy="15"
                    r="3"
                />
            </svg>
        )
    }



    const trazo = {
        viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8,
        strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const,
        className: 'h-[18px] w-[18px]', 'aria-hidden': true,
    }
    if (tipo === 'calendario') return (
        <svg {...trazo}><rect x="3.5" y="5" width="17" height="15" rx="2" /><path d="M3.5 10h17M8 3v4M16 3v4" /></svg>
    )
    if (tipo === 'reloj') return (
        <svg {...trazo}><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12l3 2" /></svg>
    )
    if (tipo === 'buscar') return (
        <svg {...trazo}><circle cx="11" cy="11" r="6.5" /><path d="m20 20-4.2-4.2" /></svg>
    )
    if (tipo === 'ficha') return (
        <svg {...trazo}><path d="M5 4h14v16l-3-2-2 2-2-2-2 2-2-2-3 2V4Z" /><path d="M9 9h6M9 13h4" /></svg>
    )
    if (tipo === 'estetoscopio') return (
        <svg {...trazo}><path d="M6 3v6a4 4 0 0 0 8 0V3" /><path d="M10 13v2a5 5 0 0 0 10 0v-1" /><circle cx="20" cy="12" r="2" /></svg>
    )
    if (tipo === 'servicio') return (
        <svg {...trazo}><path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3l-5-9V3" /><path d="M7.5 15h9" /></svg>
    )
    if (tipo === 'historia') return (
        <svg {...trazo}><path d="M7 4h10a2 2 0 0 1 2 2v14H5V6a2 2 0 0 1 2-2Z" /><path d="M9 3h6v3H9zM9 11h6M9 15h4" /></svg>
    )
    if (tipo === 'respaldo') return (
        <svg {...trazo}><path d="M7 18a4.5 4.5 0 1 1 .9-8.9A6 6 0 0 1 19 10.5a3.8 3.8 0 0 1-1 7.5H7Z" /><path d="M12 11v5M9.8 13.8 12 16l2.2-2.2" /></svg>
    )

    return (
        <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            className="h-[18px] w-[18px]"
            aria-hidden="true"
        >
            <rect
                x="3"
                y="5"
                width="18"
                height="14"
                rx="2"
            />

            <path d="M3 10h18" />

            <path d="M7 15h4" />
        </svg>
    )
}
