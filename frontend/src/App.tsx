import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AltaOrganizacion } from '@/paginas/AltaOrganizacion'
import { InicioSesion } from '@/paginas/InicioSesion'
import { Organizaciones } from '@/paginas/Organizaciones'
import { RegistroPaciente } from '@/paginas/RegistroPaciente'
import { Panel } from '@/paginas/Panel'
import { RutaProtegida } from '@/rutas/RutaProtegida'
import { ProveedorSesion } from '@/sesion/ContextoSesion'

/**
 * Las rutas de la aplicación web.
 *
 * Están agrupadas por historia y con un bloque de comentario cada una: es el
 * único archivo del frontend que todas comparten, así que conviene que cada
 * una toque su bloque y no la línea de al lado. Es la misma regla que
 * `urls.py` en el backend.
 */
export default function App() {
  return (
    <ProveedorSesion>
      <BrowserRouter>
        <Routes>
          {/* ---------- US-02 (Karen): sesión ---------- */}
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

          {/* ---------- US-43 (Luis Mateo): organizaciones ---------- */}
          <Route
            path="/organizaciones"
            element={
              <RutaProtegida>
                <Organizaciones />
              </RutaProtegida>
            }
          />
          <Route
            path="/organizaciones/nueva"
            element={
              <RutaProtegida>
                <AltaOrganizacion />
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
