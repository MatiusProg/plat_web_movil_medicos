import {
    BrowserRouter,
    Navigate,
    Outlet,
    Route,
    Routes,
} from 'react-router-dom'

import { BarraPlataforma } from '@/componentes/BarraPlataforma'

import { InicioSesion } from '@/paginas/InicioSesion'
import { Panel } from '@/paginas/Panel'
import { Planes } from '@/paginas/Planes'
import { Suscripciones } from '@/paginas/Suscripciones'
import { HistorialSuscripcion } from '@/paginas/HistorialSuscripcion'

import { RutaProtegida } from '@/rutas/RutaProtegida'
import { ProveedorSesion } from '@/sesion/ContextoSesion'


function LayoutPlataforma() {
    return (
        <div className="flex min-h-dvh bg-slate-50">

            <BarraPlataforma />

            <main className="min-w-0 flex-1 overflow-x-hidden">
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

                    <Route
                        path="/ingresar"
                        element={
                            <InicioSesion />
                        }
                    />


                    <Route
                        element={
                            <Protegida>
                                <LayoutPlataforma />
                            </Protegida>
                        }
                    >

                        <Route
                            path="/panel"
                            element={
                                <Panel />
                            }
                        />

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