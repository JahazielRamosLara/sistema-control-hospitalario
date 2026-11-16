import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, type Indicadores } from '../api'
import { AtencionForm } from '../components/AtencionForm'
import { PacienteForm } from '../components/PacienteForm'
import { Cargando, ErrorMsg, Kpi, Modal, RiesgoBadge } from '../components/ui'

export function Tablero() {
  const [datos, setDatos] = useState<Indicadores | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [modal, setModal] = useState<'paciente' | 'atencion' | null>(null)
  const navegar = useNavigate()

  const cargar = () => api.indicadores().then(setDatos).catch(setError)
  useEffect(() => {
    void cargar()
  }, [])

  if (error) return <ErrorMsg error={error} />
  if (!datos) return <Cargando />

  return (
    <>
      <header className="pagina-header">
        <div>
          <h1>Menú principal</h1>
          <p className="subtitulo">Indicadores de operación al {new Date().toLocaleDateString('es-MX')}</p>
        </div>
        <div className="botonera">
          <button className="btn" onClick={() => setModal('paciente')}>
            Alta de paciente
          </button>
          <button className="btn btn-primario" onClick={() => setModal('atencion')}>
            Registrar atención
          </button>
        </div>
      </header>

      <section className="kpis">
        <Kpi etiqueta="Pacientes registrados" valor={datos.pacientes_registrados} />
        <Kpi etiqueta="Atenciones registradas" valor={datos.atenciones_registradas} />
        <Kpi etiqueta="Eventos críticos" valor={datos.eventos_criticos} />
        <Kpi etiqueta="En riesgo alto o crítico" valor={datos.pacientes_en_alerta} tono="rojo" />
        <Kpi etiqueta="Médicos activos" valor={datos.medicos_activos} />
        <Kpi etiqueta="Camas censables" valor={datos.camas_censables} />
      </section>

      <section className="bloque">
        <h2>Pacientes prioritarios</h2>
        {datos.pacientes_prioritarios.length === 0 ? (
          <p className="tenue">Ningún paciente en nivel de alerta.</p>
        ) : (
          <div className="tabla-scroll">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Expediente</th>
                  <th>Paciente</th>
                  <th>Servicio</th>
                  <th>Médico tratante</th>
                  <th>Riesgo</th>
                  <th>Acción requerida</th>
                </tr>
              </thead>
              <tbody>
                {datos.pacientes_prioritarios.map((p) => (
                  <tr key={p.id} className="fila-link" onClick={() => navegar(`/pacientes/${p.id}`)}>
                    <td className="mono">{p.expediente}</td>
                    <td>{p.nombre}</td>
                    <td>{p.servicio}</td>
                    <td>{p.medico_tratante}</td>
                    <td className="nowrap">
                      <RiesgoBadge {...p.riesgo} eventos={p.riesgo.eventos_criticos} />
                    </td>
                    <td>{p.riesgo.accion}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <div className="columnas">
        <section className="bloque">
          <h2>Pacientes por nivel de riesgo</h2>
          <table className="tabla">
            <thead>
              <tr>
                <th>Nivel</th>
                <th className="num">Pacientes</th>
              </tr>
            </thead>
            <tbody>
              {datos.distribucion_riesgo.map((n) => (
                <tr key={n.nivel}>
                  <td>
                    <Link to={`/pacientes?nivel=${encodeURIComponent(n.nivel)}`} className="sin-subrayado">
                      <RiesgoBadge nivel={n.nivel} semaforo={n.semaforo} />
                    </Link>
                  </td>
                  <td className="num">{n.pacientes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="bloque">
          <h2>Atenciones por servicio</h2>
          <table className="tabla">
            <thead>
              <tr>
                <th>Servicio</th>
                <th className="num">Atenciones</th>
                <th className="num">Eventos críticos</th>
              </tr>
            </thead>
            <tbody>
              {datos.atenciones_por_servicio.map((s) => (
                <tr key={s.servicio}>
                  <td>{s.servicio}</td>
                  <td className="num">{s.atenciones}</td>
                  <td className={`num ${s.eventos_criticos ? 'marca-critica' : 'tenue'}`}>{s.eventos_criticos}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>

      <Modal titulo="Alta de paciente" abierto={modal === 'paciente'} onCerrar={() => setModal(null)}>
        <PacienteForm
          onCancelar={() => setModal(null)}
          onGuardado={(p) => {
            setModal(null)
            navegar(`/pacientes/${p.id}`)
          }}
        />
      </Modal>
      <Modal titulo="Registrar atención" abierto={modal === 'atencion'} onCerrar={() => setModal(null)} ancho={760}>
        <AtencionForm
          onCancelar={() => setModal(null)}
          onGuardado={() => {
            setModal(null)
            void cargar()
          }}
        />
      </Modal>
    </>
  )
}
