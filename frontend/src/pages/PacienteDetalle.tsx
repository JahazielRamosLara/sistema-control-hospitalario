import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, type Atencion, type PacienteDetalle as Detalle } from '../api'
import { AtencionForm } from '../components/AtencionForm'
import { PacienteForm } from '../components/PacienteForm'
import { Cargando, ErrorMsg, Modal, RiesgoBadge, TriageBadge } from '../components/ui'
import { fecha } from '../formato'

export function PacienteDetalle() {
  const { id } = useParams()
  const navegar = useNavigate()
  const [p, setP] = useState<Detalle | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [editar, setEditar] = useState(false)
  const [atencion, setAtencion] = useState<Atencion | 'nueva' | null>(null)

  const cargar = useCallback(() => {
    api
      .paciente(Number(id))
      .then((r) => {
        setP(r)
        setError(null)
      })
      .catch(setError)
  }, [id])

  useEffect(cargar, [cargar])

  async function eliminar() {
    if (!p) return
    if (!confirm(`¿Eliminar el expediente ${p.expediente} y sus ${p.atenciones.length} atenciones? No se puede deshacer.`))
      return
    try {
      await api.eliminarPaciente(p.id)
      navegar('/pacientes')
    } catch (e) {
      setError(e)
    }
  }

  async function eliminarAtencion(a: Atencion) {
    if (!confirm(`¿Eliminar la atención del ${fecha(a.fecha)} (${a.tipo_atencion})?`)) return
    try {
      await api.eliminarAtencion(a.id)
      cargar()
    } catch (e) {
      setError(e)
    }
  }

  if (error && !p) return <ErrorMsg error={error} />
  if (!p) return <Cargando />

  return (
    <>
      <nav className="migas">
        <Link to="/pacientes">Pacientes</Link> / <span className="mono">{p.expediente}</span>
      </nav>
      <header className="pagina-header">
        <div>
          <h1>{p.nombre}</h1>
          <p className="subtitulo">
            <span className="mono">{p.expediente}</span> · {p.servicio ?? 'Sin servicio'} · {p.estado}
          </p>
        </div>
        <div className="botonera">
          <button className="btn" onClick={() => setEditar(true)}>
            Editar datos
          </button>
          <a className="btn" href={api.urlExpedientePdf(p.id)} target="_blank" rel="noreferrer">
            Generar expediente PDF
          </a>
          <button className="btn btn-primario" onClick={() => setAtencion('nueva')}>
            Registrar atención
          </button>
        </div>
      </header>
      <ErrorMsg error={error} />

      <div className={`banda-riesgo sem-borde-${p.riesgo.semaforo.toLowerCase()}`}>
        <RiesgoBadge {...p.riesgo} />
        <div>
          <strong>{p.riesgo.eventos_criticos}</strong> eventos críticos acumulados en{' '}
          <strong>{p.total_atenciones}</strong> atenciones
          {p.riesgo.accion && <div className="tenue">Acción requerida: {p.riesgo.accion}</div>}
        </div>
      </div>

      <section className="tarjeta">
        <h2>Ficha de identificación</h2>
        <dl className="ficha">
          <div><dt>Médico tratante</dt><dd>{p.medico_tratante ?? '—'}</dd></div>
          <div><dt>Fecha de nacimiento</dt><dd>{fecha(p.fecha_nacimiento)}</dd></div>
          <div><dt>Edad</dt><dd>{p.edad != null ? `${p.edad} años` : '—'}</dd></div>
          <div><dt>Sexo</dt><dd>{p.sexo === 'M' ? 'Masculino' : p.sexo === 'F' ? 'Femenino' : '—'}</dd></div>
          <div><dt>Tipo de sangre</dt><dd>{p.tipo_sangre ?? '—'}</dd></div>
          <div>
            <dt>Alergias</dt>
            <dd className={p.alergias && p.alergias !== 'Ninguna conocida' ? 'alergia' : ''}>{p.alergias ?? '—'}</dd>
          </div>
          <div><dt>Contacto de emergencia</dt><dd>{p.contacto_emergencia ?? '—'}</dd></div>
          <div><dt>Teléfono</dt><dd>{p.telefono ?? '—'}</dd></div>
          <div><dt>Última atención</dt><dd>{fecha(p.ultima_atencion)}</dd></div>
        </dl>
      </section>

      <section className="tarjeta sin-relleno">
        <h2 className="con-relleno">Historial de atenciones</h2>
        {p.atenciones.length === 0 ? (
          <p className="estado-vacio">Sin atenciones registradas.</p>
        ) : (
          <div className="tabla-scroll">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Tipo de atención</th>
                  <th>Médico que atiende</th>
                  <th>Turno</th>
                  <th>Triage</th>
                  <th>Nota clínica / hallazgos</th>
                  <th>Plan de manejo</th>
                  <th>E.C.</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {p.atenciones.map((a) => (
                  <tr key={a.id} className={a.evento_critico ? 'fila-critica' : ''}>
                    <td className="nowrap">{fecha(a.fecha)}</td>
                    <td>{a.tipo_atencion}</td>
                    <td>{a.medico}</td>
                    <td>{a.turno}</td>
                    <td><TriageBadge triage={a.triage} /></td>
                    <td className="texto-largo">{a.nota_clinica}</td>
                    <td className="texto-largo">{a.plan_manejo}</td>
                    <td>{a.evento_critico && <span className="marca-critica">SÍ</span>}</td>
                    <td className="nowrap">
                      <button className="btn-texto" onClick={() => setAtencion(a)}>Editar</button>
                      <button className="btn-texto peligro" onClick={() => eliminarAtencion(a)}>Eliminar</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <div className="zona-peligro">
        <button className="btn btn-peligro" onClick={eliminar}>Eliminar paciente</button>
      </div>

      <Modal titulo={`Editar ${p.expediente}`} abierto={editar} onCerrar={() => setEditar(false)}>
        <PacienteForm
          paciente={p}
          onCancelar={() => setEditar(false)}
          onGuardado={() => {
            setEditar(false)
            cargar()
          }}
        />
      </Modal>
      <Modal
        titulo={atencion === 'nueva' ? 'Registrar atención' : 'Editar atención'}
        abierto={atencion !== null}
        onCerrar={() => setAtencion(null)}
        ancho={760}
      >
        <AtencionForm
          pacienteId={p.id}
          atencion={atencion && atencion !== 'nueva' ? atencion : undefined}
          onCancelar={() => setAtencion(null)}
          onGuardado={() => {
            setAtencion(null)
            cargar()
          }}
        />
      </Modal>
    </>
  )
}
