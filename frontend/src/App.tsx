import {
    BrowserRouter,
    Navigate,
    Route,
    Routes,
} from 'react-router-dom'

import { ArmazonPlataforma } from '@/componentes/ArmazonPlataforma'

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
import { Especialidades } from '@/paginas/Especialidades'
import { Profesionales } from '@/paginas/Profesionales'
import { Usuarios } from '@/paginas/Usuarios'
import { Sucursales } from '@/paginas/Sucursales'
import { HistorialSuscripcion } from '@/paginas/HistorialSuscripcion'

import { RutaProtegida } from '@/rutas/RutaProtegida'
import { ProveedorSesion } from '@/sesion/ContextoSesion'


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
                                <ArmazonPlataforma />
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


                        {/* US-06: bitácora de auditoría */}

                        <Route
                            path="/bitacora"
                            element={
                                <Bitacora />
                            }
                        />


                        {/* US-11: gestión de sucursales */}
                        <Route path="/sucursales" element={<Sucursales />} />

                        {/* US-13 / US-14: agendas médicas y bloqueos */}

                        {/* US-12: administracion del catalogo medico */}
                        <Route path="/especialidades" element={<Especialidades />} />
                        <Route path="/profesionales" element={<Profesionales />} />

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