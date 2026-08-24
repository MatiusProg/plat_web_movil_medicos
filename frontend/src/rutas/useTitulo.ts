import { useEffect } from 'react'

const SUFIJO = 'Centro Médico'

/**
 * Pone el título de la pestaña según la pantalla.
 *
 * No es cosmética: con varias pestañas abiertas —que es exactamente cómo
 * trabaja una recepcionista— el título es lo único que distingue una de otra.
 * Y es lo primero que anuncia un lector de pantalla al cambiar de página.
 */
export function useTitulo(titulo: string): void {
  useEffect(() => {
    const anterior = document.title
    document.title = `${titulo} · ${SUFIJO}`
    return () => {
      document.title = anterior
    }
  }, [titulo])
}
