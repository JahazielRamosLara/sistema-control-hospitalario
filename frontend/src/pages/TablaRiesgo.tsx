import { useEffect, useState } from 'react'
import { api, type Umbral } from '../api'
import { useCatalogos } from '../catalogos'
import { Cargando, ErrorMsg, RiesgoBadge } from '../components/ui'

export function TablaRiesgo() {
  const { config } = useCatalogos()
  const [filas, setFilas] = useState<Umbral[] | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [aviso, setAviso] = useState('')
  const [sucio, setSucio] = useState(false)

  useEffect(() => {
    api.riesgo().then(setFilas).catch(setError)
  }, [])

  if (!filas) return error ? <ErrorMsg error={error} /> : <Cargando />

  const cambiar = (i: number, cambio: Partial<Umbral>) => {
    setSucio(true)
    setAviso('')
    setFilas(filas.map((f, j) => (j === i ? { ...f, ...cambio } : f)))
  }

  async function guardar() {
    try {
      const r = await api.guardarRiesgo(
        filas!.map(({ eventos_minimos, nivel, semaforo, accion, alerta }) => ({ eventos_minimos, nivel, semaforo, accion, alerta })),
      )
      setFilas(r)
      setError(null)
      setSucio(false)
      setAviso('Escala guardada. El nivel de todos los pacientes se recalcula automáticamente.')
    } catch (e) {
      setError(e)
    }
  }

  const rango = (i: number) => {
    const desde = filas[i].eventos_minimos
    const sig = filas[i + 1]?.eventos_minimos
    if (sig === undefined) return `${desde} o más`
    if (sig - 1 === desde) return `${desde}`
    return `${desde} a ${sig - 1}`
  }

  return (
    <>
      <header className="pagina-header">
        <div>
          <h1>Tabla de riesgo</h1>
          <p className="subtitulo">
            Escala acumulativa e histórica: el nivel es el último umbral que no supera los eventos críticos del paciente.
          </p>
        </div>
        <div className="botonera">
          <button
            className="btn"
            onClick={() => {
              setSucio(true)
              setFilas([...filas, { eventos_minimos: (filas.at(-1)?.eventos_minimos ?? 0) + 1, nivel: 'NUEVO NIVEL', semaforo: 'Rojo', accion: '', alerta: true }])
            }}
          >
            Agregar nivel
          </button>
          <button className="btn btn-primario" disabled={!sucio} onClick={guardar}>
            Guardar escala
          </button>
        </div>
      </header>
      <ErrorMsg error={error} />
      {aviso && <div className="alerta-ok">{aviso}</div>}

      <section className="tarjeta sin-relleno">
        <div className="tabla-scroll">
          <table className="tabla tabla-edicion">
            <thead>
              <tr>
                <th>Eventos críticos (mínimo)</th>
                <th>Rango</th>
                <th>Nivel</th>
                <th>Semáforo</th>
                <th>Acción requerida</th>
                <th title="Cuenta en el indicador «Pacientes en riesgo alto o crítico»">Alerta</th>
                <th>Vista</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filas.map((f, i) => (
                <tr key={i}>
                  <td>
                    <input type="number" min={0} value={f.eventos_minimos} disabled={i === 0} onChange={(e) => cambiar(i, { eventos_minimos: Number(e.target.value) })} />
                  </td>
                  <td className="nowrap tenue">{rango(i)}</td>
                  <td><input value={f.nivel} onChange={(e) => cambiar(i, { nivel: e.target.value.toUpperCase() })} /></td>
                  <td>
                    <select value={f.semaforo} onChange={(e) => cambiar(i, { semaforo: e.target.value })}>
                      {config?.semaforos.map((s) => <option key={s}>{s}</option>)}
                    </select>
                  </td>
                  <td><input value={f.accion ?? ''} onChange={(e) => cambiar(i, { accion: e.target.value })} className="ancho" /></td>
                  <td className="centro"><input type="checkbox" checked={f.alerta} onChange={(e) => cambiar(i, { alerta: e.target.checked })} /></td>
                  <td><RiesgoBadge nivel={f.nivel} semaforo={f.semaforo} /></td>
                  <td>
                    {i > 0 && (
                      <button className="btn-texto peligro" onClick={() => { setSucio(true); setFilas(filas.filter((_, j) => j !== i)) }}>
                        Quitar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <p className="nota">
        Los umbrales dependen del perfil del hospital. Al guardar se ordenan de menor a mayor; el primero siempre es 0 y no
        se admiten umbrales repetidos. «Alerta» marca los niveles que cuentan como riesgo alto o crítico en el menú.
      </p>
    </>
  )
}
