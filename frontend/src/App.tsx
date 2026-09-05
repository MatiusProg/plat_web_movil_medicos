import {
    BrowserRouter,
    Navigate,
    Outlet,
    Route,
    Routes,
} from 'react-router-dom'

import { BarraPlataforma } from '@/componentes/BarraPlataforma'

import { AltaOrganizacion } from '@/paginas/AltaOrganizacion'
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


function LayoutPlataforma() {
    return (
        <div className="flex min-h-dvh bg-tinta-950">

            <BarraPlataforma />

            <main className="min-w-0 flex-1 overflow-x-hidden bg-tinta-950">
                <Outlet />
            </main>

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
                                <Planes />
                            }
                        />

                        <Route
                            path="/suscripciones"
                            element={
                                <Suscripciones />
                            }
                        />

                        <Route
                            path="/suscripciones/:organizationId/historial"
                            element={
                                <HistorialSuscripcion />
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