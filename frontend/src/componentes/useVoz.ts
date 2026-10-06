/**
 * Dictado en el navegador, con la Web Speech API.
 *
 * **El audio no sale del navegador.** Quien transcribe es el propio Chrome —en
 * su implementación, contra los servidores de Google— y lo que viaja a nuestro
 * backend es el texto. Por eso acá no se graba, no se guarda y no se sube nada.
 *
 * Dos cosas que conviene saber antes de tocar este archivo:
 *
 * 1. **No está en todos los navegadores.** Chrome y Edge sí, Firefox no. Por
 *    eso se expone `soportado`: la pantalla esconde el botón en vez de ofrecer
 *    algo que no va a funcionar. El formulario sigue armándose a mano.
 * 2. **Exige origen seguro.** El micrófono sólo funciona en `https` o en
 *    `localhost`. Abrir la web por la IP de la red local —`http://192.168…`—
 *    deja el botón visible y el permiso denegado, así que ese caso se detecta
 *    y se dice.
 */
import { useCallback, useEffect, useRef, useState } from 'react'

/** Lo mínimo que usamos de la API, que TypeScript no trae declarada. */
interface ReconocimientoDeVoz extends EventTarget {
  lang: string
  continuous: boolean
  interimResults: boolean
  start(): void
  stop(): void
  abort(): void
  onresult: ((evento: EventoDeResultado) => void) | null
  onerror: ((evento: { error: string }) => void) | null
  onend: (() => void) | null
}

interface EventoDeResultado {
  resultIndex: number
  results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }>
}

type Constructor = new () => ReconocimientoDeVoz

function constructorDeReconocimiento(): Constructor | null {
  const ventana = window as unknown as {
    SpeechRecognition?: Constructor
    webkitSpeechRecognition?: Constructor
  }
  return ventana.SpeechRecognition ?? ventana.webkitSpeechRecognition ?? null
}

export interface EstadoDeVoz {
  /** El navegador puede dictar y la página está en un origen seguro. */
  soportado: boolean
  /** Por qué no se puede dictar, para decírselo a la persona. */
  motivo: string
  escuchando: boolean
  /** Lo que se va oyendo, incluso antes de que termine la frase. */
  texto: string
  error: string
  empezar: () => void
  terminar: () => void
  limpiar: () => void
}

export function useVoz(alTerminar?: (texto: string) => void): EstadoDeVoz {
  const [escuchando, setEscuchando] = useState(false)
  const [texto, setTexto] = useState('')
  const [error, setError] = useState('')
  const reconocimiento = useRef<ReconocimientoDeVoz | null>(null)
  // En una ref y no en el estado: el manejador `onend` se registra una sola
  // vez y leería el texto que había cuando se registró.
  const ultimo = useRef('')
  // En una ref y actualizada en un efecto: el manejador `onend` se registra
  // una sola vez, así que tiene que poder leer el callback vigente sin que
  // cambiarlo obligue a recrear el motor de reconocimiento.
  const alTerminarRef = useRef(alTerminar)
  useEffect(() => {
    alTerminarRef.current = alTerminar
  }, [alTerminar])

  const disponible = typeof window !== 'undefined' && constructorDeReconocimiento() !== null
  const origenSeguro = typeof window !== 'undefined' && window.isSecureContext

  const motivo = !disponible
    ? 'Tu navegador no permite dictar. Probá con Chrome o Edge, o armá el reporte a mano.'
    : !origenSeguro
      ? 'El micrófono sólo funciona con https o en localhost. Entrá por localhost para dictar.'
      : ''

  useEffect(() => {
    // Cortar al desmontar: sin esto, salir de la pantalla mientras escucha
    // deja el micrófono abierto hasta que el navegador lo corta solo.
    return () => reconocimiento.current?.abort()
  }, [])

  const empezar = useCallback(() => {
    const Constructor = constructorDeReconocimiento()
    if (!Constructor || !origenSeguro) return

    const motor = new Constructor()
    motor.lang = 'es-BO'
    motor.continuous = false
    motor.interimResults = true

    motor.onresult = (evento) => {
      let frase = ''
      for (let i = 0; i < evento.results.length; i += 1) {
        frase += evento.results[i][0].transcript
      }
      ultimo.current = frase.trim()
      setTexto(ultimo.current)
    }
    motor.onerror = (evento) => {
      setError(
        evento.error === 'not-allowed'
          ? 'No diste permiso para usar el micrófono.'
          : evento.error === 'no-speech'
            ? 'No escuché nada. Probá de nuevo.'
            : 'No se pudo usar el micrófono.',
      )
      setEscuchando(false)
    }
    motor.onend = () => {
      setEscuchando(false)
      if (ultimo.current) alTerminarRef.current?.(ultimo.current)
    }

    ultimo.current = ''
    setTexto('')
    setError('')
    setEscuchando(true)
    reconocimiento.current = motor
    motor.start()
  }, [origenSeguro])

  const terminar = useCallback(() => reconocimiento.current?.stop(), [])

  const limpiar = useCallback(() => {
    ultimo.current = ''
    setTexto('')
    setError('')
  }, [])

  return {
    soportado: disponible && origenSeguro,
    motivo,
    escuchando,
    texto,
    error,
    empezar,
    terminar,
    limpiar,
  }
}
