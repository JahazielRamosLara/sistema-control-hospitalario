import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Atencion } from '../api'
import { useCatalogos } from '../catalogos'
import { AtencionForm } from '../components/AtencionForm'
import { Cargando, ErrorMsg, Modal, RiesgoBadge, TriageBadge } from '../components/ui'
import { fecha } from '../formato'

const POR_PAGINA = 25

export function Seguimiento() {
  const { servicios, medicos, config } = useCatalogos()
  const [filtros, setFiltros] = useState({
    q: '',
    servicio_id: '' as number | '',
    medico_id: '' as number | '',
    turno: '',
    solo_criticos: false,
    desde: '',
    hasta: '',
  })
  const [pagina, setPagina] = useState(0)
  const [datos, setDatos] = useState<{ total: number; items: Atencion[] } | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [modal, setModal] = useState<Atencion | 'nueva' | null>(null)
  const [version, setVersion] = useState(0)

  useEffect(() => {
    const t = setTimeout(() => {
      api
        .atenciones({ ...filtros, limit: POR_PAGINA, offset: pagina * POR_PAGINA })
        .then((r) => {
          setDatos(r)
          setError(null)
        })
        .catch(setError)
    }, 200)
    return () => clearTimeout(t)
  }, [filtros, pagina, version])

  const set = <K extends keyof typeof filtros>(k: K, v: (typeof filtros)[K]) => {
    setPagina(0)
    setFiltros((f) => ({ ...f, [k]: v }))
  }
  const paginas = datos ? Math.max(1, Math.ceil(datos.total / POR_PAGINA)) : 1

  return (
    <>
      <header className="pagina-header">
        <div>
          <h1>Seguimiento clínico</h1>
          <p className="subtitulo">Bitácora de atenciones · cada fila es una atención prestada a un paciente</p>
        </div>
        <button className="btn btn-primario" onClick={() => setModal('nueva')}>
          Registrar atención
        </button>
      </header>

      <div className="filtros">
        <input
          type="search"
          className="filtro-busqueda"
          placeholder="Expediente, paciente o texto de la nota…"
          value={filtros.q}
          onChange={(e) => set('q', e.target.value)}
        />
        <select value={filtros.servicio_id} onChange={(e) => set('servicio_id', e.target.value ? Number(e.target.value) : '')}>
          <option value="">Todos los servicios</option>
          {servicios.map((s) => (
            <option key={s.id} value={s.id}>{s.nombre}</option>
          ))}
        </select>
        <select value={filtros.medico_id} onChange={(e) => set('medico_id', e.target.value ? Number(e.target.value) : '')}>
          <option value="">Todos los médicos</option>
          {medicos.map((m) => (
            <option key={m.id} value={m.id}>{m.nombre}</option>
          ))}
        </select>
        <select value={filtros.turno} onChange={(e) => set('turno', e.target.value)}>
          <option value="">Todos los turnos</option>
          {config?.turnos.map((t) => <option key={t}>{t}</option>)}
        </select>
        <label className="filtro-fecha">
          Desde <input type="date" value={filtros.desde} onChange={(e) => set('desde', e.target.value)} />
        </label>
        <label className="filtro-fecha">
          Hasta <input type="date" value={filtros.hasta} onChange={(e) => set('hasta', e.target.value)} />
        </label>
        <label className="filtro-check">
          <input type="checkbox" checked={filtros.solo_criticos} onChange={(e) => set('solo_criticos', e.target.checked)} />
          Solo eventos críticos
        </label>
      </div>

      <ErrorMsg error={error} />
      {!datos ? (
        <Cargando />
      ) : datos.items.length === 0 ? (
        <div className="estado-vacio">Sin atenciones para los filtros elegidos.</div>
      ) : (
        <div className="tarjeta sin-relleno">
          <div className="tabla-scroll">
            <table className="tabla tabla-densa">
              <thead>
                <tr>
                  <th className="num">ID</th>
                  <th>Fecha</th>
                  <th>Expediente</th>
                  <th>Paciente</th>
                  <th>Servicio</th>
                  <th>Tipo de atención</th>
                  <th>Médico que atiende</th>
                  <th>Turno</th>
                  <th>Triage</th>
                  <th>Nota clínica</th>
                  <th>E.C.</th>
                  <th>Riesgo del paciente</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {datos.items.map((a) => (
                  <tr key={a.id} className={a.evento_critico ? 'fila-critica' : ''}>
                    <td className="num tenue">{a.id}</td>
                    <td className="nowrap">{fecha(a.fecha)}</td>
                    <td className="mono"><Link to={`/pacientes/${a.paciente_id}`}>{a.expediente}</Link></td>
                    <td>{a.paciente}</td>
                    <td>{a.servicio}</td>
                    <td>{a.tipo_atencion}</td>
                    <td>{a.medico}</td>
                    <td>{a.turno}</td>
                    <td><TriageBadge triage={a.triage} /></td>
                    <td className="texto-largo">{a.nota_clinica}</td>
                    <td>{a.evento_critico && <span className="marca-critica">SÍ</span>}</td>
                    <td><RiesgoBadge nivel={a.nivel_riesgo} semaforo={a.semaforo} eventos={a.total_eventos_criticos} /></td>
                    <td><button className="btn-texto" onClick={() => setModal(a)}>Editar</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="paginacion">
            <span>{datos.total} atenciones</span>
            <button className="btn" disabled={pagina === 0} onClick={() => setPagina((p) => p - 1)}>‹ Anterior</button>
            <span>Página {pagina + 1} de {paginas}</span>
            <button className="btn" disabled={pagina + 1 >= paginas} onClick={() => setPagina((p) => p + 1)}>Siguiente ›</button>
          </div>
        </div>
      )}

      <Modal
        titulo={modal === 'nueva' ? 'Registrar atención' : 'Editar atención'}
        abierto={modal !== null}
        onCerrar={() => setModal(null)}
        ancho={760}
      >
        <AtencionForm
          atencion={modal && modal !== 'nueva' ? modal : undefined}
          onCancelar={() => setModal(null)}
          onGuardado={() => {
            setModal(null)
            setVersion((v) => v + 1)
          }}
        />
      </Modal>
    </>
  )
}
