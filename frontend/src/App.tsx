import {
    BrowserRouter,
    Navigate,
    Outlet,
    Route,
    Routes,
} from 'react-router-dom'

import { BarraPlataforma } from '@/componentes/BarraPlataforma'

import { Agendas } from '@/paginas/Agendas'
import { AltaOrganizacion } from '@/paginas/AltaOrganizacion'
import { Bitacora } from '@/paginas/Bitacora'
import { BloqueosAgenda } from '@/paginas/BloqueosAgenda'
import { BuscarProfesionales } from '@/paginas/BuscarProfesionales'
import { Disponibilidad } from '@/paginas/Disponibilidad'
import { InicioSesion } from '@/paginas/InicioSesion'
import { Organizaciones } from '@/paginas/Organizaciones'
import { RegistroPaciente } from '@/paginas/RegistroPaciente'
import { Panel } from '@/paginas/Panel'
import { Planes } from '@/paginas/Planes'
import { RecuperarAcceso } from '@/paginas/RecuperarAcceso'
import { RestablecerContrasena } from '@/paginas/RestablecerContrasena'
import { Roles } from '@/paginas/Roles'
import { Suscripciones } from '@/paginas/Suscripciones'
import { Usuarios } from '@/paginas/Usuarios'
import { HistorialSuscripcion } from '@/paginas/HistorialSuscripcion'

import { RutaProtegida } from '@/rutas/RutaProtegida'
import { ProveedorSesion } from '@/sesion/ContextoSesion'


/**
 * El armazón de las pantallas con sesión: barra lateral fija y área de
 * contenido.
 *
 * **El área de contenido tiene que seguir al tema, no imponerlo.** Todas las
 * pantallas están escritas en claro con variantes `dark:` —`text-tinta-900
 * dark:text-tinta-50`, `bg-white dark:bg-tinta-900/50`— y esas variantes las
 * activa `prefers-color-scheme`, como declara `index.css`. Cuando acá se fijaba
 * `bg-tinta-950` a secas, en un equipo en modo claro quedaba un fondo casi
 * negro debajo de textos casi negros: se perdía todo salvo lo que estuviera
 * dentro de una tarjeta blanca. `Panel` era la única pantalla que se salvaba,
 * porque se pinta su propio fondo.
 *
 * En una aplicación médica eso no es un detalle estético: la pantalla la lee
 * alguien apurado, en el monitor que le tocó.
 *
 * La barra lateral sí queda oscura siempre, y es a propósito: es el patrón
 * habitual de un panel de administración —navegación oscura, contenido claro—
 * y sus colores están elegidos para ese fondo.
 */
function LayoutPlataforma() {
    return (
        <div className="flex min-h-dvh bg-tinta-50 dark:bg-tinta-950">

            <BarraPlataforma />

            <main className="min-w-0 flex-1 overflow-x-hidden bg-tinta-50 dark:bg-tinta-950">
                <Outlet />
            </main>

        </div>
    )
}


/**
 * Lienzo oscuro para las tres pantallas de plataforma.
 *
 * `Planes`, `Suscripciones` e `HistorialSuscripcion` están escritas **sólo en
 * oscuro**: sus tarjetas usan `bg-tinta-900` y su texto `text-tinta-100`, sin
 * variantes claras. El resto de la aplicación está escrita al revés, en claro
 * con variantes `dark:`.
 *
 * Mientras el layout imponía fondo oscuro a todo, esas tres se veían bien y las
 * demás no. Al hacer que el área de contenido siga al tema, la cuenta se
 * invierte: por eso estas tres se llevan su propio fondo, igual que `Panel` se
 * lleva el suyo claro.
 *
 * **Esto es un parche, no el diseño.** Lo correcto es escribir esas tres como
 * las demás —claro con `dark:`—, pero son de US-44 y US-45 y no son de esta
 * historia. Cuando alguien las ponga en línea, este envoltorio se borra y las
 * rutas quedan como las otras.
 */
function PantallaDePlataforma({
                                  children,
                              }: {
    children: React.ReactNode
}) {
    return (
        <div className="min-h-dvh bg-tinta-950 text-tinta-100">
            {children}
        </div>
    )
}


function Protegida({
                       children,
                   }: {
    children: React.ReactNode
}) {
    return (
        <RutaProtegida>
            {children}
        </RutaProtegida>
    )
}


export default function App() {
    return (
        <ProveedorSesion>

            <BrowserRouter>

                <Routes>

                    {/* US-02: inicio de sesión */}

                    <Route
                        path="/ingresar"
                        element={
                            <InicioSesion />
                        }
                    />


                    {/* US-03: recuperación de contraseña.

                        Las dos son públicas a propósito: quien las usa es
                        justamente alguien que no puede iniciar sesión. */}

                    <Route
                        path="/recuperar"
                        element={
                            <RecuperarAcceso />
                        }
                    />

                    <Route
                        path="/restablecer"
                        element={
                            <RestablecerContrasena />
                        }
                    />


                    {/* US-01: registro de paciente */}

                    <Route
                        path="/registro"
                        element={
                            <RegistroPaciente />
                        }
                    />


                    {/* Área administrativa */}

                    <Route
                        element={
                            <Protegida>
                                <LayoutPlataforma />
                            </Protegida>
                        }
                    >

                        {/* Panel */}

                        <Route
                            path="/panel"
                            element={
                                <Panel />
                            }
                        />


                        {/* GES-43: organizaciones */}

                        <Route
                            path="/organizaciones"
                            element={
                                <Organizaciones />
                            }
                        />

                        <Route
                            path="/organizaciones/nueva"
                            element={
                                <AltaOrganizacion />
                            }
                        />


                        {/* GES-44: planes y suscripciones */}

                        <Route
                            path="/planes"
                            element={
                                <PantallaDePlataforma>
                                    <Planes />
                                </PantallaDePlataforma>
                            }
                        />

                        <Route
                            path="/suscripciones"
                            element={
                                <PantallaDePlataforma>
                                    <Suscripciones />
                                </PantallaDePlataforma>
                            }
                        />

                        <Route
                            path="/suscripciones/:organizationId/historial"
                            element={
                                <PantallaDePlataforma>
                                    <HistorialSuscripcion />
                                </PantallaDePlataforma>
                            }
                        />


                        {/* US-04: roles, permisos y asignación */}

                        <Route
                            path="/roles"
                            element={
                                <Roles />
                            }
                        />

                        <Route
                            path="/usuarios"
                            element={
                                <Usuarios />
                            }
                        />


                        {/* US-06: bitácora de auditoría */}

                        <Route
                            path="/bitacora"
                            element={
                                <Bitacora />
                            }
                        />


                        {/* US-13 / US-14: agendas médicas y bloqueos */}

                        <Route
                            path="/agendas"
                            element={
                                <Agendas />
                            }
                        />

                        <Route
                            path="/agendas/bloqueos"
                            element={
                                <BloqueosAgenda />
                            }
                        />


                        {/* US-15: disponibilidad consolidada */}

                        <Route
                            path="/disponibilidad"
                            element={
                                <Disponibilidad />
                            }
                        />


                        {/* US-16: búsqueda de profesionales */}

                        <Route
                            path="/buscar-profesionales"
                            element={
                                <BuscarProfesionales />
                            }
                        />

                    </Route>


                    <Route
                        path="/"
                        element={
                            <Navigate
                                to="/panel"
                                replace
                            />
                        }
                    />

                    <Route
                        path="*"
                        element={
                            <Navigate
                                to="/panel"
                                replace
                            />
                        }
                    />

                </Routes>

            </BrowserRouter>

        </ProveedorSesion>
    )
}