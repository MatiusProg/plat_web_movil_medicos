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
import { Suscripciones } from '@/paginas/Suscripciones'
import { HistorialSuscripcion } from '@/paginas/HistorialSuscripcion'

import { RutaProtegida } from '@/rutas/RutaProtegida'
import { ProveedorSesion } from '@/sesion/ContextoSesion'


/**
 * Layout principal de administración de plataforma.
 *
 * Las páginas protegidas comparten la barra lateral.
 */
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


/**
 * Rutas de la aplicación web.
 *
 * Cada historia mantiene su bloque separado para reducir
 * conflictos al integrar cambios entre ramas.
 */
export default function App() {
  return (
    <ProveedorSesion>

      <BrowserRouter>

        <Routes>

          {/* ---------- US-02: inicio de sesión ---------- */}

          <Route
            path="/ingresar"
            element={
              <InicioSesion />
            }
          />


          {/* ---------- US-01: registro de paciente ---------- */}

          <Route
            path="/registro"
            element={
              <RegistroPaciente />
            }
          />


          {/* ---------- Rutas administrativas protegidas ---------- */}

          <Route
            element={
              <Protegida>
                <LayoutPlataforma />
              </Protegida>
            }
          >

            {/* ---------- Panel ---------- */}

            <Route
              path="/panel"
              element={
                <Panel />
              }
            />


            {/* ---------- GES-43: organizaciones ---------- */}

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


            {/* ---------- GES-44: planes y suscripciones ---------- */}

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


          {/* ---------- Redirecciones ---------- */}

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