import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api, type Paciente, type Umbral } from '../api'
import { useAuth } from '../auth'
import { useCatalogos } from '../catalogos'
import { PacienteForm } from '../components/PacienteForm'
import { Cargando, ErrorMsg, Modal, RiesgoBadge } from '../components/ui'

export function Pacientes() {
  const { puede } = useAuth()
  const { servicios } = useCatalogos()
  const [params, setParams] = useSearchParams()
  const [pacientes, setPacientes] = useState<Paciente[] | null>(null)
  const [niveles, setNiveles] = useState<Umbral[]>([])
  const [error, setError] = useState<unknown>(null)
  const [alta, setAlta] = useState(false)
  const navegar = useNavigate()

  const q = params.get('q') ?? ''
  const servicio = params.get('servicio') ?? ''
  const nivel = params.get('nivel') ?? ''

  const filtro = (k: string, v: string) => {
    const p = new URLSearchParams(params)
    if (v) p.set(k, v)
    else p.delete(k)
    setParams(p, { replace: true })
  }

  useEffect(() => {
    api.riesgo().then(setNiveles).catch(() => {})
  }, [])

  useEffect(() => {
    const t = setTimeout(() => {
      api
        .pacientes({ q, servicio_id: servicio ? Number(servicio) : '', nivel })
        .then((r) => {
          setPacientes(r)
          setError(null)
        })
        .catch(setError)
    }, 200)
    return () => clearTimeout(t)
  }, [q, servicio, nivel])

  return (
    <>
      <header className="pagina-header">
        <div>
          <h1>Pacientes</h1>
          <p className="subtitulo">Censo de pacientes y búsqueda por expediente</p>
        </div>
        {puede('pacientes') && (
        <button className="btn btn-primario" onClick={() => setAlta(true)}>
          Alta de paciente
        </button>
        )}
      </header>

      <div className="filtros">
        <input
          type="search"
          placeholder="Buscar por expediente o nombre…"
          value={q}
          onChange={(e) => filtro('q', e.target.value)}
          className="filtro-busqueda"
        />
        <select value={servicio} onChange={(e) => filtro('servicio', e.target.value)}>
          <option value="">Todos los servicios</option>
          {servicios.map((s) => (
            <option key={s.id} value={s.id}>
              {s.nombre}
            </option>
          ))}
        </select>
        <select value={nivel} onChange={(e) => filtro('nivel', e.target.value)}>
          <option value="">Todos los niveles</option>
          {niveles.map((n) => (
            <option key={n.nivel}>{n.nivel}</option>
          ))}
        </select>
      </div>

      <ErrorMsg error={error} />
      {!pacientes ? (
        <Cargando />
      ) : pacientes.length === 0 ? (
        <div className="estado-vacio">No hay pacientes que coincidan con los filtros.</div>
      ) : (
        <div className="tarjeta sin-relleno">
          <div className="tabla-scroll">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Expediente</th>
                  <th>Paciente</th>
                  <th>Servicio</th>
                  <th>Médico tratante</th>
                  <th className="num">Edad</th>
                  <th>Sexo</th>
                  <th>Sangre</th>
                  <th className="num">Atenciones</th>
                  <th>Riesgo</th>
                </tr>
              </thead>
              <tbody>
                {pacientes.map((p) => (
                  <tr key={p.id} className="fila-link" onClick={() => navegar(`/pacientes/${p.id}`)}>
                    <td className="mono">{p.expediente}</td>
                    <td>
                      {p.nombre}
                      {p.estado !== 'Activo' && <span className="etiqueta">{p.estado}</span>}
                    </td>
                    <td>{p.servicio ?? '—'}</td>
                    <td>{p.medico_tratante ?? '—'}</td>
                    <td className="num">{p.edad ?? '—'}</td>
                    <td>{p.sexo ?? '—'}</td>
                    <td>{p.tipo_sangre ?? '—'}</td>
                    <td className="num">{p.total_atenciones}</td>
                    <td>
                      <RiesgoBadge {...p.riesgo} eventos={p.riesgo.eventos_criticos} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="pie-tabla">{pacientes.length} pacientes</p>
        </div>
      )}

      <Modal titulo="Alta de paciente" abierto={alta} onCerrar={() => setAlta(false)}>
        <PacienteForm
          onCancelar={() => setAlta(false)}
          onGuardado={(p) => {
            setAlta(false)
            navegar(`/pacientes/${p.id}`)
          }}
        />
      </Modal>
    </>
  )
}
