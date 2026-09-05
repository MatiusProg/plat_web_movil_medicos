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
]


export function BarraPlataforma() {
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


    return (
        <aside className="sticky top-0 flex h-dvh w-64 shrink-0 flex-col border-r border-tinta-800 bg-tinta-900 px-4 py-5">

            {/* Marca */}

            <div className="mb-8 flex items-center gap-3 px-2">

                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-marca-600 text-white shadow-lg shadow-marca-950/30">

                    <IconoEscudo className="size-6" />

                </div>


                <div className="leading-tight">

                    <h1 className="text-[17px] font-bold tracking-tight text-tinta-50">
                        MediAdmin
                    </h1>

                    <p className="mt-1 text-[10px] font-bold tracking-[0.18em] text-marca-400">
                        PLATAFORMA
                    </p>

                </div>

            </div>


            {/* Menú */}

            <div className="mb-3 px-3">

                <p className="text-[11px] font-semibold uppercase tracking-wider text-tinta-500">
                    Menú principal
                </p>

            </div>


            <nav className="flex flex-1 flex-col gap-1.5">

                {visibles.map((item) => (
                    <NavLink
                        key={item.ruta}
                        to={item.ruta}
                        className={({ isActive }) =>
                            [
                                'group relative flex items-center gap-3 rounded-xl px-3.5 py-3 text-sm font-medium transition-all duration-200',

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
                                        'flex h-8 w-8 items-center justify-center rounded-lg transition',

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


                                <span>
                  {item.etiqueta}
                </span>
                            </>
                        )}
                    </NavLink>
                ))}

            </nav>


            {/* Perfil */}

            <div className="mt-5 border-t border-tinta-800 pt-5">

                <button
                    type="button"
                    onClick={cerrarSesion}
                    className="mb-4 flex w-full items-center gap-3 rounded-xl px-3.5 py-3 text-sm font-medium text-tinta-400 transition hover:bg-red-950/40 hover:text-red-400"
                >
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg">

                        <IconoSalir className="size-[18px]" />

                    </div>

                    Cerrar sesión
                </button>


                <div className="rounded-2xl border border-tinta-800 bg-tinta-950/60 p-4">

                    <div className="flex items-center gap-3">

                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-marca-950 text-marca-400">

                            <IconoEscudo className="size-5" />

                        </div>


                        <div className="min-w-0">

                            <p className="truncate text-sm font-semibold text-tinta-100">
                                {usuario?.full_name
                                    || 'Superadministrador'}
                            </p>

                            <p className="mt-0.5 text-xs text-tinta-500">
                                {usuario?.is_platform_admin
                                    ? 'Administrador de plataforma'
                                    : usuario?.organization
                                    || 'Usuario'}
                            </p>

                        </div>

                    </div>


                    <div className="mt-3 flex items-center gap-2 border-t border-tinta-800 pt-3">

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