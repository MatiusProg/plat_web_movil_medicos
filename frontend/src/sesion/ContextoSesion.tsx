/**
 * El estado de la sesión, disponible para toda la aplicación.
 *
 * Se resuelven acá tres cosas que si se dejan en las pantallas terminan mal:
 *
 * 1. **El refresco automático.** Un temporizador renueva el acceso poco antes
 *    de que expire. Sin esto, a los 30 minutos la aplicación empieza a
 *    responder 401 en medio de cualquier trámite.
 * 2. **La rotación.** El backend invalida el refresco en cada uso, así que hay
 *    que guardar SIEMPRE los dos valores que devuelve. Guardar sólo el `access`
 *    deja la sesión sin poder renovarse nunca más.
 * 3. **La sincronización entre pestañas.** Si cerrás sesión en una, las otras
 *    tienen que enterarse; si no, siguen mostrando datos con un token muerto.
 */

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'

import { cerrarSesion as pedirCierre, iniciarSesion, renovarSesion, verUsuarioActual } from '@/api/autenticacion'
import type { Credenciales } from '@/api/autenticacion'
import {
  borrarSesion,
  CLAVE_SESION,
  guardarOrganizacion,
  guardarSesion,
  leerSesion,
  type SesionGuardada,
} from './almacenamiento'
import { ContextoSesion, type EstadoSesion } from './contexto'

/**
 * Cuánto antes de que expire el acceso se lo renueva.
 *
 * El backend lo emite con 30 minutos (`ACCESS_TOKEN_LIFETIME`). Se renueva 5
 * minutos antes para dejar margen: si el reloj del navegador está corrido unos
 * minutos respecto del servidor —pasa más de lo que uno cree—, renovar justo
 * sobre la hora produce un 401 intermitente imposible de reproducir.
 */
const MINUTOS_DE_MARGEN = 5

/**
 * Milisegundos hasta renovar, según el vencimiento (`exp`) del propio token.
 *
 * Contar 25 minutos desde que se abre la aplicación fallaba al volver con la
 * sesión guardada: si el acceso ya había vencido (la pestaña cerrada media
 * hora o hasta el día siguiente), todo respondía «Given token not valid for any
 * token type» durante 25 minutos. Con el vencimiento real, un acceso vencido se
 * renueva enseguida. Si el token no se puede leer, se renueva enseguida también.
 */
function msHastaRenovar(access: string): number {
  try {
    const carga = JSON.parse(atob(access.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    return Math.max(0, carga.exp * 1000 - Date.now() - MINUTOS_DE_MARGEN * 60_000)
  } catch {
    return 0
  }
}

export function ProveedorSesion({ children }: { children: ReactNode }) {
  // Se lee en el primer render y no en un efecto: `localStorage` es síncrono,
  // así que no hay ningún momento en que la sesión "todavía no se sabe". Con un
  // efecto haría falta un estado de carga, y cada recarga mostraría un
  // parpadeo antes de decidir.
  const [sesion, setSesion] = useState<SesionGuardada | null>(leerSesion)
  const temporizador = useRef<number | null>(null)

  const olvidar = useCallback(() => {
    if (temporizador.current !== null) {
      window.clearTimeout(temporizador.current)
      temporizador.current = null
    }
    borrarSesion()
    setSesion(null)
  }, [])

  const persistir = useCallback((nueva: SesionGuardada) => {
    guardarSesion(nueva)
    setSesion(nueva)
  }, [])

  // ---- Renovación programada ---------------------------------------------
  useEffect(() => {
    if (!sesion) return

    let vigente = true

    const renovar = async () => {
      try {
        const par = await renovarSesion(sesion.refresh)
        if (!vigente) return
        // Los DOS valores: el backend rota, y el refresco viejo ya no sirve.
        // Y el usuario de ahora: los permisos pudieron cambiar desde el login.
        // Si esa lectura falla, se sigue con el que había.
        const usuario = await verUsuarioActual(par.access).catch(() => sesion.usuario)
        if (!vigente) return
        persistir({ access: par.access, refresh: par.refresh, usuario })
      } catch {
        // El refresco venció o fue a la lista negra. No hay nada que
        // reintentar: hay que volver a iniciar sesión.
        if (vigente) olvidar()
      }
    }

    temporizador.current = window.setTimeout(renovar, msHastaRenovar(sesion.access))

    return () => {
      vigente = false
      if (temporizador.current !== null) {
        window.clearTimeout(temporizador.current)
        temporizador.current = null
      }
    }
  }, [sesion, persistir, olvidar])

  // ---- Sincronización entre pestañas -------------------------------------
  useEffect(() => {
    const alCambiar = (evento: StorageEvent) => {
      if (evento.key !== CLAVE_SESION) return
      setSesion(leerSesion())
    }
    window.addEventListener('storage', alCambiar)
    return () => window.removeEventListener('storage', alCambiar)
  }, [])

  const entrar = useCallback(
    async (credenciales: Credenciales, senal?: AbortSignal) => {
      const datos = await iniciarSesion(credenciales, senal)
      persistir({ access: datos.access, refresh: datos.refresh, usuario: datos.user })
      guardarOrganizacion(credenciales.organizacion)
      return datos.user
    },
    [persistir],
  )

  const salir = useCallback(async () => {
    const actual = sesion
    // Se limpia primero y se avisa después: si el servidor no responde, la
    // sesión tiene que quedar cerrada en este navegador de todas formas.
    olvidar()
    if (!actual) return
    try {
      await pedirCierre(actual.refresh, actual.access)
    } catch {
      // El token expira solo. Nada que informarle a quien ya se fue.
    }
  }, [sesion, olvidar])

  const actualizar = useCallback<EstadoSesion['actualizar']>((cambios) => {
    setSesion((previa) => {
      if (!previa) return previa
      const nueva: SesionGuardada = {
        access: cambios.access ?? previa.access,
        refresh: cambios.refresh ?? previa.refresh,
        usuario: { ...previa.usuario, ...cambios.usuario },
      }
      guardarSesion(nueva)
      return nueva
    })
  }, [])

  const puede = useCallback(
    (permiso: string) => sesion?.usuario.permissions.includes(permiso) ?? false,
    [sesion],
  )

  const valor = useMemo<EstadoSesion>(
    () => ({
      usuario: sesion?.usuario ?? null,
      token: sesion?.access ?? null,
      entrar,
      salir,
      puede,
      actualizar,
    }),
    [sesion, entrar, salir, puede, actualizar],
  )

  return <ContextoSesion.Provider value={valor}>{children}</ContextoSesion.Provider>
}
