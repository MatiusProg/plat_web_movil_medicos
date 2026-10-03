/**
 * Claro, oscuro o como el sistema.
 *
 * La elección vive en el navegador (localStorage): es una preferencia de esta
 * persona en este equipo, no un dato del centro médico. Se aplica poniendo o
 * quitando la clase `dark` en <html>, que es lo que mira Tailwind
 * (`@custom-variant dark` en index.css).
 *
 * `index.html` aplica la clase antes de que cargue React, con el mismo
 * criterio, para que la página no parpadee en claro al abrirla en oscuro.
 */

export type Tema = 'sistema' | 'claro' | 'oscuro'

const CLAVE = 'tema'
const consulta = () => window.matchMedia('(prefers-color-scheme: dark)')

export function leerTema(): Tema {
  try {
    const guardado = localStorage.getItem(CLAVE)
    if (guardado === 'claro' || guardado === 'oscuro' || guardado === 'sistema') return guardado
  } catch {
    // Sin acceso al almacenamiento (modo privado estricto): como el sistema.
  }
  return 'sistema'
}

function aplicar(tema: Tema) {
  const oscuro = tema === 'oscuro' || (tema === 'sistema' && consulta().matches)
  document.documentElement.classList.toggle('dark', oscuro)
}

export function guardarTema(tema: Tema) {
  try {
    localStorage.setItem(CLAVE, tema)
  } catch {
    // Si no se puede guardar, igual se aplica por esta sesión.
  }
  aplicar(tema)
}

/** Aplica lo guardado y, con "como el sistema", sigue sus cambios en vivo. */
export function iniciarTema() {
  aplicar(leerTema())
  consulta().addEventListener('change', () => {
    if (leerTema() === 'sistema') aplicar('sistema')
  })
}
