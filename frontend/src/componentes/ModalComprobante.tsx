/**
 * US-19 — El comprobante de una ficha pagada, con su QR.
 *
 * El QR lleva el código firmado `MC1.<firma>` que emite el backend: recepción
 * lo escanea o lo pega en el check-in (US-22). La web no arma ni valida nada
 * del código; sólo lo dibuja.
 */

import { QRCodeSVG } from 'qrcode.react'
import { useEffect, useState } from 'react'

import { comprobante, type Comprobante } from '@/api/fichas'
import { ErrorApi } from '@/api/tipos'
import { Aviso } from '@/componentes/Aviso'
import { useSesion } from '@/sesion/useSesion'

interface Props {
  fichaId: string | null
  onCerrar: () => void
}

function fechaYHora(iso: string): string {
  return new Date(iso).toLocaleString('es-BO', {
    weekday: 'long', day: 'numeric', month: 'long',
    hour: '2-digit', minute: '2-digit',
  })
}

export function ModalComprobante({ fichaId, onCerrar }: Props) {
  const { token } = useSesion()
  const [datos, setDatos] = useState<Comprobante | null>(null)
  const [error, setError] = useState<ErrorApi | null>(null)
  const [copiado, setCopiado] = useState(false)

  useEffect(() => {
    if (!fichaId) return
    setDatos(null)
    setError(null)
    setCopiado(false)
    comprobante(fichaId, { token })
      .then(setDatos)
      .catch((fallo: unknown) => setError(fallo instanceof ErrorApi ? fallo : null))
  }, [fichaId, token])

  if (!fichaId) return null

  const copiar = async () => {
    if (!datos) return
    try {
      await navigator.clipboard.writeText(datos.code)
      setCopiado(true)
    } catch {
      setCopiado(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      onMouseDown={onCerrar}
    >
      <div
        className="border-tinta-200 dark:border-tinta-800 dark:bg-tinta-900 flex max-h-[calc(100dvh-2rem)] w-full max-w-md flex-col overflow-hidden rounded-3xl border bg-white shadow-2xl"
        onMouseDown={(evento) => evento.stopPropagation()}
      >
        <header className="border-tinta-200 dark:border-tinta-800 flex shrink-0 items-start justify-between border-b px-6 py-5">
          <div>
            <p className="text-marca-600 dark:text-marca-400 text-xs font-semibold uppercase tracking-wider">
              Comprobante
            </p>
            <h2 className="text-tinta-900 dark:text-tinta-50 mt-1 text-xl font-bold">
              {datos?.organization_name ?? 'Cargando…'}
            </h2>
          </div>
          <button
            type="button"
            onClick={onCerrar}
            className="text-tinta-500 hover:bg-tinta-100 dark:hover:bg-tinta-800 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-xl transition"
            aria-label="Cerrar"
          >
            ×
          </button>
        </header>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-5">
          {error && <Aviso codigo={error.codigo} mensaje={error.message} />}
          {datos && (
            <>
              <div className="flex justify-center rounded-2xl bg-white p-4">
                <QRCodeSVG value={datos.code} size={232} level="M" marginSize={2} />
              </div>
              <p className="text-tinta-500 text-center text-sm">
                Presentá este código en recepción al llegar.
              </p>
              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sm">
                <dt className="text-tinta-500">Paciente</dt>
                <dd className="text-tinta-900 dark:text-tinta-50">{datos.patient_name}</dd>
                <dt className="text-tinta-500">Profesional</dt>
                <dd className="text-tinta-900 dark:text-tinta-50">{datos.practitioner_name}</dd>
                <dt className="text-tinta-500">Sucursal</dt>
                <dd className="text-tinta-900 dark:text-tinta-50">
                  {datos.branch_name}
                  {datos.branch_address && ` · ${datos.branch_address}`}
                </dd>
                <dt className="text-tinta-500">Fecha</dt>
                <dd className="text-tinta-900 dark:text-tinta-50 capitalize">
                  {fechaYHora(datos.starts_at)}
                </dd>
              </dl>
              <button
                type="button"
                onClick={copiar}
                className="border-tinta-300 dark:border-tinta-700 text-tinta-600 dark:text-tinta-300 hover:bg-tinta-100 dark:hover:bg-tinta-800 w-full rounded-xl border px-3 py-2 text-sm font-semibold transition"
              >
                {copiado ? 'Código copiado' : 'Copiar el código'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
