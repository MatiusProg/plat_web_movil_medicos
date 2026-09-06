/**
 * El armazón de las pantallas con sesión: barra lateral y área de contenido.
 *
 * Vive acá y no en `App.tsx` porque tiene estado —plegada, abierta en móvil— y
 * `App.tsx` es el archivo que más historias tocan: cuanto menos haya ahí, menos
 * conflictos.
 *
 * **Tres problemas resuelve, y conviene no perderlos de vista al tocarlo:**
 *
 * 1. *La barra no tenía scroll propio.* Con `h-dvh` y sin `overflow`, cada
 *    opción nueva empujaba el bloque de perfil hacia abajo hasta sacarlo de la
 *    pantalla. Un administrador con todos los permisos ya no llegaba a ver su
 *    propio botón de cerrar sesión. Ahora scrollea la lista de opciones y el
 *    perfil queda anclado abajo.
 *
 * 2. *En móvil ocupaba 16rem de un ancho de 20.* Ahora está fuera de pantalla y
 *    se abre como cajón sobre el contenido, con fondo oscuro detrás y cierre con
 *    Escape, tocando fuera, o al navegar a otra pantalla.
 *
 * 3. *No se podía plegar en escritorio.* Se pliega a una franja de iconos, y la
 *    preferencia se recuerda entre sesiones.
 *
 * **La barra es `fixed`, no un elemento en el flujo.** Por eso el contenido se
 * corre con `padding-left` en vez de que un `flex` lo empuje: con `fixed`, la
 * misma barra sirve de cajón en móvil sin dejar un hueco de 16rem cuando está
 * cerrada.
 */

import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'

import { BarraPlataforma } from '@/componentes/BarraPlataforma'


const CLAVE_PREFERENCIA = 'barra-plegada'


/**
 * Leer y escribir `localStorage` va envuelto porque **puede lanzar**, no sólo
 * devolver vacío: en una ventana privada o con las cookies de sitio bloqueadas,
 * el acceso tira una excepción. Sin el `try`, la aplicación no arranca.
 */
function leerPreferencia(): boolean {
    try {
        return window.localStorage.getItem(CLAVE_PREFERENCIA) === 'si'
    } catch {
        return false
    }
}


function guardarPreferencia(plegada: boolean) {
    try {
        window.localStorage.setItem(CLAVE_PREFERENCIA, plegada ? 'si' : 'no')
    } catch {
        // Que no se recuerde la preferencia no es motivo para romper nada.
    }
}


export function ArmazonPlataforma() {
    const [plegada, setPlegada] =
        useState(leerPreferencia)

    const [abiertaEnMovil, setAbiertaEnMovil] =
        useState(false)

    const { pathname } =
        useLocation()


    useEffect(() => {
        guardarPreferencia(plegada)
    }, [plegada])


    // Al navegar, el cajón se cierra. Sin esto, en móvil se elige una opción y
    // el cajón queda tapando la pantalla a la que se acaba de llegar.
    useEffect(() => {
        setAbiertaEnMovil(false)
    }, [pathname])


    // Escape cierra el cajón. Es lo que espera cualquiera que use teclado, y
    // cuesta cuatro líneas.
    useEffect(() => {
        if (!abiertaEnMovil) return

        const alPresionar = (evento: KeyboardEvent) => {
            if (evento.key === 'Escape') setAbiertaEnMovil(false)
        }

        window.addEventListener('keydown', alPresionar)
        return () => window.removeEventListener('keydown', alPresionar)
    }, [abiertaEnMovil])


    return (
        <div className="min-h-dvh bg-tinta-50 dark:bg-tinta-950">

            <BarraPlataforma
                plegada={plegada}
                alternarPlegada={() => setPlegada((previa) => !previa)}
                abiertaEnMovil={abiertaEnMovil}
                cerrarEnMovil={() => setAbiertaEnMovil(false)}
            />


            {/* Fondo del cajón. Sólo en móvil y sólo con el cajón abierto. */}

            {abiertaEnMovil && (
                <div
                    className="fixed inset-0 z-30 bg-black/50 md:hidden"
                    onClick={() => setAbiertaEnMovil(false)}
                    aria-hidden="true"
                />
            )}


            <div
                className={[
                    'flex min-h-dvh flex-col transition-[padding] duration-200',

                    // El desplazamiento sólo existe a partir de `md`: en móvil
                    // la barra flota sobre el contenido y no le quita ancho.
                    plegada
                        ? 'md:pl-[4.5rem]'
                        : 'md:pl-64',
                ].join(' ')}
            >

                {/* Barra superior de móvil: es lo único que abre el cajón. */}

                <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-3 border-b border-tinta-200 bg-tinta-50/90 px-4 backdrop-blur md:hidden dark:border-tinta-800 dark:bg-tinta-950/90">

                    <button
                        type="button"
                        onClick={() => setAbiertaEnMovil(true)}
                        aria-label="Abrir el menú"
                        aria-expanded={abiertaEnMovil}
                        className="text-tinta-600 hover:bg-tinta-200 dark:text-tinta-300 dark:hover:bg-tinta-800 -ml-1 grid size-10 place-items-center rounded-xl transition"
                    >
                        <IconoHamburguesa />
                    </button>

                    <span className="text-tinta-800 dark:text-tinta-100 text-[0.9375rem] font-semibold">
                        MediAdmin
                    </span>

                </header>


                <main className="min-w-0 flex-1 overflow-x-hidden">
                    <Outlet />
                </main>

            </div>

        </div>
    )
}


function IconoHamburguesa() {
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
            <path d="M4 7h16" />
            <path d="M4 12h16" />
            <path d="M4 17h16" />
        </svg>
    )
}
