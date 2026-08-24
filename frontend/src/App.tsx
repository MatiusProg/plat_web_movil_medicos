import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { InicioSesion } from '@/paginas/InicioSesion'
import { RegistroPaciente } from '@/paginas/RegistroPaciente'
import { Panel } from '@/paginas/Panel'
import { RutaProtegida } from '@/rutas/RutaProtegida'
import { ProveedorSesion } from '@/sesion/ContextoSesion'

/**
 * Las rutas de la aplicación web.
 *
 * En el Sprint 0 son dos: la de entrar y la de después de entrar. Cada
 * historia de los sprints siguientes agrega la suya acá adentro de
 * `<RutaProtegida>`.
 */
export default function App() {
  return (
    <ProveedorSesion>
      <BrowserRouter>
        <Routes>
          <Route path="/ingresar" element={<InicioSesion />} />
          <Route path="/registro" element={<RegistroPaciente />} />
          <Route
            path="/panel"
            element={
              <RutaProtegida>
                <Panel />
              </RutaProtegida>
            }
          />
          {/* Cualquier otra ruta cae en el panel, que a su vez manda al login
              si no hay sesión. Así una URL vieja o mal escrita nunca deja una
              pantalla en blanco. */}
          <Route path="*" element={<Navigate to="/panel" replace />} />
        </Routes>
      </BrowserRouter>
    </ProveedorSesion>
  )
}
