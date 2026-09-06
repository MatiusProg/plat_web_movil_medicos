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

import { NavLink, useNavigate } from 'react-router-dom'

import {
    IconoEdificio,
    IconoEscudo,
    IconoPulso,
    IconoSalir,
} from '@/componentes/iconos'

import { useSesion } from '@/sesion/useSesion'


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
    /**
     * Quién ve la entrada.
     *
     * `'plataforma'` es del Superadministrador y se decide por
     * `is_platform_admin`, no por permisos: su lista de permisos llega vacía
     * porque `user_roles` está protegida por RLS y sus filas irían con
     * `organization_id` NULL. Cualquier otro valor es un código de permiso y
     * se consulta con `puede`. Sin `requiere`, la entrada la ve todo el mundo.
     *
     * Esconder una entrada no autoriza nada: la puerta real la pone el
     * backend en cada endpoint.
     */
    requiere?: 'plataforma' | string
}


const items: ItemMenu[] = [
    {
        etiqueta: 'Panel',
        ruta: '/panel',
        icono: 'panel',
    },
    {
        etiqueta: 'Organizaciones',
        ruta: '/organizaciones',
        icono: 'organizaciones',
        requiere: 'plataforma',
    },
    {
        etiqueta: 'Planes',
        ruta: '/planes',
        icono: 'planes',
        requiere: 'plataforma',
    },
    {
        etiqueta: 'Suscripciones',
        ruta: '/suscripciones',
        icono: 'suscripciones',
        requiere: 'plataforma',
    },

    // US-04 — administración de la organización.
    {
        etiqueta: 'Roles y permisos',
        ruta: '/roles',
        icono: 'roles',
        requiere: 'users.role.read',
    },
    {
        etiqueta: 'Usuarios',
        ruta: '/usuarios',
        icono: 'usuarios',
        requiere: 'users.user.read',
    },

    // US-06 — bitácora de auditoría.
    {
        etiqueta: 'Bitácora',
        ruta: '/bitacora',
        icono: 'bitacora',
        requiere: 'audit.log.read',
    },

    // US-13 a US-16 — agendas y catálogo.
    {
        etiqueta: 'Agendas',
        ruta: '/agendas',
        icono: 'agendas',
        requiere: 'scheduling.schedule.read',
    },
    {
        etiqueta: 'Disponibilidad',
        ruta: '/disponibilidad',
        icono: 'agendas',
        requiere: 'scheduling.slot.read',
    },
    {
        etiqueta: 'Buscar profesionales',
        ruta: '/buscar-profesionales',
        icono: 'catalogo',
        requiere: 'catalog.professional.read',
    },
]


interface Props {
    /** Sólo a partir de `md`: en móvil la barra es un cajón, no una franja. */
    plegada: boolean
    alternarPlegada: () => void
    abiertaEnMovil: boolean
    cerrarEnMovil: () => void
}


export function BarraPlataforma({
                                    plegada,
                                    alternarPlegada,
                                    abiertaEnMovil,
                                    cerrarEnMovil,
                                }: Props) {
    const {
        usuario,
        salir,
        puede,
    } = useSesion()

    const navigate =
        useNavigate()


    const visibles =
        items.filter((item) => {
            if (!item.requiere) return true

            if (item.requiere === 'plataforma') {
                return Boolean(
                    usuario?.is_platform_admin,
                )
            }

            return puede(item.requiere)
        })


    const cerrarSesion =
        async () => {
            await salir()
            navigate('/ingresar')
        }


    // Plegada sólo aplica de `md` para arriba. Dentro del cajón de móvil las
    // etiquetas se ven siempre: ahí sobra el ancho.
    const soloAncha =
        plegada ? 'md:hidden' : ''


    return (
        <aside
            className={[
                'fixed inset-y-0 left-0 z-40 flex h-dvh flex-col border-r border-tinta-800 bg-tinta-900',
                'transition-[width,transform] duration-200 ease-out',

                // Ancho: en móvil siempre cómoda; en escritorio, según se pliegue.
                'w-64',
                plegada ? 'md:w-[4.5rem]' : 'md:w-64',

                // En móvil entra y sale; de `md` en adelante está siempre puesta.
                abiertaEnMovil ? 'translate-x-0' : '-translate-x-full',
                'md:translate-x-0',
            ].join(' ')}
        >

            {/* Marca */}

            <div className="flex shrink-0 items-center gap-3 px-4 py-5">

                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-marca-600 text-white shadow-lg shadow-marca-950/30">

                    <IconoEscudo className="size-6" />

                </div>


                <div className={`leading-tight ${soloAncha}`}>

                    <h1 className="text-[17px] font-bold tracking-tight text-tinta-50">
                        MediAdmin
                    </h1>

                    <p className="mt-1 text-[10px] font-bold tracking-[0.18em] text-marca-400">
                        PLATAFORMA
                    </p>

                </div>


                {/* Cerrar el cajón. Sólo en móvil: en escritorio no hay cajón. */}

                <button
                    type="button"
                    onClick={cerrarEnMovil}
                    aria-label="Cerrar el menú"
                    className="ml-auto grid size-9 shrink-0 place-items-center rounded-xl text-tinta-400 transition hover:bg-tinta-800 hover:text-tinta-100 md:hidden"
                >
                    <IconoCerrar />
                </button>

            </div>


            {/* Menú */}

            <div className={`mb-3 px-7 ${soloAncha}`}>

                <p className="text-[11px] font-semibold uppercase tracking-wider text-tinta-500">
                    Menú principal
                </p>

            </div>


            {/* `flex-1` con `overflow-y-auto`: las opciones scrollean acá dentro
                en vez de empujar el perfil fuera de la pantalla. */}

            <nav className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto px-4 pb-2">

                {visibles.map((item) => (
                    <NavLink
                        key={item.ruta}
                        to={item.ruta}
                        title={plegada ? item.etiqueta : undefined}
                        className={({ isActive }) =>
                            [
                                'group relative flex shrink-0 items-center gap-3 rounded-xl px-3.5 py-3 text-sm font-medium transition-all duration-200',

                                isActive
                                    ? 'bg-marca-950 text-marca-300'
                                    : 'text-tinta-400 hover:bg-tinta-800 hover:text-tinta-100',
                            ].join(' ')
                        }
                    >
                        {({ isActive }) => (
                            <>
                                {isActive && (
                                    <span className="absolute left-0 h-6 w-1 rounded-r-full bg-marca-500" />
                                )}


                                <div
                                    className={[
                                        'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition',

                                        isActive
                                            ? 'bg-marca-900 text-marca-300'
                                            : 'text-tinta-500 group-hover:bg-tinta-700 group-hover:text-tinta-200',
                                    ].join(' ')}
                                >
                                    <IconoMenu
                                        tipo={
                                            item.icono
                                        }
                                    />
                                </div>


                                <span className={`truncate ${soloAncha}`}>
                                    {item.etiqueta}
                                </span>
                            </>
                        )}
                    </NavLink>
                ))}

            </nav>


            {/* Plegar. Sólo en escritorio, que es donde plegar significa algo. */}

            <button
                type="button"
                onClick={alternarPlegada}
                aria-label={plegada ? 'Desplegar el menú' : 'Plegar el menú'}
                title={plegada ? 'Desplegar el menú' : 'Plegar el menú'}
                className="mx-4 hidden shrink-0 items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium text-tinta-500 transition hover:bg-tinta-800 hover:text-tinta-200 md:flex"
            >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center">
                    <IconoPlegar plegada={plegada} />
                </div>

                <span className={soloAncha}>
                    Plegar
                </span>
            </button>


            {/* Perfil. `shrink-0` para que quede anclado abajo pase lo que pase. */}

            <div className="mt-3 shrink-0 border-t border-tinta-800 px-4 pt-4 pb-5">

                <button
                    type="button"
                    onClick={cerrarSesion}
                    title={plegada ? 'Cerrar sesión' : undefined}
                    className="mb-3 flex w-full items-center gap-3 rounded-xl px-3.5 py-3 text-sm font-medium text-tinta-400 transition hover:bg-red-950/40 hover:text-red-400"
                >
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg">

                        <IconoSalir className="size-[18px]" />

                    </div>

                    <span className={soloAncha}>
                        Cerrar sesión
                    </span>
                </button>


                <div
                    className={[
                        'rounded-2xl border border-tinta-800 bg-tinta-950/60',
                        plegada ? 'p-4 md:p-2' : 'p-4',
                    ].join(' ')}
                >

                    <div className="flex items-center gap-3">

                        <div
                            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-marca-950 text-marca-400"
                            title={plegada ? (usuario?.full_name ?? '') : undefined}
                        >

                            <IconoEscudo className="size-5" />

                        </div>


                        <div className={`min-w-0 ${soloAncha}`}>

                            <p className="truncate text-sm font-semibold text-tinta-100">
                                {usuario?.full_name
                                    || 'Superadministrador'}
                            </p>

                            <p className="mt-0.5 truncate text-xs text-tinta-500">
                                {usuario?.is_platform_admin
                                    ? 'Administrador de plataforma'
                                    : usuario?.organization
                                    || 'Usuario'}
                            </p>

                        </div>

                    </div>


                    <div className={`mt-3 flex items-center gap-2 border-t border-tinta-800 pt-3 ${soloAncha}`}>

                        <span className="h-2 w-2 rounded-full bg-emerald-500" />

                        <span className="text-xs font-medium text-emerald-400">
                            Cuenta activa
                        </span>

                    </div>

                </div>

            </div>

        </aside>
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


function IconoPlegar({
                         plegada,
                     }: {
    plegada: boolean
}) {
    return (
        <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-[18px] w-[18px]"
            aria-hidden="true"
        >
            {plegada
                ? <path d="M9 6l6 6-6 6" />
                : <path d="M15 6l-6 6 6 6" />}
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
