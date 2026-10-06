/**
 * Característica general 5 — El constructor de reportes, y pedirlos hablando.
 *
 * La pantalla arma la definición —conjunto, columnas, criterios, orden— y la
 * manda al mismo endpoint que usa el móvil. El catálogo de `GET /datasets/`
 * es lo único que necesita: de ahí salen las columnas, los filtros, sus tipos
 * y qué comparaciones admite cada uno, así que esta pantalla no sabe nada del
 * modelo de datos.
 *
 * **La voz llena este formulario; no genera nada por su cuenta.** Lo que se
 * dicta viaja como texto al backend, que devuelve una propuesta; acá se marca
 * en los mismos controles que se usan a mano y queda esperando confirmación.
 * La consigna de la materia pide una interfaz previa para filtrar antes de
 * generar: si la voz ejecutara sola, esa interfaz no existiría.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  COMPARACIONES, exportar, interpretarPorVoz, listarConjuntos, previsualizar,
  type CampoDeReporte, type CatalogoDeReportes, type ConjuntoDeDatos,
  type CriterioDeFiltro, type DefinicionDeReporte, type Formato,
  type Interpretacion, type VistaPrevia,
} from '@/api/reportes'
import { Boton } from '@/componentes/Boton'
import { useVoz } from '@/componentes/useVoz'
import { useTitulo } from '@/rutas/useTitulo'
import { useSesion } from '@/sesion/useSesion'
import { AvisoCatalogo, ErrorCatalogo, INPUT, PANEL, SECONDARY, mensajeError } from './catalogo_comun'

const FORMATOS: { valor: Exclude<Formato, 'json'>; etiqueta: string }[] = [
  { valor: 'xlsx', etiqueta: 'Excel' },
  { valor: 'pdf', etiqueta: 'PDF' },
  { valor: 'html', etiqueta: 'HTML' },
  { valor: 'csv', etiqueta: 'CSV' },
]

/** El valor de un criterio, según el tipo del campo. */
function valorInicial(campo: CampoDeReporte): string | boolean {
  if (campo.kind === 'boolean') return true
  if (campo.kind === 'choice') return campo.choices?.[0]?.value ?? ''
  return ''
}

export function Reportes() {
  const { token, puede } = useSesion()
  useTitulo('Reportes')
  const habilitado = puede('reporting.report.run')

  const [catalogo, setCatalogo] = useState<CatalogoDeReportes | null>(null)
  const [conjunto, setConjunto] = useState<ConjuntoDeDatos | null>(null)
  const [columnas, setColumnas] = useState<string[]>([])
  const [criterios, setCriterios] = useState<CriterioDeFiltro[]>([])
  const [orden, setOrden] = useState<string[]>([])
  const [vista, setVista] = useState<VistaPrevia | null>(null)
  const [interpretacion, setInterpretacion] = useState<Interpretacion | null>(null)
  const [trabajando, setTrabajando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)

  // ---------- el catálogo ------------------------------------------------
  useEffect(() => {
    if (!habilitado) return
    const control = new AbortController()
    listarConjuntos({ token }, control.signal)
      .then((datos) => {
        setCatalogo(datos)
        elegirConjunto(datos.datasets[0] ?? null)
      })
      .catch((e) => {
        if (!(e instanceof DOMException && e.name === 'AbortError')) setError(mensajeError(e))
      })
    return () => control.abort()
    // `elegirConjunto` sólo toca estado local y no cambia entre renders.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [habilitado, token])

  function elegirConjunto(elegido: ConjuntoDeDatos | null) {
    setConjunto(elegido)
    setColumnas(elegido ? [...elegido.default_columns] : [])
    setCriterios([])
    setOrden([])
    setVista(null)
    setInterpretacion(null)
  }

  const definicion: DefinicionDeReporte | null = useMemo(
    () =>
      conjunto
        ? { dataset: conjunto.code, columns: columnas, filters: criterios, order_by: orden }
        : null,
    [conjunto, columnas, criterios, orden],
  )

  // ---------- la voz -----------------------------------------------------
  const aplicar = useCallback(
    (propuesta: Interpretacion) => {
      setInterpretacion(propuesta)
      const nueva = propuesta.definition
      if (!nueva || !catalogo) return
      const elegido = catalogo.datasets.find((d) => d.code === nueva.dataset)
      if (!elegido) return
      setConjunto(elegido)
      setColumnas(nueva.columns.length ? nueva.columns : [...elegido.default_columns])
      setCriterios(nueva.filters)
      setOrden(nueva.order_by)
      setVista(null)
    },
    [catalogo],
  )

  const dictado = useCallback(
    async (texto: string) => {
      setTrabajando(true)
      setError(null)
      try {
        aplicar(await interpretarPorVoz(texto, conjunto?.code ?? '', { token }))
      } catch (e) {
        setError(mensajeError(e))
      } finally {
        setTrabajando(false)
      }
    },
    [aplicar, conjunto, token],
  )

  const voz = useVoz((texto) => void dictado(texto))

  // ---------- generar ----------------------------------------------------
  const previsualizarAhora = async () => {
    if (!definicion) return
    setTrabajando(true)
    setError(null)
    try {
      setVista(await previsualizar(definicion, { token }))
    } catch (e) {
      setError(mensajeError(e))
      setVista(null)
    } finally {
      setTrabajando(false)
    }
  }

  const exportarAhora = async (formato: Exclude<Formato, 'json'>) => {
    if (!definicion || !conjunto) return
    setTrabajando(true)
    setError(null)
    try {
      const nombre = await exportar(definicion, formato, conjunto.label, { token })
      setAviso(`Reporte descargado: ${nombre}.`)
    } catch (e) {
      setError(mensajeError(e))
    } finally {
      setTrabajando(false)
    }
  }

  if (!habilitado) {
    return (
      <main className="mx-auto max-w-4xl px-5 py-10 text-tinta-500">
        No tenés permiso para armar reportes.
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-5xl space-y-6 px-5 py-8 sm:py-10">
      <div className="surgir">
        <p className="text-sm font-medium text-marca-700 dark:text-marca-400">Organización</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-tinta-900 dark:text-tinta-50">Reportes</h1>
        <p className="mt-1.5 max-w-2xl text-[0.9375rem] text-tinta-500">
          Elegí qué datos querés, con qué criterios y en qué orden. Podés pedirlo hablando y después revisarlo
          antes de generarlo.
        </p>
      </div>

      {aviso && <AvisoCatalogo mensaje={aviso} onCerrar={() => setAviso(null)} />}
      {error && <ErrorCatalogo mensaje={error} />}

      <SeccionVoz voz={voz} trabajando={trabajando} interpretacion={interpretacion} />

      {catalogo && conjunto && (
        <>
          <section className={PANEL}>
            <h2 className="font-semibold text-tinta-900 dark:text-tinta-100">Qué datos</h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {catalogo.datasets.map((d) => (
                <button
                  key={d.code}
                  type="button"
                  onClick={() => elegirConjunto(d)}
                  className={
                    d.code === conjunto.code
                      ? 'rounded-lg bg-marca-600 px-3 py-2 text-sm font-semibold text-white'
                      : SECONDARY
                  }
                >
                  {d.label}
                </button>
              ))}
            </div>
            <p className="mt-3 text-sm text-tinta-500">{conjunto.description}</p>
          </section>

          <Columnas
            conjunto={conjunto}
            elegidas={columnas}
            onCambiar={setColumnas}
            orden={orden}
            onOrden={setOrden}
          />

          <Criterios conjunto={conjunto} criterios={criterios} onCambiar={setCriterios} />

          <section className={PANEL}>
            <div className="flex flex-wrap items-center gap-3">
              <Boton
                type="button"
                className="w-auto"
                cargando={trabajando}
                disabled={!columnas.length}
                onClick={() => void previsualizarAhora()}
              >
                Ver resultado
              </Boton>
              {FORMATOS.map((f) => (
                <button
                  key={f.valor}
                  type="button"
                  className={SECONDARY}
                  disabled={trabajando || !columnas.length}
                  onClick={() => void exportarAhora(f.valor)}
                >
                  {f.etiqueta}
                </button>
              ))}
            </div>
            {!columnas.length && (
              <p className="mt-3 text-sm text-tinta-500">Elegí al menos una columna.</p>
            )}
          </section>

          {vista && <Resultado vista={vista} maximo={catalogo.max_rows} />}
        </>
      )}
    </main>
  )
}

// --------------------------------------------------------------------------
//  La voz
// --------------------------------------------------------------------------
function SeccionVoz({
  voz,
  trabajando,
  interpretacion,
}: {
  voz: ReturnType<typeof useVoz>
  trabajando: boolean
  interpretacion: Interpretacion | null
}) {
  return (
    <section className={PANEL} aria-labelledby="voz-titulo">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-xl">
          <h2 id="voz-titulo" className="font-semibold text-tinta-900 dark:text-tinta-100">
            Pedilo hablando
          </h2>
          <p className="mt-1 text-sm text-tinta-500">
            Por ejemplo: «pacientes mujeres dadas de alta en septiembre, con nombre y teléfono».
            Lo que entienda queda marcado abajo para que lo revises.
          </p>
          {!voz.soportado && <p className="mt-2 text-sm text-tinta-500">{voz.motivo}</p>}
        </div>
        {voz.soportado && (
          <Boton
            type="button"
            className="w-auto"
            cargando={trabajando}
            onClick={voz.escuchando ? voz.terminar : voz.empezar}
          >
            {voz.escuchando ? 'Listo' : 'Hablar'}
          </Boton>
        )}
      </div>

      {voz.escuchando && (
        <p className="mt-4 text-sm text-marca-700 dark:text-marca-400" aria-live="polite">
          Escuchando… {voz.texto}
        </p>
      )}
      {voz.error && <p className="mt-3 text-sm text-alerta-600 dark:text-alerta-500">{voz.error}</p>}

      {interpretacion && !voz.escuchando && (
        <div className="mt-4 rounded-xl border border-tinta-200 p-4 text-sm dark:border-tinta-800">
          <p className="text-tinta-800 dark:text-tinta-100">
            {interpretacion.understood ? 'Entendí: ' : ''}
            {interpretacion.spoken_summary}
          </p>
          {interpretacion.unresolved.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-tinta-500">
              {interpretacion.unresolved.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
          {interpretacion.generated_by === 'plantilla' && (
            <p className="mt-2 text-xs text-tinta-500">
              El asistente no pudo interpretar la frase completa: revisá las columnas y los criterios
              antes de generar.
            </p>
          )}
        </div>
      )}
    </section>
  )
}

// --------------------------------------------------------------------------
//  Columnas y orden
// --------------------------------------------------------------------------
function Columnas({
  conjunto,
  elegidas,
  onCambiar,
  orden,
  onOrden,
}: {
  conjunto: ConjuntoDeDatos
  elegidas: string[]
  onCambiar: (columnas: string[]) => void
  orden: string[]
  onOrden: (orden: string[]) => void
}) {
  const alternar = (codigo: string) =>
    onCambiar(
      elegidas.includes(codigo) ? elegidas.filter((c) => c !== codigo) : [...elegidas, codigo],
    )

  /** Sin orden → ascendente → descendente → sin orden. */
  const rotarOrden = (codigo: string) => {
    if (orden.includes(codigo)) return onOrden(orden.map((o) => (o === codigo ? `-${codigo}` : o)))
    if (orden.includes(`-${codigo}`)) return onOrden(orden.filter((o) => o !== `-${codigo}`))
    onOrden([...orden, codigo])
  }

  const marcaDeOrden = (codigo: string) =>
    orden.includes(codigo) ? ' ↑' : orden.includes(`-${codigo}`) ? ' ↓' : ''

  return (
    <section className={PANEL}>
      <h2 className="font-semibold text-tinta-900 dark:text-tinta-100">Qué columnas</h2>
      <p className="mt-1 text-sm text-tinta-500">
        Tocá el nombre para incluirla; la flecha ordena por esa columna.
      </p>
      <ul className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {conjunto.columns.map((columna) => (
          <li key={columna.code} className="flex items-center justify-between gap-2">
            <label className="flex flex-1 items-center gap-2 text-sm text-tinta-700 dark:text-tinta-200">
              <input
                type="checkbox"
                checked={elegidas.includes(columna.code)}
                onChange={() => alternar(columna.code)}
                className="size-4 rounded border-tinta-300"
              />
              {columna.label}
            </label>
            <button
              type="button"
              className="rounded-lg px-2 py-1 text-xs text-tinta-500 hover:bg-tinta-100 dark:hover:bg-tinta-800"
              onClick={() => rotarOrden(columna.code)}
              aria-label={`Ordenar por ${columna.label}`}
            >
              orden{marcaDeOrden(columna.code)}
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

// --------------------------------------------------------------------------
//  Criterios de selección
// --------------------------------------------------------------------------
function Criterios({
  conjunto,
  criterios,
  onCambiar,
}: {
  conjunto: ConjuntoDeDatos
  criterios: CriterioDeFiltro[]
  onCambiar: (criterios: CriterioDeFiltro[]) => void
}) {
  const agregar = () => {
    const campo = conjunto.filters[0]
    if (!campo) return
    onCambiar([
      ...criterios,
      { field: campo.code, operator: campo.operators?.[0] ?? 'eq', value: valorInicial(campo) },
    ])
  }

  const cambiar = (indice: number, cambios: Partial<CriterioDeFiltro>) =>
    onCambiar(criterios.map((c, i) => (i === indice ? { ...c, ...cambios } : c)))

  return (
    <section className={PANEL}>
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-semibold text-tinta-900 dark:text-tinta-100">Con qué criterios</h2>
        <button type="button" className={SECONDARY} onClick={agregar}>
          Agregar criterio
        </button>
      </div>

      {criterios.length === 0 && (
        <p className="mt-3 text-sm text-tinta-500">Sin criterios: salen todas las filas.</p>
      )}

      <ul className="mt-3 space-y-3">
        {criterios.map((criterio, indice) => {
          const campo = conjunto.filters.find((f) => f.code === criterio.field)
          return (
            <li key={indice} className="flex flex-wrap items-center gap-2">
              <select
                className={`${INPUT} w-auto`}
                value={criterio.field}
                onChange={(e) => {
                  const nuevo = conjunto.filters.find((f) => f.code === e.target.value)
                  if (!nuevo) return
                  cambiar(indice, {
                    field: nuevo.code,
                    operator: nuevo.operators?.[0] ?? 'eq',
                    value: valorInicial(nuevo),
                  })
                }}
              >
                {conjunto.filters.map((f) => (
                  <option key={f.code} value={f.code}>
                    {f.label}
                  </option>
                ))}
              </select>

              <select
                className={`${INPUT} w-auto`}
                value={criterio.operator}
                onChange={(e) => cambiar(indice, { operator: e.target.value })}
              >
                {(campo?.operators ?? ['eq']).map((op) => (
                  <option key={op} value={op}>
                    {COMPARACIONES[op] ?? op}
                  </option>
                ))}
              </select>

              <ValorDeCriterio
                campo={campo}
                valor={criterio.value}
                onCambiar={(valor) => cambiar(indice, { value: valor })}
              />

              <button
                type="button"
                className="rounded-lg px-2 py-2 text-sm text-alerta-600 hover:bg-alerta-50 dark:text-alerta-500 dark:hover:bg-alerta-500/10"
                onClick={() => onCambiar(criterios.filter((_, i) => i !== indice))}
              >
                Quitar
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function ValorDeCriterio({
  campo,
  valor,
  onCambiar,
}: {
  campo: CampoDeReporte | undefined
  valor: string | number | boolean
  onCambiar: (valor: string | boolean) => void
}) {
  if (!campo) return null

  if (campo.kind === 'boolean') {
    return (
      <select
        className={`${INPUT} w-auto`}
        value={String(valor)}
        onChange={(e) => onCambiar(e.target.value === 'true')}
      >
        <option value="true">Sí</option>
        <option value="false">No</option>
      </select>
    )
  }

  if (campo.kind === 'choice') {
    return (
      <select
        className={`${INPUT} w-auto`}
        value={String(valor)}
        onChange={(e) => onCambiar(e.target.value)}
      >
        {(campo.choices ?? []).map((opcion) => (
          <option key={opcion.value} value={opcion.value}>
            {opcion.label}
          </option>
        ))}
      </select>
    )
  }

  return (
    <input
      className={`${INPUT} w-auto`}
      type={campo.kind === 'date' || campo.kind === 'datetime' ? 'date' : campo.kind === 'number' ? 'number' : 'text'}
      value={String(valor)}
      onChange={(e) => onCambiar(e.target.value)}
    />
  )
}

// --------------------------------------------------------------------------
//  El resultado
// --------------------------------------------------------------------------
function Resultado({ vista, maximo }: { vista: VistaPrevia; maximo: number }) {
  return (
    <section className={PANEL}>
      <h2 className="font-semibold text-tinta-900 dark:text-tinta-100">{vista.title}</h2>
      {vista.rows.length === 0 ? (
        <p className="mt-3 text-sm text-tinta-500">Ninguna fila cumple esos criterios.</p>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-tinta-500">
              <tr>
                {vista.columns.map((columna) => (
                  <th key={columna.code} className="whitespace-nowrap px-2 py-1 font-medium">
                    {columna.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="text-tinta-800 dark:text-tinta-100">
              {vista.rows.map((fila, i) => (
                <tr key={i} className="border-t border-tinta-200 dark:border-tinta-800">
                  {fila.map((celda, j) => (
                    <td key={j} className="whitespace-nowrap px-2 py-1">
                      {celda === null || celda === '' ? '—' : String(celda)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-3 text-xs text-tinta-500">
        {vista.truncated
          ? `Vista previa recortada. El archivo trae hasta ${maximo.toLocaleString('es-BO')} filas.`
          : 'Esto es una vista previa: el archivo exportado trae todas las filas.'}
      </p>
    </section>
  )
}
