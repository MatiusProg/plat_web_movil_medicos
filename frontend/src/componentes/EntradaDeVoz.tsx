/**
 * Un pedido hablado o escrito.
 *
 * Una caja de texto y, si el navegador puede dictar, un botón para hablar. Las
 * dos cosas terminan en lo mismo: un texto que se manda a `alEnviar`. **Hablar
 * no es obligatorio**: Firefox no tiene la Web Speech API y un celular puede
 * tener el micrófono denegado, así que escribir siempre tiene que alcanzar.
 *
 * El audio no sale del navegador (ver `useVoz.ts`): acá solo llega el texto ya
 * transcrito, que se vuelca en la caja para que se pueda corregir antes —o
 * después— de mandarlo. Cuando termina de hablar se envía solo: esperar un
 * segundo botón después de dictar es justo lo que hace que la voz no valga la
 * pena.
 */

import { useId, useState, type FormEvent } from 'react'

import { INPUT, SECONDARY } from '@/paginas/catalogo_comun'

import { Boton } from './Boton'
import { IconoMicrofono } from './iconos'
import { useVoz } from './useVoz'

interface Props {
  /** Qué hacer con el pedido, ya sea dictado o escrito. */
  alEnviar: (texto: string) => void
  /** Hay una consulta en curso. */
  ocupado?: boolean
  etiqueta: string
  placeholder?: string
}

export function EntradaDeVoz({ alEnviar, ocupado = false, etiqueta, placeholder }: Props) {
  const id = useId()
  const [texto, setTexto] = useState('')
  const voz = useVoz((dictado) => {
    setTexto(dictado)
    alEnviar(dictado)
  })

  const enviar = (evento: FormEvent) => {
    evento.preventDefault()
    const limpio = texto.trim()
    if (limpio) alEnviar(limpio)
  }

  return (
    <form onSubmit={enviar} className="space-y-3">
      <div>
        <label htmlFor={id} className="text-sm font-medium text-tinta-700 dark:text-tinta-200">
          {etiqueta}
        </label>
        <input
          id={id}
          type="text"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          maxLength={300}
          placeholder={placeholder}
          autoComplete="off"
          className={`${INPUT} mt-1.5`}
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Boton
          type="submit"
          className="w-auto"
          cargando={ocupado && !voz.escuchando}
          textoCargando="Buscando…"
          disabled={!texto.trim() || voz.escuchando}
        >
          Buscar
        </Boton>
        {voz.soportado && (
          <button
            type="button"
            className={SECONDARY}
            onClick={voz.escuchando ? voz.terminar : voz.empezar}
            aria-pressed={voz.escuchando}
          >
            <IconoMicrofono className="size-4" />
            {voz.escuchando ? 'Listo' : 'Hablar'}
          </button>
        )}
      </div>

      {voz.escuchando && (
        <p className="text-sm text-marca-700 dark:text-marca-400" aria-live="polite">
          Escuchando… {voz.texto}
        </p>
      )}
      {voz.error && <p className="text-sm text-alerta-600 dark:text-alerta-500">{voz.error}</p>}
      {!voz.soportado && (
        <p className="text-sm text-tinta-500">
          Dictar no está disponible en este navegador. Escribe lo que buscas y pulsa «Buscar».
        </p>
      )}
    </form>
  )
}
